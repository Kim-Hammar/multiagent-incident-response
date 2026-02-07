#!/bin/bash
set -e

# Create vsftpd required directory
mkdir -p /var/run/vsftpd/empty

# Start cron for nightly backups
cron

# Start vsftpd in foreground
exec vsftpd /etc/vsftpd.conf
