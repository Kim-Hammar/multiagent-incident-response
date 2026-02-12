#!/bin/bash
# Runtime-only artifacts for server_3 (sourced by entrypoint after sshd starts).
# Static files (logs, .ssh, bash_history, cron, tools) are baked in by plant_static.sh.
set +e

# --- Start disguised backdoor process ---
nohup /opt/artifacts/backdoor.sh >/dev/null 2>&1 &

# --- Simulate live attacker SSH session (requires sshd to be running) ---
for i in $(seq 1 10); do
    if ss -tlnp | grep -q ':22'; then break; fi
    sleep 1
done
sshpass -p password123 ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -f admin@127.0.0.1 \
    "sudo bash -c 'while true; do sleep 3600; done'"
