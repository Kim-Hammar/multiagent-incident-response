# Incident Response Planner

<a href="https://github.com/Kim-Hammar/ccs26_incident_response">
    <img src="https://img.shields.io/badge/-github-teal?logo=github" alt="github">
</a>
<a href="https://pypi.org/project/ccs-response-planner-backend/">
    <img src="https://img.shields.io/pypi/dm/ccs-response-planner-backend" alt="PyPI downloads">
</a>
<a href="https://codecov.io/gh/Kim-Hammar/ccs26_incident_response">
    <img src="https://codecov.io/gh/Kim-Hammar/ccs26_incident_response/graph/badge.svg" alt="codecov">
</a>
<a href="https://github.com/Kim-Hammar/ccs26_incident_response/actions/workflows/ci.yml">
    <img src="https://github.com/Kim-Hammar/ccs26_incident_response/actions/workflows/ci.yml/badge.svg" alt="CI">
</a>

LLM-based incident response planner for cyber-security. Monorepo with two sub-projects:

- `ccs-response-planner-backend/` — Python backend (Flask REST API + planner logic)
- `ccs-response-planner-frontend/` — React frontend (Vite + JSX)

## About

Incident response refers to the coordinated actions taken to contain, mitigate, and recover from cyberattacks. Today, incident response is largely a manual process that is slow, labor-intensive, and requires specialized skills. To address this, an emerging direction of research is to leverage the security knowledge encoded in large language models (LLMs) as decision support.

This tool implements a novel approach: instead of using the LLM to directly generate response actions from system logs, we use it to generate a **code model** of the response process as Python code. This model allows us to leverage standard planning algorithms (e.g., tree search) to efficiently compute an effective response plan through simulation. The code model is then refined through **in-context learning (ICL)** based on feedback from security operators.

<p align="center">
<img src="docs/method.png" alt="Method overview" width="600" />
</p>

## Configuration

Before building or deploying, copy the example environment file and edit it with your credentials:

```bash
cp .env.example .env
```

The `.env` file contains the following settings:

| Variable            | Description                        | Default                          |
|---------------------|------------------------------------|----------------------------------|
| `POSTGRES_DB`       | PostgreSQL database name           | `ccs`                            |
| `POSTGRES_USER`     | PostgreSQL user                    | `ccs`                            |
| `POSTGRES_PASSWORD` | PostgreSQL password                | `CHANGE_ME_TO_A_STRONG_PASSWORD` |
| `ADMIN_USERNAME`    | Application admin login username   | `admin`                          |
| `ADMIN_PASSWORD`    | Application admin login password   | `CHANGE_ME_TO_A_STRONG_PASSWORD` |
| `GEMINI_API_KEY`    | Google Gemini API key              | `CHANGE_ME_TO_YOUR_GEMINI_API_KEY` |

The admin credentials are used to seed the initial login account on first startup. Make sure to set strong passwords before deploying.

To deploy remotely with Ansible, add your target hosts to `ansible/inventory.yml` under the `servers` group:

```yaml
servers:
  hosts:
    web1.example.com:
      ansible_user: ubuntu
```

Then run the playbook with `--limit servers`. See [`ansible/README.md`](ansible/README.md) for full details.

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

Docker configuration is in `docker/`. See [`docker/README.md`](docker/README.md) for full details.

Quick start:

```bash
cd docker
make up
```

The server starts at http://localhost:8888.

## Ansible

An Ansible playbook is provided in `ansible/` to automate deployment on Ubuntu/Debian hosts. It installs Docker, clones the repo, and starts the app. See [`ansible/README.md`](ansible/README.md) for full details.

Quick start:

```bash
cd ansible
ansible-playbook playbook.yml -i inventory.yml --limit local
```

## Release Management

To create a new release, run the `release.sh` script with a semver version number:

```bash
./release.sh 1.0.0
```

This will:

1. Update the Python package version in `__version__.py`
2. Run backend and frontend tests
3. Build and push the Docker image to DockerHub (`kimham/ccs_incident_response_planner:<version>`)
4. Build and upload the Python package to PyPI

Ensure you are logged in to DockerHub (`docker login`) and have a PyPI token configured (`~/.pypirc`) before running the script.

## Author & Maintainer

Kim Hammar <kimham@kth.se>

## Copyright and license

[LICENSE](LICENSE.md)

Creative Commons

(C) 2026, Kim Hammar, Tansu Alpcan, Emil Lupu
