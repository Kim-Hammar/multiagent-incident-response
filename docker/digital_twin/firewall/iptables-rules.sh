#!/bin/bash
set -e

# Enable IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward

# Flush existing rules
iptables -F
iptables -t nat -F

# Default policies
iptables -P INPUT ACCEPT
iptables -P FORWARD ACCEPT
iptables -P OUTPUT ACCEPT

# Allow established connections
iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow traffic from gateway to internal network
iptables -A FORWARD -s 10.0.0.254 -d 10.0.0.0/24 -j ACCEPT

# Allow internal network traffic
iptables -A FORWARD -s 10.0.0.0/24 -d 10.0.0.0/24 -j ACCEPT

# Log dropped packets
iptables -A FORWARD -j LOG --log-prefix "FW-DROP: " --log-level 4
