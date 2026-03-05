#!/bin/bash
set -e

# Create vsftpd required directory
mkdir -p /var/run/vsftpd/empty

# Start rsyslog for auth.log
rsyslogd

# Start cron for nightly backups
cron

# Seed realistic vsftpd.log entries — normal backup activity from Server 1
cat >> /var/log/vsftpd.log << 'VSFTPLOG'
Thu Feb  5 02:00:03 2026 [pid 1201] CONNECT: Client "10.0.2.1"
Thu Feb  5 02:00:03 2026 [pid 1201] [ftpuser] OK LOGIN: Client "10.0.2.1"
Thu Feb  5 02:00:04 2026 [pid 1201] [ftpuser] OK UPLOAD: Client "10.0.2.1", "/srv/backups/db-backup-20260205.tar.gz", 1482956 bytes, 12847.33Kbyte/sec
Thu Feb  5 02:00:04 2026 [pid 1201] [ftpuser] OK LOGOUT: Client "10.0.2.1"
Thu Feb  6 02:00:02 2026 [pid 1318] CONNECT: Client "10.0.2.1"
Thu Feb  6 02:00:02 2026 [pid 1318] [ftpuser] OK LOGIN: Client "10.0.2.1"
Thu Feb  6 02:00:03 2026 [pid 1318] [ftpuser] OK UPLOAD: Client "10.0.2.1", "/srv/backups/db-backup-20260206.tar.gz", 1497201 bytes, 13104.55Kbyte/sec
Thu Feb  6 02:00:03 2026 [pid 1318] [ftpuser] OK LOGOUT: Client "10.0.2.1"
VSFTPLOG

# Create dummy backup files matching the seeded log entries
dd if=/dev/urandom bs=1k count=1448 2>/dev/null | gzip > /srv/backups/db-backup-20260205.tar.gz
dd if=/dev/urandom bs=1k count=1462 2>/dev/null | gzip > /srv/backups/db-backup-20260206.tar.gz
chown ftpuser:ftpuser /srv/backups/db-backup-2026020*.tar.gz

# Seed matching xferlog entries (standard wu-ftpd format)
cat >> /var/log/xferlog << 'XFERLOG'
Thu Feb  5 02:00:04 2026 1 10.0.2.1 1482956 /srv/backups/db-backup-20260205.tar.gz b _ i r ftpuser ftp 0 * c
Thu Feb  6 02:00:03 2026 1 10.0.2.1 1497201 /srv/backups/db-backup-20260206.tar.gz b _ i r ftpuser ftp 0 * c
XFERLOG

# Seed auth.log entries — PAM authentication for FTP logins
cat >> /var/log/auth.log << 'AUTHLOG'
Feb  5 02:00:03 server2 vsftpd[1201]: pam_unix(vsftpd:auth): authentication failure; logname= uid=0 euid=0 tty=ftp ruser=ftpuser rhost=10.0.2.1 user=ftpuser
Feb  5 02:00:03 server2 vsftpd[1201]: pam_unix(vsftpd:session): session opened for user ftpuser by (uid=0)
Feb  5 02:00:04 server2 vsftpd[1201]: pam_unix(vsftpd:session): session closed for user ftpuser
Feb  6 02:00:02 server2 vsftpd[1318]: pam_unix(vsftpd:session): session opened for user ftpuser by (uid=0)
Feb  6 02:00:03 server2 vsftpd[1318]: pam_unix(vsftpd:session): session closed for user ftpuser
AUTHLOG

# Start vsftpd in foreground
exec vsftpd /etc/vsftpd.conf
