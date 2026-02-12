#!/bin/bash
# Runtime-only artifacts for server_6 (sourced by entrypoint after services start).
# Static files (logs, .ssh, bash_history, cron, exfil) are baked in by plant_static.sh.
set +e

# --- Start disguised backdoor process ---
nohup /opt/artifacts/backdoor.sh >/dev/null 2>&1 &
