#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"

# Copy test fixtures into gateway build context
cp "${DIR}/test_fixtures/samba_exploit.py" "${DIR}/gateway/samba_exploit.py"

for img in gateway firewall ids server_1 server_2 server_3 server_4 server_5 server_6; do
    tag="ccs-dt-${img//_/}:latest"
    echo ">>> Building ${tag}"
    docker build -t "${tag}" "${DIR}/${img}"
done

# Clean up copied fixture
rm -f "${DIR}/gateway/samba_exploit.py"

for img in i2_server_1 i2_server_2 i2_server_3 i2_server_4 i2_server_5 i2_server_6; do
    tag="ccs-dt-${img//_/}:latest"
    echo ">>> Building ${tag}"
    docker build -t "${tag}" "${DIR}/${img}"
done

echo ">>> Building ccs-dt-attacker:latest"
docker build -t "ccs-dt-attacker:latest" "${DIR}/attacker"

echo ">>> Building ccs-dt-python-sandbox:latest"
docker build -t "ccs-dt-python-sandbox:latest" "${DIR}/python_sandbox"

echo ">>> All images built."
