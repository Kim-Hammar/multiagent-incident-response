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

## Docker

### Quick Start

```bash
docker compose up --build
```

The server starts at http://localhost:8888.

### Dev Commands

Run any check inside the container:

```bash
docker compose exec app ./unit_tests.sh       # Backend (pytest) + frontend (vitest) tests
docker compose exec app ./linter.sh           # Both linters (flake8 + eslint)
docker compose exec app ./python_linter.sh    # flake8 only
docker compose exec app ./js_linter.sh        # eslint only
docker compose exec app ./type-checker.sh     # mypy
```

Start the frontend dev server (hot reload on port 3005):

```bash
docker compose exec app bash -c "cd ccs-response-planner-frontend && npm start"
```

Rebuild the frontend production bundle:

```bash
docker compose exec app bash -c "cd ccs-response-planner-frontend && npm run build"
```

Open a shell inside the container:

```bash
docker compose exec app bash
```

### Rebuilding After Dependency Changes

If you change `package.json` or `pyproject.toml`, rebuild the image:

```bash
docker compose down -v && docker compose up --build
```

### Stopping and Cleanup

Stop the running containers:

```bash
docker compose down
```

Stop and remove all associated volumes (anonymous volumes for `node_modules`, `build`, `egg-info`):

```bash
docker compose down -v
```

Remove the built image as well:

```bash
docker compose down -v --rmi all
```

### Ports

| Port | Description              |
|------|--------------------------|
| 8888 | Production server        |
| 3005 | Frontend dev server      |

## Author & Maintainer

Kim Hammar <kimham@kth.se>

## Copyright and license

[LICENSE](LICENSE.md)

Creative Commons

(C) 2026, Kim Hammar
