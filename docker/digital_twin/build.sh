#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"

# --- Incident 1 images ---
# Copy test fixtures into gateway build context
cp "${DIR}/incident_1/test_fixtures/samba_exploit.py" \
   "${DIR}/incident_1/gateway/samba_exploit.py"

for img in gateway firewall log_collector server_1 server_2 server_3 server_4 server_5 server_6; do
    tag="dt-i1-${img//_/}:latest"
    echo ">>> Building ${tag}"
    docker build -t "${tag}" "${DIR}/incident_1/${img}"
done

# Clean up copied fixture
rm -f "${DIR}/incident_1/gateway/samba_exploit.py"

# --- Incident 2 images ---
for img in server_1 server_2 server_3 server_4 server_5 server_6; do
    tag="dt-i2-${img//_/}:latest"
    echo ">>> Building ${tag}"
    docker build -t "${tag}" "${DIR}/incident_2/${img}"
done

# --- Shared images ---
echo ">>> Building dt-attacker:latest"
docker build -t "dt-attacker:latest" "${DIR}/shared/attacker"

echo ">>> Building dt-python-sandbox:latest"
docker build -t "dt-python-sandbox:latest" "${DIR}/shared/python_sandbox"

echo ">>> All images built."
