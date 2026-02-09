#!/bin/bash
set -e

# Start PostgreSQL (use Debian wrapper — config is in /etc, not the data dir)
service postgresql start

# Start Samba
smbd -D
nmbd -D

# Plant post-attack artifacts (after Samba creates /var/log/samba/)
source /opt/artifacts/plant_artifacts.sh

# Keep container alive (Debian Jessie bash lacks wait -n)
tail -f /dev/null
