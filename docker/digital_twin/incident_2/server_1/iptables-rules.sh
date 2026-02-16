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

# Allow HTTP/HTTPS/8080 from Internet to Server 2 (DMZ web server)
iptables -A FORWARD -s 10.1.0.0/24 -d 10.1.1.10 -p tcp --dport 80 -j ACCEPT
iptables -A FORWARD -s 10.1.0.0/24 -d 10.1.1.10 -p tcp --dport 443 -j ACCEPT
iptables -A FORWARD -s 10.1.0.0/24 -d 10.1.1.10 -p tcp --dport 8080 -j ACCEPT

# Allow SSH from Internet to Server 3 (jump host)
iptables -A FORWARD -s 10.1.0.0/24 -d 10.1.1.20 -p tcp --dport 22 -j ACCEPT

# Allow Server 2 to reach Server 4 PostgreSQL (DMZ -> DB)
iptables -A FORWARD -s 10.1.1.10 -d 10.1.2.10 -p tcp --dport 5432 -j ACCEPT

# Allow ICMP within DMZ and LAN for connectivity checks
iptables -A FORWARD -s 10.1.1.0/24 -d 10.1.1.0/24 -p icmp -j ACCEPT
iptables -A FORWARD -s 10.1.2.0/24 -d 10.1.2.0/24 -p icmp -j ACCEPT

# Allow ICMP from Server 2 to Server 4 (DMZ web server -> DB)
iptables -A FORWARD -s 10.1.1.10 -d 10.1.2.10 -p icmp -j ACCEPT

# Allow ICMP from Internet to DMZ (for reachability tests)
iptables -A FORWARD -s 10.1.0.0/24 -d 10.1.1.0/24 -p icmp -j ACCEPT

# Block DMZ hosts from reaching LAN hosts they shouldn't
# (Server 2 can only reach Server 4, not Server 5/6)
iptables -A FORWARD -s 10.1.1.10 -d 10.1.2.50 -j DROP
iptables -A FORWARD -s 10.1.1.10 -d 10.1.2.60 -j DROP

# Allow DMZ and LAN to reach the internet (outbound)
iptables -A FORWARD -s 10.1.1.0/24 -j ACCEPT
iptables -A FORWARD -s 10.1.2.0/24 -j ACCEPT

# NAT masquerade for outbound traffic from DMZ and LAN
iptables -t nat -A POSTROUTING -s 10.1.1.0/24 -j MASQUERADE
iptables -t nat -A POSTROUTING -s 10.1.2.0/24 -j MASQUERADE

# Log dropped packets
iptables -A FORWARD -j LOG --log-prefix "FW-DROP: " --log-level 4
