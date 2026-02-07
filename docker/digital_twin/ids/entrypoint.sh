#!/bin/bash
set -e

# Start rsyslog for log aggregation
rsyslogd

# Start tcpdump in background, writing to pcap file
mkdir -p /var/log/tcpdump
tcpdump -i eth0 -w /var/log/tcpdump/capture.pcap &

# Keep container alive
wait -n
