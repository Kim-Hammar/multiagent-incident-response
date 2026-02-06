# CCS Incident Response Planner

LLM-based incident response planner for cyber-security. Monorepo with two sub-projects:

- `ccs-response-planner-backend/` — Python backend (Flask REST API + planner logic)
- `ccs-response-planner-frontend/` — React frontend (Vite + JSX)

## Prerequisites

- Python 3.10+
- Node.js 22+

## Build the Frontend

```bash
cd ccs-response-planner-frontend
npm install
npm run build
```

This produces a production bundle in `ccs-response-planner-frontend/build/`.

## Install the Backend

```bash
cd ccs-response-planner-backend
pip install -e ".[test]"
```

## Start the Server

The backend serves the frontend's production build as static files. Make sure you have built the frontend first.

```bash
cd ccs-response-planner-frontend
python server/server.py
```

The server starts at http://localhost:8888. It serves the React app at `/` and exposes API endpoints at `/api/health` and `/api/plan`.

## Development

Run the frontend dev server (with hot reload) on port 3005:

```bash
cd ccs-response-planner-frontend
npm start
```

## Tests and Checks

From the project root:

```bash
./unit_tests.sh       # Backend (pytest) + frontend (vitest) tests
./python_linter.sh    # flake8
./js_linter.sh        # eslint
./linter.sh           # Both linters
./type-checker.sh     # mypy
```

## Author & Maintainer

Kim Hammar <kimham@kth.se>

## Copyright and license

[LICENSE](LICENSE.md)

Creative Commons

(C) 2026, Kim Hammar
