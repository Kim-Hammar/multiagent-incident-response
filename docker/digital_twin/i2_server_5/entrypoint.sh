#!/bin/bash
set -e

# Start dnsmasq
dnsmasq

# Start SSH daemon
/usr/sbin/sshd 2>/dev/null || true

# Keep container alive
exec tail -f /dev/null
