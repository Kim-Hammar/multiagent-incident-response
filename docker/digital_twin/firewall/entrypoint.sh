#!/bin/bash
set -e

# Apply iptables rules
/iptables-rules.sh 2>/dev/null || true

# Keep container alive
exec sleep infinity
