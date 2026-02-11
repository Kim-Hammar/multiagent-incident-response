#!/bin/bash
set -e

# Create samba user
useradd -M -s /usr/sbin/nologin backup 2>/dev/null || true
echo -e "backup123\nbackup123" | smbpasswd -a -s backup 2>/dev/null || true

# Set up nightly rsync backup cron job
echo "0 2 * * * rsync -a /srv/shared/ /srv/backups/" > /etc/cron.d/nightly-backup
chmod 644 /etc/cron.d/nightly-backup

# Start services
cron
smbd
nmbd

# Keep container alive
exec tail -f /dev/null
