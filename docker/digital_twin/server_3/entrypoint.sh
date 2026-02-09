#!/bin/bash
set -e

# Start cron for CI/CD pipeline
cron

# Start SSH in daemon mode (so artifacts can open a live attacker session)
/usr/sbin/sshd

# Plant post-attack artifacts (after sshd is running)
source /opt/artifacts/plant_artifacts.sh

# Keep container alive
exec tail -f /dev/null
