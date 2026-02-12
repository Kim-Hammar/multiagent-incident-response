#!/bin/bash
# Plant static post-attack artifacts for gateway at Docker build time.
# These are baked into the image so they are always present.

# --- Auth log (baseline cron sessions) ---
cat /opt/artifacts/auth.log > /var/log/auth.log

# --- Snort alert log (matches EXAMPLES.SECURITY_ALERTS exactly) ---
mkdir -p /var/log/snort
cp /opt/artifacts/alert.log /var/log/snort/alert.log
ln -sf /var/log/snort/alert.log /var/log/snort/alert
