# Docker

This directory contains the Docker configuration for the Incident Response Planner. It defines two services: the application (Python backend + React frontend) and a PostgreSQL database.

## Services

- `app` ([Dockerfile](./Dockerfile)): the main application container. Builds from `python:3.11-slim`, installs Node.js 22, the Python backend, and the React frontend. Serves the production bundle on port 8888.
- `db`: PostgreSQL 16 (Alpine) for user and session storage. Data is persisted in a named volume. Only accessible within the Docker network (no host port mapping).

## Prerequisites

- Docker and Docker Compose v2
- A configured `../.env` file (copy from `../.env.example` and set passwords)

## Quick Start

```bash
cd docker
make up
```

The server starts at http://localhost:8888.

## Useful Commands

```bash
make build    # Build Docker images
make up       # Start all containers in the background
make down     # Stop and remove containers
make clean    # Stop containers and remove volumes and images
make logs     # Tail container logs
make shell    # Open a shell inside the app container
make tests    # Run backend and frontend tests inside the container
make lint     # Run all linters inside the container
make format   # Run Prettier formatter inside the container
make rebuild  # Full rebuild (remove volumes, rebuild images, start)
make dt-build # Build all digital twin images
make dt-clean # Remove all digital twin images
make help     # Show all available targets
```

## Ports

| Port | Description         |
|------|---------------------|
| 8888 | Production server   |
| 3005 | Frontend dev server |

## Author & Maintainer

Kim Hammar <kimham@kth.se>

## Copyright and license

[LICENSE](../LICENSE.md)

Creative Commons

(C) 2026, Kim Hammar, Tansu Alpcan, Emil C. Lupu
