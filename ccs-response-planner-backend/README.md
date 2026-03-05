# CCS Response Planner Backend

[![PyPI version](https://badge.fury.io/py/ccs-response-planner-backend.svg)](https://badge.fury.io/py/ccs-response-planner-backend)
![PyPI - Downloads](https://img.shields.io/pypi/dm/ccs-response-planner-backend)

Python backend for the CCS Incident Response Planner. Provides a Flask REST API, a multi-agent system for incident response planning, external security tool integrations, and a digital twin manager.

## Architecture

The backend source lives under `src/ccs_response_planner_backend/`:

- `rest_api/` — Flask app factory (`create_app`) with route blueprints for all API endpoints
- `agents/` — Multi-agent orchestration system with 10 specialized agent types
- `db/` — `DatabaseFacade` for PostgreSQL operations (users, tokens, sessions, reports, incidents)
- `planner/` — Incident response planner core logic with plan generation
- `docker_manager/` — Digital twin deployment and management (Docker container orchestration)
- `constants/` — Shared constants including API routes, database config, and example incidents

## Agents

The multi-agent system coordinates 10 specialized agents:

| Agent | Role |
|-------|------|
| `orchestrator` | Master coordinator that delegates tasks to other agents |
| `plan_manager` | Orchestrates response plan management |
| `report` | Generates incident reports from analysis |
| `report_manager` | Manages report generation workflow |
| `report_verifier` | Verifies generated reports for accuracy |
| `code` | Generates remediation code |
| `code_manager` | Manages code generation workflow |
| `code_verifier` | Verifies generated code for quality and safety |
| `plan_verifier` | Verifies response plans on the digital twin |
| `rl` | Reinforcement learning agent for policy optimization |

## External Integrations

The backend integrates with 6 external security APIs:

| Service | Description |
|---------|-------------|
| Tavily | Web search and reconnaissance |
| NVD | NIST National Vulnerability Database |
| MITRE ATT&CK | Adversary tactics, techniques, and procedures |
| VirusTotal | File and URL malware scanning |
| AbuseIPDB | IP reputation checking |
| AlienVault OTX | Open Threat Exchange intelligence |

## Database

PostgreSQL via `DatabaseFacade` (static-method facade). The schema has 6 tables:

- `management_users` — User credentials with bcrypt password hashing
- `session_tokens` — Bearer tokens for authenticated sessions
- `example_incidents` — Pre-configured incident scenarios
- `digital_twin_configs` — Docker network and container configurations (JSONB)
- `agent_reports` — Records of agent analysis and actions (JSONB)
- `planning_sessions` — User session state for incident response planning (JSONB)

## Environment Variables

A `.env` file is required at the project root. Copy from `../.env.example` and fill in your credentials. See the [root README](../README.md#configuration) for the full variable list.

## Development (Native)

```bash
pip install -e ".[test]"
pytest --cov=ccs_response_planner_backend
flake8 src tests
mypy src
tox                # Run all checks (pytest + flake8 + mypy)
```

### Agent Integration Tests

The agent integration tests exercise the full agent loop with real LLM calls (Gemini). They are excluded from the regular unit test suite and run separately:

```bash
# From the project root:
./agent_tests.sh              # All agent tests (needs GEMINI_API_KEY + Docker)
./agent_tests.sh --no-docker  # Skip tests that require a Docker daemon
```

Requires `GEMINI_API_KEY` in the root `.env` file. Tests marked `@pytest.mark.docker` also need a running Docker daemon.

## Development (Docker)

From the project root:

```bash
docker compose up --build
docker compose exec app bash -c "cd ccs-response-planner-backend && pytest --cov=ccs_response_planner_backend"
docker compose exec app bash -c "cd ccs-response-planner-backend && flake8 src tests"
docker compose exec app bash -c "cd ccs-response-planner-backend && mypy src"
```

## Author & Maintainer

Kim Hammar <kimham@kth.se>

## Copyright and license

[LICENSE](LICENSE.md)

Creative Commons

(C) 2026, Kim Hammar, Tansu Alpcan, Emil Lupu