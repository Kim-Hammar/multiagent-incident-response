#!/bin/bash
DIR="$(dirname "$0")"

echo "=== Backend tests (pytest) ==="
cd "$DIR/ccs-response-planner-backend" || exit 1
pytest --cov=ccs_response_planner_backend
backend_status=$?

echo ""
echo "=== Frontend tests (vitest) ==="
cd "$DIR/ccs-response-planner-frontend" || exit 1
npx vitest run
frontend_status=$?

if [ $backend_status -ne 0 ] || [ $frontend_status -ne 0 ]; then
  exit 1
fi
