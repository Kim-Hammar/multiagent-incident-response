#!/bin/bash
set -e

# Start PostgreSQL (use Debian wrapper — config is in /etc, not the data dir)
service postgresql start

# Set a strong password for remote (md5) access and create the portal database.
# Local connections use peer/trust auth (pg_hba.conf), so the password only
# matters for TCP connections — making remote brute-force implausible.
# NOTE: PostgreSQL 9.4 lacks \gexec and ON CONFLICT, so use separate commands.
su - postgres -c "psql -c \"ALTER USER postgres WITH PASSWORD 'Kj8mP2vL9nQ4xR7w';\""
su - postgres -c "createdb portal" 2>/dev/null || true
su - postgres -c "psql -d portal" <<'SQL'
CREATE TABLE IF NOT EXISTS users (
    id integer PRIMARY KEY,
    username character varying(64) NOT NULL,
    password character varying(128) NOT NULL,
    role character varying(16) DEFAULT 'user',
    email character varying(128)
);

INSERT INTO users SELECT 1, 'admin',      'pbkdf2:sha256:260000$salt$hashedpassword',   'admin',   'admin@company.local'
    WHERE NOT EXISTS (SELECT 1 FROM users WHERE id = 1);
INSERT INTO users SELECT 2, 'operator',   'pbkdf2:sha256:260000$salt2$hashedpassword2', 'user',    'operator@company.local'
    WHERE NOT EXISTS (SELECT 1 FROM users WHERE id = 2);
INSERT INTO users SELECT 3, 'backup_svc', 'pbkdf2:sha256:260000$salt3$hashedpassword3', 'service', 'backup@company.local'
    WHERE NOT EXISTS (SELECT 1 FROM users WHERE id = 3);
SQL

# Start Samba
smbd -D
nmbd -D

# Plant post-attack artifacts (after Samba creates /var/log/samba/)
source /opt/artifacts/plant_artifacts.sh

# Keep container alive (Debian Jessie bash lacks wait -n)
tail -f /dev/null
