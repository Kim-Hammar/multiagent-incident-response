#!/bin/bash
set -e

# Start SSH daemon
/usr/sbin/sshd

# Keep container alive
exec tail -f /dev/null
