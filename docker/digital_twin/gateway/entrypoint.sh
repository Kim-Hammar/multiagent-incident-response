#!/bin/bash
set -e

mkdir -p /var/log/snort

# Start Snort in IDS mode on eth0
snort -c /etc/snort/snort.conf -i eth0 -D -l /var/log/snort 2>/dev/null || true

# Keep container alive
exec tail -f /var/log/snort/alert.log 2>/dev/null || exec sleep infinity
