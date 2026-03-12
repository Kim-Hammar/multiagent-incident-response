# Multiagent Incident Response Planning with Code Models

This repository includes to code of a **multiagent incident response system** that autonomously investigates 
security incidents and recommends optimized response actions. The system decomposes incident response into subtasks 
that are managed by a hierarchy of agents, each of which uses a large language model as the processing engine. 
At the top of the hierarchy is an orchestrator that manages the execution of subagents who investigate the incident 
by running system commands and reading log files. Based on the outcome of this investigation, the agents generate a 
code model of the response process, which is then passed to an external planning engine that computes a response plan 
with theoretical performance guarantees. 

<p align="center">
<img src="ccs-response-planner-frontend/src/components/About/method.png" alt="Method overview" width="600" />
</p>

## Demo

[Download the demo video](docs/multiagent_incident_response_demo_10_mar_short_version_anonymized_compressed.mp4)

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
| `ANTHROPIC_API_KEY` | Anthropic API key                  | `CHANGE_ME_TO_YOUR_ANTHROPIC_API_KEY` |
| `TAVILY_API_KEY`    | Tavily web search API key          | `CHANGE_ME_TO_YOUR_TAVILY_API_KEY` |
| `NVD_API_KEY`       | NIST NVD API key                   | `CHANGE_ME_TO_YOUR_NVD_API_KEY` |
| `VIRUSTOTAL_API_KEY`| VirusTotal API key                 | `CHANGE_ME_TO_YOUR_VIRUSTOTAL_API_KEY` |
| `ABUSEIPDB_API_KEY` | AbuseIPDB API key                  | `CHANGE_ME_TO_YOUR_ABUSEIPDB_API_KEY` |
| `OTX_API_KEY`       | AlienVault OTX API key             | `CHANGE_ME_TO_YOUR_OTX_API_KEY` |

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

- Python 3.11+
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

The server starts at http://localhost:8888. It serves the React app at `/` and exposes REST API endpoints under `/api`.

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
./agent_tests.sh      # Agent integration tests with real LLM calls (needs API keys)
./agent_tests.sh --no-docker  # Agent tests without Docker-dependent tests
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
3. Build and push the Docker image to DockerHub (`anonymous/ccs_incident_response_planner:<version>`)
4. Build and upload the Python package to PyPI

Ensure you are logged in to DockerHub (`docker login`) and have a PyPI token configured (`~/.pypirc`) before running the script.

## Author & Maintainer

Author A <authorA@anonymous.org>

## Copyright and license

[LICENSE](LICENSE.md)

Creative Commons

(C) 2026, Author A, Author B, Author C
