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
Thu Feb  6 08:31:17 2026 [pid 1502] CONNECT: Client "10.0.3.3"
Thu Feb  6 08:31:17 2026 [pid 1502] [ftpuser] FAIL LOGIN: Client "10.0.3.3"
Thu Feb  6 08:31:19 2026 [pid 1503] CONNECT: Client "10.0.3.3"
Thu Feb  6 08:31:20 2026 [pid 1503] [ftpuser] FAIL LOGIN: Client "10.0.3.3"
Thu Feb  6 08:31:22 2026 [pid 1504] CONNECT: Client "10.0.3.3"
Thu Feb  6 08:31:22 2026 [pid 1504] [ftpuser] OK LOGIN: Client "10.0.3.3"
Thu Feb  6 08:31:23 2026 [pid 1504] [ftpuser] OK DOWNLOAD: Client "10.0.3.3", "/srv/backups/db-backup-20260206.tar.gz", 1497201 bytes, 14523.88Kbyte/sec
Thu Feb  6 08:31:24 2026 [pid 1504] [ftpuser] OK DOWNLOAD: Client "10.0.3.3", "/srv/backups/db-backup-20260205.tar.gz", 1482956 bytes, 14301.12Kbyte/sec
Thu Feb  6 08:31:24 2026 [pid 1504] [ftpuser] OK LOGOUT: Client "10.0.3.3"
VSFTPLOG

# Seed matching xferlog entries (standard wu-ftpd format)
cat >> /var/log/xferlog << 'XFERLOG'
Thu Feb  5 02:00:04 2026 1 10.0.2.1 1482956 /srv/backups/db-backup-20260205.tar.gz b _ i r ftpuser ftp 0 * c
Thu Feb  6 02:00:03 2026 1 10.0.2.1 1497201 /srv/backups/db-backup-20260206.tar.gz b _ i r ftpuser ftp 0 * c
Thu Feb  6 08:31:23 2026 1 10.0.3.3 1497201 /srv/backups/db-backup-20260206.tar.gz b _ o r ftpuser ftp 0 * c
Thu Feb  6 08:31:24 2026 1 10.0.3.3 1482956 /srv/backups/db-backup-20260205.tar.gz b _ o r ftpuser ftp 0 * c
XFERLOG

# Seed auth.log entries — PAM authentication for FTP logins
cat >> /var/log/auth.log << 'AUTHLOG'
Feb  5 02:00:03 server2 vsftpd[1201]: pam_unix(vsftpd:auth): authentication failure; logname= uid=0 euid=0 tty=ftp ruser=ftpuser rhost=10.0.2.1 user=ftpuser
Feb  5 02:00:03 server2 vsftpd[1201]: pam_unix(vsftpd:session): session opened for user ftpuser by (uid=0)
Feb  5 02:00:04 server2 vsftpd[1201]: pam_unix(vsftpd:session): session closed for user ftpuser
Feb  6 02:00:02 server2 vsftpd[1318]: pam_unix(vsftpd:session): session opened for user ftpuser by (uid=0)
Feb  6 02:00:03 server2 vsftpd[1318]: pam_unix(vsftpd:session): session closed for user ftpuser
Feb  6 08:31:17 server2 vsftpd[1502]: pam_unix(vsftpd:auth): authentication failure; logname= uid=0 euid=0 tty=ftp ruser=ftpuser rhost=10.0.3.3 user=ftpuser
Feb  6 08:31:19 server2 vsftpd[1503]: pam_unix(vsftpd:auth): authentication failure; logname= uid=0 euid=0 tty=ftp ruser=ftpuser rhost=10.0.3.3 user=ftpuser
Feb  6 08:31:22 server2 vsftpd[1504]: pam_unix(vsftpd:session): session opened for user ftpuser by (uid=0)
Feb  6 08:31:24 server2 vsftpd[1504]: pam_unix(vsftpd:session): session closed for user ftpuser
AUTHLOG

# Start vsftpd in foreground
exec vsftpd /etc/vsftpd.conf
