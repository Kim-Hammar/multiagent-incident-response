#!/bin/bash
set -e

# Enable IP forwarding so IDS can route between zones
echo 1 > /proc/sys/net/ipv4/ip_forward 2>/dev/null || true

# Start rsyslog for log aggregation
rsyslogd

# Start tcpdump on all interfaces, writing to pcap file
mkdir -p /var/log/tcpdump
tcpdump -i any -w /var/log/tcpdump/capture.pcap &

# Keep container alive
wait -n
