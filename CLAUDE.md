# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LLM-based incident response planner for cyber-security. Monorepo with two sub-projects:
- **`response-planner-backend/`** — Python backend (REST API + planner logic)
- **`response-planner-frontend/`** — React frontend (Vite + JSX)

The backend serves the frontend's production build as static files via a REST API on port 8888. The frontend dev server runs on port 3005.

## Backend Commands

All commands run from `response-planner-backend/`.

```bash
# Install (editable with dev deps)
pip install -e ".[test]"

# Run tests with coverage
pytest --cov=response_planner_backend

# Run a single test
pytest tests/test_foo.py::test_name -v

# Lint
flake8 src tests

# Type check
mypy src

# Run all checks via tox (tests + flake8 + mypy)
tox

# Start the backend server
python ../response-planner-frontend/server/server.py
```

Python 3.11+ required. Flake8 max line length is 120 chars.

## Frontend Commands

All commands run from `response-planner-frontend/`.

```bash
npm install
npm start          # Dev server on http://localhost:3005
npm run build      # Production build to build/
npm test           # Vitest
npx eslint . --quiet  # Lint
npm run format     # Prettier format
```

## Architecture

### Backend (`response-planner-backend/src/response_planner_backend/`)

- `rest_api/` — Flask app factory (`create_app`) + `start_server` entry point
- `planner/` — `IncidentResponsePlanner` class with `generate_plan()` method
- `constants/` — Shared constants (`API_PREFIX`, `HEALTH_ROUTE`, `PLAN_ROUTE`, etc.)

The server entry point is `response-planner-frontend/server/server.py`, which imports `response_planner_backend.rest_api` and starts the server with the frontend build as the static folder.

### Frontend (`response-planner-frontend/src/`)

React app using React Router for navigation. Uses Bootstrap 4 (loaded via CDN in `index.html`).

- `App.jsx` — Root component with route definitions
- `components/Common/constants.js` — Route path and API URL constants
- `components/MainContainer/MainContainer.jsx` — Layout wrapper with navbar and `<Outlet />`
- `components/MainContainer/Home/Home.jsx` — Home page component
- `components/MainContainer/NotFound/NotFound.jsx` — 404 page component

### Dependency Management

Backend dependencies are declared in four places that **must be kept in sync**:
- `pyproject.toml` — `dependencies` (pinned versions, e.g. `==1.23.5`) and `[project.optional-dependencies] test`
- `setup.cfg` — `install_requires` (minimum versions, e.g. `>=1.23.5`) and `[options.extras_require] testing`
- `requirements.txt` — pinned runtime deps (mirrors `pyproject.toml` `dependencies`)
- `requirements_dev.txt` — includes `-r requirements.txt` plus dev/test deps

When adding or updating a Python dependency, update **all four** locations.

### Session Persistence

The Response Planner supports session persistence via the `planning_sessions` table:
- Each user can have one active session at a time
- Sessions store conversation history, pending proposals, incident inputs, and agent config
- On refresh, the frontend restores the active session (if any)
- Sessions are auto-cancelled when a new session is created
- Completed sessions are marked with status='completed' and remain in the DB for reference

### UI Patterns

- **Alert auto-dismiss:** All alert/notification banners in the frontend must auto-dismiss after 3 seconds using a `useEffect` with `setTimeout`. Users can still manually dismiss them before the timer fires.

### Testing Workflow

- **Do not run tests automatically after every code change.** Only run tests (pytest, vitest) when explicitly asked by the user. Linting (flake8, eslint, prettier) is fine to run for verification.

### Code Style

- **Backend:** flake8 (120 char lines), mypy strict mode, pytest for tests
- **Frontend:** ESLint (flat config with react/promise/node plugins) + Prettier (no semicolons, single quotes, 2-space tabs, 100 char width, no trailing commas)

### Python Docstring Format

All Python docstrings must use the reST `:param` / `:return` style with triple-quoted multi-line blocks:

```python
def create_app(static_folder: str) -> Flask:
    """
    Create and configure the Flask application.

    :param static_folder: path to the static frontend build directory
    :return: a configured Flask app instance
    """
```

- Opening `"""` on its own line after the `def`
- Description on the next line
- `:param name:` for each parameter
- `:return:` for the return value
- Closing `"""` on its own line
