#!/bin/bash
set -e

# Note: IP forwarding is enabled via Docker sysctls config
# (net.ipv4.ip_forward=1), so no /proc/sys write is needed.

# Flush existing rules
iptables -F
iptables -t nat -F

# Default policies — DROP all forwarded traffic by default
iptables -P INPUT ACCEPT
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# Allow established and related connections (return traffic)
iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT

# Only allow perimeter traffic to Server 2 (FTP) and Server 3 (SSH)
iptables -A FORWARD -s 10.0.1.0/24 -d 10.0.2.2 -j ACCEPT
iptables -A FORWARD -s 10.0.1.0/24 -d 10.0.3.3 -j ACCEPT

# Log dropped packets
iptables -A FORWARD -j LOG --log-prefix "FW-DROP: " --log-level 4
