#!/bin/bash
set -e

# Start Redis
redis-server /etc/redis/redis.conf --daemonize yes

# Start SSH
/usr/sbin/sshd

# Start API server in foreground
exec python3 /opt/app.py
