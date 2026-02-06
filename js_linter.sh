#!/bin/bash
cd "$(dirname "$0")/ccs-response-planner-frontend" || exit 1
npx eslint . --quiet
