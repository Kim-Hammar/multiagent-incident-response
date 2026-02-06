#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Installing backend ==="
cd "$DIR/ccs-response-planner-backend" || exit 1
pip install -e ".[test]"
backend_status=$?

echo ""
echo "=== Installing frontend ==="
cd "$DIR/ccs-response-planner-frontend" || exit 1
npm install
frontend_status=$?

if [ $backend_status -ne 0 ] || [ $frontend_status -ne 0 ]; then
  exit 1
fi
