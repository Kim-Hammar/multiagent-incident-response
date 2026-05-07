#!/bin/bash
cd "$(dirname "$0")/response-planner-backend" || exit 1
mypy src
