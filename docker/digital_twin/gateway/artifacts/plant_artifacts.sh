#!/bin/bash
# Plant pre-populated Snort alert log on gateway
# These alerts match the EXAMPLES.SECURITY_ALERTS constant exactly

# --- Auth log (baseline cron sessions) ---
cat /opt/artifacts/auth.log >> /var/log/auth.log

mkdir -p /var/log/snort
cp /opt/artifacts/alert.log /var/log/snort/alert.log
