#!/bin/bash
set -euo pipefail

DOCKERHUB_USER="kimham"
DOCKER_IMAGE="ccs_incident_response_planner"
PYPI_PACKAGE_DIR="ccs-response-planner-backend"

usage() {
    echo "Usage: $0 <version>"
    echo ""
    echo "Create a new release by pushing a Docker image to DockerHub"
    echo "and the Python package to PyPI."
    echo ""
    echo "Example: $0 1.0.0"
    exit 1
}

if [ $# -ne 1 ]; then
    usage
fi

VERSION="$1"

# Validate version format (semver-like: digits.digits.digits)
if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "ERROR: Version must be in semver format (e.g., 1.0.0)"
    exit 1
fi

DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Releasing version ${VERSION} ==="

# ---------- Update Python package version ----------
echo ""
echo "=== Updating Python package version to ${VERSION} ==="
VERSION_FILE="$DIR/$PYPI_PACKAGE_DIR/src/ccs_response_planner_backend/__version__.py"
echo "__version__ = '${VERSION}'" > "$VERSION_FILE"
echo "Updated $VERSION_FILE"

# ---------- Run tests ----------
echo ""
echo "=== Running backend tests ==="
cd "$DIR/$PYPI_PACKAGE_DIR"
pytest -q

echo ""
echo "=== Running frontend tests ==="
cd "$DIR/ccs-response-planner-frontend"
npm test

# ---------- Build and push Docker image ----------
echo ""
echo "=== Building Docker image ==="
cd "$DIR"
docker build -f docker/Dockerfile -t "$DOCKERHUB_USER/$DOCKER_IMAGE:$VERSION" \
    -t "$DOCKERHUB_USER/$DOCKER_IMAGE:latest" .

echo ""
echo "=== Pushing Docker image to DockerHub ==="
docker push "$DOCKERHUB_USER/$DOCKER_IMAGE:$VERSION"
docker push "$DOCKERHUB_USER/$DOCKER_IMAGE:latest"

# ---------- Build and upload Python package ----------
echo ""
echo "=== Building Python package ==="
cd "$DIR/$PYPI_PACKAGE_DIR"
rm -rf dist/
python -m build

echo ""
echo "=== Uploading Python package to PyPI ==="
twine upload dist/*

# ---------- Done ----------
echo ""
echo "=== Release ${VERSION} complete ==="
echo "  Docker: $DOCKERHUB_USER/$DOCKER_IMAGE:$VERSION"
echo "  PyPI:   ccs-response-planner-backend $VERSION"
