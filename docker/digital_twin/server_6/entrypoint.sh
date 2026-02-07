#!/bin/bash
set -e

# Start PostgreSQL (use Debian wrapper — config is in /etc, not the data dir)
service postgresql start

# Start Samba
smbd -D
nmbd -D

# Keep container alive (Debian Jessie bash lacks wait -n)
tail -f /dev/null
