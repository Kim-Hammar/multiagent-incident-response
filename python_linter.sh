#!/bin/bash
cd "$(dirname "$0")/response-planner-backend" || exit 1
flake8 src tests
