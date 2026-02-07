#!/bin/bash
set -e

# Start cron for CI/CD pipeline
cron

# Start SSH in foreground
exec /usr/sbin/sshd -D
