# CCS Response Planner Backend

[![PyPI version](https://badge.fury.io/py/ccs-response-planner-backend.svg)](https://badge.fury.io/py/ccs-response-planner-backend)
![PyPI - Downloads](https://img.shields.io/pypi/dm/ccs-response-planner-backend)

Python backend for the CCS Incident Response Planner. Provides a Flask REST API and LLM-based planner logic.

## Development (Native)

```bash
pip install -e ".[test]"
pytest --cov=ccs_response_planner_backend
flake8 src tests
mypy src
```

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