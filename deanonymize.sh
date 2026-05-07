#!/usr/bin/env bash
#
# deanonymize.sh — Restore real identity strings from anonymous placeholders.
# Reads real values from .env, reverses the anonymization done by anonymize.sh.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found. Cannot deanonymize without real values."
  exit 1
fi

# Source .env to get real identity values
set -a
source "$ENV_FILE"
set +a

# --- Anonymous placeholders (must match anonymize.sh) ---
ANON_REPO_URL_GIT="https://github.com/anonymous/anonymous-repo.git"
ANON_REPO_URL="https://github.com/anonymous/anonymous-repo"
ANON_WEBSITE="https://example.com"
ANON_EMAIL="authorA@anonymous.org"
ANON_AUTHOR_A="Author A"
ANON_AUTHOR_B="Author B"
ANON_AUTHOR_C="Author C"
ANON_AFFILIATION_1="Anonymous University 1"
ANON_AFFILIATION_2="Anonymous University 2"
ANON_USERNAME="anonymous"

# --- Target files ---
TARGET_FILES=(
  "$SCRIPT_DIR/README.md"
  "$SCRIPT_DIR/LICENSE.md"
  "$SCRIPT_DIR/CITATION.cff"
  "$SCRIPT_DIR/release.sh"
  "$SCRIPT_DIR/response-planner-backend/pyproject.toml"
  "$SCRIPT_DIR/response-planner-backend/setup.cfg"
  "$SCRIPT_DIR/response-planner-backend/README.md"
  "$SCRIPT_DIR/response-planner-backend/LICENSE.md"
  "$SCRIPT_DIR/response-planner-frontend/README.md"
  "$SCRIPT_DIR/docker/README.md"
  "$SCRIPT_DIR/response-planner-frontend/src/components/Footer/Footer.jsx"
  "$SCRIPT_DIR/ansible/vars.yml"
  "$SCRIPT_DIR/ansible/README.md"
)

echo "=== Deanonymizing files ==="

# Helper: escape string for use in sed pattern
sed_escape() {
  printf '%s' "$1" | sed 's/[&/\\.^$*+?(){}|[\]]/\\&/g'
}

# Helper: escape string for use in sed replacement
sed_replace_escape() {
  printf '%s' "$1" | sed 's/[&/\\]/\\&/g'
}

# Apply a sed replacement across all target files
replace_in_files() {
  local pattern="$1"
  local replacement="$2"
  local escaped_pattern
  local escaped_replacement
  escaped_pattern="$(sed_escape "$pattern")"
  escaped_replacement="$(sed_replace_escape "$replacement")"

  for f in "${TARGET_FILES[@]}"; do
    if [[ -f "$f" ]]; then
      sed -i '' "s|${escaped_pattern}|${escaped_replacement}|g" "$f"
    fi
  done
}

# --- CITATION.cff structured fields first (before generic replacements) ---
CITATION_FILE="$SCRIPT_DIR/CITATION.cff"
if [[ -f "$CITATION_FILE" ]]; then
  sed -i '' "s|family-names: AuthorA|family-names: $(sed_replace_escape "$AUTHOR_A_FAMILY")|g" "$CITATION_FILE"
  sed -i '' "s|given-names: A$|given-names: $(sed_replace_escape "$AUTHOR_A_GIVEN")|g" "$CITATION_FILE"
  sed -i '' "s|family-names: AuthorB|family-names: $(sed_replace_escape "$AUTHOR_B_FAMILY")|g" "$CITATION_FILE"
  sed -i '' "s|given-names: B$|given-names: $(sed_replace_escape "$AUTHOR_B_GIVEN")|g" "$CITATION_FILE"
  sed -i '' "s|family-names: AuthorC|family-names: $(sed_replace_escape "$AUTHOR_C_FAMILY")|g" "$CITATION_FILE"
  sed -i '' "s|given-names: C$|given-names: $(sed_replace_escape "$AUTHOR_C_GIVEN")|g" "$CITATION_FILE"
fi

# --- DockerHub user — restore in DOCKERHUB_USER="..." context and standalone ---
for f in "${TARGET_FILES[@]}"; do
  if [[ -f "$f" ]]; then
    sed -i '' "s|DOCKERHUB_USER=\"${ANON_USERNAME}\"|DOCKERHUB_USER=\"$(sed_replace_escape "$DOCKERHUB_USER_REAL")\"|g" "$f"
    sed -i '' "s|${ANON_USERNAME}/incident_response|$(sed_replace_escape "$DOCKERHUB_USER_REAL")/incident_response|g" "$f"
  fi
done

# --- Restore replacements (reverse order of anonymize.sh, longest first) ---

# GitHub username (before URLs, so URL restoration picks up the real username)
replace_in_files "$ANON_USERNAME/anonymous-repo.git" "$GITHUB_USERNAME/incident_response.git"
replace_in_files "$ANON_USERNAME/anonymous-repo" "$GITHUB_USERNAME/incident_response"

# URLs
replace_in_files "$ANON_REPO_URL_GIT" "$GITHUB_REPO_URL_GIT"
replace_in_files "$ANON_REPO_URL" "$GITHUB_REPO_URL"
replace_in_files "$ANON_WEBSITE" "$AUTHOR_A_WEBSITE"

# Affiliations
replace_in_files "$ANON_AFFILIATION_1" "$AFFILIATION_1"
replace_in_files "$ANON_AFFILIATION_2" "$AFFILIATION_2"

# Full names (before emails, since email restoration won't conflict)
replace_in_files "$ANON_AUTHOR_A" "$AUTHOR_A_FULL"
replace_in_files "$ANON_AUTHOR_B" "$AUTHOR_B_FULL"
replace_in_files "$ANON_AUTHOR_C" "$AUTHOR_C_FULL"

# Emails — we need to figure out which anonymous email maps to which real one.
# In pyproject.toml/setup.cfg the email is the personal one, in READMEs it's the academic one.
# The anonymize step replaced both with the same placeholder, so we need targeted restoration.

# First restore the personal email in pyproject.toml and setup.cfg (they have "Author A" nearby)
PYPROJECT="$SCRIPT_DIR/response-planner-backend/pyproject.toml"
SETUPCFG="$SCRIPT_DIR/response-planner-backend/setup.cfg"
if [[ -f "$PYPROJECT" ]]; then
  sed -i '' "s|$(sed_escape "$ANON_EMAIL")|$(sed_replace_escape "$AUTHOR_A_EMAIL_PERSONAL")|g" "$PYPROJECT"
fi
if [[ -f "$SETUPCFG" ]]; then
  sed -i '' "s|$(sed_escape "$ANON_EMAIL")|$(sed_replace_escape "$AUTHOR_A_EMAIL_PERSONAL")|g" "$SETUPCFG"
fi

# Remaining occurrences of ANON_EMAIL are the academic email (in READMEs)
for f in "${TARGET_FILES[@]}"; do
  if [[ -f "$f" ]]; then
    sed -i '' "s|$(sed_escape "$ANON_EMAIL")|$(sed_replace_escape "$AUTHOR_A_EMAIL_ACADEMIC")|g" "$f"
  fi
done

# --- Restore CLAUDE.md from backup ---
if [[ -f "$SCRIPT_DIR/.CLAUDE.md.bak" ]]; then
  mv "$SCRIPT_DIR/.CLAUDE.md.bak" "$SCRIPT_DIR/CLAUDE.md"
  echo "  Restored CLAUDE.md from .CLAUDE.md.bak"
fi

# --- Verification ---
echo ""
echo "=== Verification ==="

ANON_STRINGS=(
  "$ANON_AUTHOR_A"
  "$ANON_AUTHOR_B"
  "$ANON_AUTHOR_C"
  "$ANON_AFFILIATION_1"
  "$ANON_AFFILIATION_2"
  "$ANON_EMAIL"
  "$ANON_REPO_URL"
)

FOUND=0
for s in "${ANON_STRINGS[@]}"; do
  for f in "${TARGET_FILES[@]}"; do
    if [[ -f "$f" ]] && grep -qF "$s" "$f"; then
      echo "  FAIL: Found '$s' in $f"
      FOUND=1
    fi
  done
done

if [[ "$FOUND" -eq 1 ]]; then
  echo ""
  echo "ERROR: Some anonymous placeholders remain. Please check the output above."
  exit 1
else
  echo "  OK: No anonymous placeholders found in target files."
fi

echo ""
echo "=== Deanonymization complete ==="
