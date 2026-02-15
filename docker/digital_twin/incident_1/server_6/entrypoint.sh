#!/bin/bash
set -e

# Start PostgreSQL (use Debian wrapper — config is in /etc, not the data dir)
service postgresql start

# Set a strong password for remote (md5) access and create the portal database.
# Local connections use peer/trust auth (pg_hba.conf), so the password only
# matters for TCP connections — making remote brute-force implausible.
su - postgres -c "psql" <<'SQL'
ALTER USER postgres WITH PASSWORD 'Kj8mP2vL9nQ4xR7w';

-- Create the portal database and populate it (idempotent on restart)
SELECT 'CREATE DATABASE portal'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'portal')\gexec

\connect portal

CREATE TABLE IF NOT EXISTS users (
    id integer PRIMARY KEY,
    username character varying(64) NOT NULL,
    password character varying(128) NOT NULL,
    role character varying(16) DEFAULT 'user',
    email character varying(128)
);

INSERT INTO users VALUES
    (1, 'admin',      'pbkdf2:sha256:260000$salt$hashedpassword',   'admin',   'admin@company.local'),
    (2, 'operator',   'pbkdf2:sha256:260000$salt2$hashedpassword2', 'user',    'operator@company.local'),
    (3, 'backup_svc', 'pbkdf2:sha256:260000$salt3$hashedpassword3', 'service', 'backup@company.local')
ON CONFLICT (id) DO NOTHING;
SQL

# Start Samba
smbd -D
nmbd -D

# Plant post-attack artifacts (after Samba creates /var/log/samba/)
source /opt/artifacts/plant_artifacts.sh

# Keep container alive (Debian Jessie bash lacks wait -n)
tail -f /dev/null
