#!/bin/bash
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
cd "$(dirname "$0")/ccs-response-planner-frontend" || exit 1
npx eslint . --quiet
