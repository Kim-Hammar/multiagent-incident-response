#!/usr/bin/env bash
# ---------------------------------------------------------------
# Agent integration tests — runs the LLM-backed agent test suite.
#
# Requires:
#   - GEMINI_API_KEY (and optionally other API keys) in .env
#   - Docker daemon running (for tests marked @pytest.mark.docker)
#
# Usage:
#   ./agent_tests.sh              # all agent tests
#   ./agent_tests.sh --no-docker  # skip tests that need Docker
# ---------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load API keys from .env
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.env"
    set +a
else
    echo "ERROR: .env file not found at $SCRIPT_DIR/.env"
    echo "Copy .env.example to .env and fill in your API keys."
    exit 1
fi

MARKER_EXPR=""
if [ "${1:-}" = "--no-docker" ]; then
    MARKER_EXPR="-m not docker"
    echo ">>> Skipping Docker-dependent agent tests"
fi

echo ">>> Running agent integration tests..."
cd "$SCRIPT_DIR/response-planner-backend"

# shellcheck disable=SC2086
pytest tests/test_agent_integration.py -v $MARKER_EXPR
