#!/usr/bin/env bash
#
# anonymize.sh — Replace real identity strings with anonymous placeholders.
# Reads real values from .env, applies sed replacements in-place.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found. Cannot anonymize without real values."
  exit 1
fi

# Source .env to get real identity values
set -a
source "$ENV_FILE"
set +a

# --- Anonymous placeholders (not sensitive, safe to have in script) ---
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
  "$SCRIPT_DIR/ccs-response-planner-backend/pyproject.toml"
  "$SCRIPT_DIR/ccs-response-planner-backend/setup.cfg"
  "$SCRIPT_DIR/ccs-response-planner-backend/README.md"
  "$SCRIPT_DIR/ccs-response-planner-backend/LICENSE.md"
  "$SCRIPT_DIR/ccs-response-planner-frontend/README.md"
  "$SCRIPT_DIR/docker/README.md"
  "$SCRIPT_DIR/ccs-response-planner-frontend/src/components/Footer/Footer.jsx"
  "$SCRIPT_DIR/ansible/vars.yml"
  "$SCRIPT_DIR/ansible/README.md"
)

echo "=== Anonymizing files ==="

# Helper: escape string for use in sed pattern
sed_escape() {
  printf '%s' "$1" | sed 's/[&/\\.^$*+?(){}|[\]]/\\&/g'
}

# Helper: escape string for use in sed replacement
sed_replace_escape() {
  printf '%s' "$1" | sed 's/[&/\\]/\\&/g'
}

# Apply a sed replacement across all target files (longest-first ordering is
# handled by the order of calls below).
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

# --- Apply replacements (longest / most specific first) ---

# URLs (longest first to prevent partial matches)
replace_in_files "$GITHUB_REPO_URL_GIT" "$ANON_REPO_URL_GIT"
replace_in_files "$GITHUB_REPO_URL" "$ANON_REPO_URL"
replace_in_files "$AUTHOR_A_WEBSITE" "$ANON_WEBSITE"

# Emails (before names, since emails contain name fragments)
replace_in_files "$AUTHOR_A_EMAIL_PERSONAL" "$ANON_EMAIL"
replace_in_files "$AUTHOR_A_EMAIL_ACADEMIC" "$ANON_EMAIL"

# Full names (before individual name parts)
replace_in_files "$AUTHOR_A_FULL" "$ANON_AUTHOR_A"
replace_in_files "$AUTHOR_B_FULL" "$ANON_AUTHOR_B"
replace_in_files "$AUTHOR_C_FULL" "$ANON_AUTHOR_C"

# Affiliations
replace_in_files "$AFFILIATION_1" "$ANON_AFFILIATION_1"
replace_in_files "$AFFILIATION_2" "$ANON_AFFILIATION_2"

# GitHub username (after full URLs have been replaced)
replace_in_files "$GITHUB_USERNAME" "$ANON_USERNAME"

# DockerHub user — in DOCKERHUB_USER="..." context and standalone
for f in "${TARGET_FILES[@]}"; do
  if [[ -f "$f" ]]; then
    sed -i '' "s|DOCKERHUB_USER=\"$(sed_escape "$DOCKERHUB_USER_REAL")\"|DOCKERHUB_USER=\"${ANON_USERNAME}\"|g" "$f"
    sed -i '' "s|$(sed_escape "$DOCKERHUB_USER_REAL")/|${ANON_USERNAME}/|g" "$f"
  fi
done

# --- CITATION.cff structured fields (family-names / given-names) ---
CITATION_FILE="$SCRIPT_DIR/CITATION.cff"
if [[ -f "$CITATION_FILE" ]]; then
  sed -i '' "s|family-names: $(sed_escape "$AUTHOR_A_FAMILY")|family-names: AuthorA|g" "$CITATION_FILE"
  sed -i '' "s|given-names: $(sed_escape "$AUTHOR_A_GIVEN")|given-names: A|g" "$CITATION_FILE"
  sed -i '' "s|family-names: $(sed_escape "$AUTHOR_B_FAMILY")|family-names: AuthorB|g" "$CITATION_FILE"
  sed -i '' "s|given-names: $(sed_escape "$AUTHOR_B_GIVEN")|given-names: B|g" "$CITATION_FILE"
  sed -i '' "s|family-names: $(sed_escape "$AUTHOR_C_FAMILY")|family-names: AuthorC|g" "$CITATION_FILE"
  sed -i '' "s|given-names: $(sed_escape "$AUTHOR_C_GIVEN")|given-names: C|g" "$CITATION_FILE"
fi

# --- Remove CLAUDE.md (backup for deanonymize to restore) ---
if [[ -f "$SCRIPT_DIR/CLAUDE.md" ]]; then
  mv "$SCRIPT_DIR/CLAUDE.md" "$SCRIPT_DIR/.CLAUDE.md.bak"
  echo "  Backed up CLAUDE.md -> .CLAUDE.md.bak"
fi

# --- Verification ---
echo ""
echo "=== Verification ==="

# Build a grep pattern from all real identity strings
VERIFY_STRINGS=(
  "$AUTHOR_A_FULL"
  "$AUTHOR_B_FULL"
  "$AUTHOR_C_FULL"
  "$AUTHOR_A_FAMILY"
  "$AUTHOR_B_FAMILY"
  "$AUTHOR_C_FAMILY"
  "$AUTHOR_A_EMAIL_ACADEMIC"
  "$AUTHOR_A_EMAIL_PERSONAL"
  "$AUTHOR_A_WEBSITE"
  "$GITHUB_REPO_URL"
  "$GITHUB_USERNAME"
  "$DOCKERHUB_USER_REAL"
  "$AFFILIATION_1"
  "$AFFILIATION_2"
)

FOUND=0
for s in "${VERIFY_STRINGS[@]}"; do
  for f in "${TARGET_FILES[@]}"; do
    if [[ -f "$f" ]] && grep -qF "$s" "$f"; then
      echo "  FAIL: Found '$s' in $f"
      FOUND=1
    fi
  done
done

if [[ "$FOUND" -eq 1 ]]; then
  echo ""
  echo "ERROR: Some identifying strings remain. Please check the output above."
  exit 1
else
  echo "  OK: No identifying strings found in target files."
fi

echo ""
echo "=== Anonymization complete ==="
