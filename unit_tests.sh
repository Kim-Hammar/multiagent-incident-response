#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

echo "=== Backend tests (pytest) ==="
cd "$DIR/response-planner-backend" || exit 1
pytest --cov=response_planner_backend --ignore=tests/test_agent_integration.py
backend_status=$?

echo ""
echo "=== Frontend tests (vitest) ==="
cd "$DIR/response-planner-frontend" || exit 1
npx vitest run
frontend_status=$?

if [ $backend_status -ne 0 ] || [ $frontend_status -ne 0 ]; then
  exit 1
fi
