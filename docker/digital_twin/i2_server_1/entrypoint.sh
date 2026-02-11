#!/bin/bash
set -e

# Apply iptables rules
/iptables-rules.sh 2>/dev/null || true

# Plant Suricata alert log artifact
mkdir -p /var/log/suricata
cp /opt/artifacts/fast.log /var/log/suricata/fast.log

# Keep container alive
exec sleep infinity
