#!/bin/bash
cd "$(dirname "$0")/ccs-response-planner-backend" || exit 1
mypy src
