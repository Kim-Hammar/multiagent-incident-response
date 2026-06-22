#!/bin/bash
set -euo pipefail

DOCKERHUB_USER="kimham"
DOCKER_IMAGE="incident_response_planner"
PYPI_PACKAGE_DIR="response-planner-backend"

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
VERSION_FILE="$DIR/$PYPI_PACKAGE_DIR/src/response_planner_backend/__version__.py"
echo "__version__ = '${VERSION}'" > "$VERSION_FILE"
echo "Updated $VERSION_FILE"

# ---------- Run tests ----------
echo ""
echo "=== Running backend tests ==="
cd "$DIR/$PYPI_PACKAGE_DIR"
pytest -q

echo ""
echo "=== Running frontend tests ==="
cd "$DIR/response-planner-frontend"
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

# ---------- Build and push digital twin images ----------
echo ""
echo "=== Building digital twin images ==="
bash "$DIR/docker/digital_twin/build.sh"

echo ""
echo "=== Pushing digital twin images to DockerHub ==="
DT_I1_IMAGES=(gateway firewall ids server_1 server_2 server_3 server_4 server_5 server_6)
for img in "${DT_I1_IMAGES[@]}"; do
    local_tag="dt-i1-${img//_/}:latest"
    remote_name="incident_response_dt_i1_${img}"
    remote_ver="$DOCKERHUB_USER/$remote_name:$VERSION"
    remote_lat="$DOCKERHUB_USER/$remote_name:latest"
    docker tag "$local_tag" "$remote_ver"
    docker tag "$local_tag" "$remote_lat"
    docker push "$remote_ver"
    docker push "$remote_lat"
    echo "  Pushed $remote_name:$VERSION"
done

DT_I2_IMAGES=(server_1 server_2 server_3 server_4 server_5 server_6)
for img in "${DT_I2_IMAGES[@]}"; do
    local_tag="dt-i2-${img//_/}:latest"
    remote_name="incident_response_dt_i2_${img}"
    remote_ver="$DOCKERHUB_USER/$remote_name:$VERSION"
    remote_lat="$DOCKERHUB_USER/$remote_name:latest"
    docker tag "$local_tag" "$remote_ver"
    docker tag "$local_tag" "$remote_lat"
    docker push "$remote_ver"
    docker push "$remote_lat"
    echo "  Pushed $remote_name:$VERSION"
done

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
for img in "${DT_I1_IMAGES[@]}"; do
    echo "  Docker: $DOCKERHUB_USER/incident_response_dt_i1_${img}:$VERSION"
done
for img in "${DT_I2_IMAGES[@]}"; do
    echo "  Docker: $DOCKERHUB_USER/incident_response_dt_i2_${img}:$VERSION"
done
echo "  PyPI:   response-planner-backend $VERSION"
