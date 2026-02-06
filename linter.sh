#!/bin/bash
DIR="$(dirname "$0")"

echo "=== Python linter (flake8) ==="
"$DIR/python_linter.sh"
python_status=$?

echo ""
echo "=== JS linter (eslint) ==="
"$DIR/js_linter.sh"
js_status=$?

if [ $python_status -ne 0 ] || [ $js_status -ne 0 ]; then
  exit 1
fi
