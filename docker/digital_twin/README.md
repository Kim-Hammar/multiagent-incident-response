# Digital Twin Docker Images

Custom Docker images for the CCS incident response digital twin. Images are organised per incident with a shared set of common images.

## Directory Structure

```
docker/digital_twin/
├── shared/            # Images used across all incidents
│   ├── attacker/
│   └── python_sandbox/
├── incident_1/        # Incident 1 — SaaS company multi-stage attack
│   ├── test_fixtures/
│   ├── gateway/
│   ├── firewall/
│   ├── ids/
│   └── server_1/ .. server_6/
├── incident_2/        # Incident 2 — Tomcat RCE + PostgreSQL lateral movement
│   └── server_1/ .. server_6/
├── build.sh
└── README.md
```

## Naming Convention

| Scope | Image name pattern | Container ID pattern |
|---|---|---|
| Shared | `ccs-dt-attacker` | `i1_attacker` / `i2_attacker` (per config) |
| Incident 1 | `ccs-dt-i1-{component}` | `i1_{component}` |
| Incident 2 | `ccs-dt-i2-{component}` | `i2_{component}` |

## Incident 1 — SaaS Company Infrastructure

A **mid-size SaaS company** infrastructure: web frontend, customer-facing API, database, mail, backups, and CI/CD — all behind a gateway with Snort IDS.

| Image | Host | Base | Services | Vulnerability |
|-------|------|------|----------|---------------|
| `ccs-dt-attacker` | Attacker (10.0.1.10) | debian:bookworm-slim | nmap, hydra, smbclient, impacket | — |
| `ccs-dt-i1-gateway` | Gateway (10.0.1.254) | ubuntu:22.04 | Snort IDS, pentest tools | — |
| `ccs-dt-i1-firewall` | Firewall (10.0.1.253) | ubuntu:22.04 | iptables, IP forwarding | — |
| `ccs-dt-i1-logcollector` | Log Collector (10.0.1.252) | ubuntu:22.04 | rsyslog, tcpdump | — |
| `ccs-dt-i1-server1` | Server 1 (10.0.2.1) | debian:bullseye-slim | Nginx, PHP-FPM, dnsmasq | SQL injection |
| `ccs-dt-i1-server2` | Server 2 (10.0.2.2) | debian:bullseye-slim | vsftpd, cron backups | — |
| `ccs-dt-i1-server3` | Server 3 (10.0.3.3) | ubuntu:20.04 | OpenSSH, cron CI/CD | Weak SSH password |
| `ccs-dt-i1-server4` | Server 4 (10.0.3.4) | debian:bullseye-slim | Postfix SMTP, health endpoint | — |
| `ccs-dt-i1-server5` | Server 5 (10.0.4.5) | debian:bullseye-slim | OpenSSH, Python API, Redis | — |
| `ccs-dt-i1-server6` | Server 6 (10.0.4.6) | debian:jessie | PostgreSQL, Samba | CVE-2017-7494 |

## Incident 2 — Enterprise Network (Tomcat RCE)

An **enterprise on-premises network** with a central firewall, DMZ, and internal LAN. Six servers behind strict iptables rules.

| Image | Host | Base | Services |
|-------|------|------|----------|
| `ccs-dt-attacker` | Attacker (10.1.0.10) | debian:bookworm-slim | nmap, hydra, smbclient, impacket |
| `ccs-dt-i2-server1` | Server 1 / Firewall (10.1.0.1) | ubuntu:22.04 | iptables, Suricata IDS |
| `ccs-dt-i2-server2` | Server 2 / Web (10.0.1.10) | ubuntu:22.04 | Nginx, Tomcat 9.0.30 |
| `ccs-dt-i2-server3` | Server 3 / Jump (10.0.1.20) | debian:bullseye-slim | SSH jump host |
| `ccs-dt-i2-server4` | Server 4 / DB (10.0.2.10) | debian:bullseye-slim | PostgreSQL, SSH |
| `ccs-dt-i2-server5` | Server 5 / DNS (10.0.2.50) | debian:bullseye-slim | dnsmasq DNS/DHCP |
| `ccs-dt-i2-server6` | Server 6 / Files (10.0.2.60) | debian:bullseye-slim | Samba, rsync backups |

## Building

```bash
# Build all images
bash build.sh

# Or from the docker/ directory
make dt-build

# Clean up images
make dt-clean
```

## IR Constraints (Incident 1)

Each server has a critical service that creates a dilemma for incident responders:

- **Server 1**: Hosts customer website AND internal DNS — taking it down breaks name resolution
- **Server 2**: Stores nightly database backups — losing it risks unrecoverable data loss
- **Server 3**: Runs CI/CD pipeline — isolating it halts releases
- **Server 4**: Handles customer emails — downtime = SLA breach
- **Server 5**: Customer-facing REST API — downtime = revenue loss
- **Server 6**: Application database — taking it offline breaks every other service
