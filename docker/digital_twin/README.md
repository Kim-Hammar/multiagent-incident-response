# Digital Twin Docker Images

Custom Docker images for the CCS incident response digital twin. Each image runs real network services with three intentional vulnerabilities for security training.

## Scenario

A **mid-size SaaS company** infrastructure: web frontend, customer-facing API, database, mail, backups, and CI/CD — all behind a gateway with Snort IDS.

## Images

| Image | Host | Base | Services | Vulnerability |
|-------|------|------|----------|---------------|
| `ccs-dt-attacker` | Attacker (10.0.1.10) | debian:bookworm-slim | nmap, hydra, smbclient, impacket | — |
| `ccs-dt-gateway` | Gateway (10.0.0.254) | ubuntu:22.04 | Snort IDS, pentest tools | — |
| `ccs-dt-firewall` | Firewall (10.0.0.253) | ubuntu:22.04 | iptables, IP forwarding | — |
| `ccs-dt-ids` | IDS (10.0.0.252) | ubuntu:22.04 | rsyslog, tcpdump | — |
| `ccs-dt-server1` | Server 1 (10.0.0.1) | debian:bullseye-slim | Nginx, PHP-FPM, dnsmasq | SQL injection → root |
| `ccs-dt-server2` | Server 2 (10.0.0.2) | debian:bullseye-slim | vsftpd, cron backups | — |
| `ccs-dt-server3` | Server 3 (10.0.0.3) | ubuntu:20.04 | OpenSSH, cron CI/CD | Weak SSH password |
| `ccs-dt-server4` | Server 4 (10.0.0.4) | debian:bullseye-slim | Postfix SMTP, health endpoint | — |
| `ccs-dt-server5` | Server 5 (10.0.0.5) | debian:bullseye-slim | OpenSSH, Python API, Redis | — |
| `ccs-dt-server6` | Server 6 (10.0.0.6) | debian:jessie | PostgreSQL, Samba | CVE-2017-7494 |

## Vulnerabilities

### Server 1 — SQL Injection (root)

- PHP-FPM runs as root (deliberate misconfiguration)
- `index.php` login form uses unsanitized SQL queries
- Auth bypass: `admin' OR '1'='1' --`
- `shell.php` has command injection via `ping` parameter: `; id`
- Combined: SQL injection → auth bypass → command injection → root

### Server 3 — Weak SSH Password

- User `admin` with password `password123`
- `admin` has `NOPASSWD:ALL` sudo access
- SSH password authentication enabled
- Dictionary attack with ~5 words cracks it instantly

### Server 6 — CVE-2017-7494 (SambaCry)

- Debian Jessie ships Samba ~4.2.x (vulnerable range 3.5.0–4.4.13)
- World-writable `[public]` share with `nt pipe support = yes`
- Upload `.so` → trigger `dlopen()` via named pipe → code executes as root

## Building

```bash
# Build all images
bash build.sh

# Or from the docker/ directory
make dt-build

# Clean up images
make dt-clean
```

## IR Constraints

Each server has a critical service that creates a dilemma for incident responders:

- **Server 1**: Hosts customer website AND internal DNS — taking it down breaks name resolution
- **Server 2**: Stores nightly database backups — losing it risks unrecoverable data loss
- **Server 3**: Runs CI/CD pipeline — isolating it halts releases
- **Server 4**: Handles customer emails — downtime = SLA breach
- **Server 5**: Customer-facing REST API — downtime = revenue loss
- **Server 6**: Application database — taking it offline breaks every other service
