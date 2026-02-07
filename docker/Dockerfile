FROM python:3.11-slim

# Install Node.js 22 via NodeSource
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
       | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" \
       > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cache layer: npm dependencies
COPY ccs-response-planner-frontend/package.json ccs-response-planner-frontend/package-lock.json ccs-response-planner-frontend/
RUN cd ccs-response-planner-frontend && npm install

# Cache layer: pip dependencies (minimal files needed for version resolution)
COPY ccs-response-planner-backend/pyproject.toml ccs-response-planner-backend/setup.cfg ccs-response-planner-backend/setup.py ccs-response-planner-backend/
COPY ccs-response-planner-backend/src/ccs_response_planner_backend/__init__.py ccs-response-planner-backend/src/ccs_response_planner_backend/
COPY ccs-response-planner-backend/src/ccs_response_planner_backend/__version__.py ccs-response-planner-backend/src/ccs_response_planner_backend/
RUN pip install -e "ccs-response-planner-backend/.[test]"

# Copy full source
COPY . .

# Re-run pip install so egg-info discovers all sub-packages
RUN pip install -e "ccs-response-planner-backend/.[test]"

# Build frontend production bundle
RUN cd ccs-response-planner-frontend && npm run build

EXPOSE 8888 3005

CMD ["python", "ccs-response-planner-frontend/server/server.py"]
