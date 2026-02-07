#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXIT_CODE=0

cleanup() {
    echo ">>> Stopping Docker containers..."
    docker compose -f "$SCRIPT_DIR/docker/docker-compose.yml" --env-file "$SCRIPT_DIR/.env" down
}
trap cleanup EXIT

echo ">>> Building and starting Docker containers..."
docker compose -f "$SCRIPT_DIR/docker/docker-compose.yml" --env-file "$SCRIPT_DIR/.env" up --build -d

echo ">>> Waiting for app to be ready (up to 30s)..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8888/api/health > /dev/null 2>&1; then
        echo ">>> App is ready after ${i}s"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo ">>> ERROR: App did not become ready within 30s"
        exit 1
    fi
    sleep 1
done

echo ">>> Loading .env for E2E tests..."
set -a
# shellcheck disable=SC1091
source "$SCRIPT_DIR/.env"
set +a

echo ">>> Installing E2E dependencies..."
cd "$SCRIPT_DIR/e2e"
npm install
npx playwright install --with-deps chromium

echo ">>> Running Playwright tests..."
npx playwright test || EXIT_CODE=$?

exit $EXIT_CODE
