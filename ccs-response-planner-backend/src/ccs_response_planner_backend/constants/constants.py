"""
Shared constants for the CCS Response Planner backend.
"""
import base64
from pathlib import Path
from typing import Any


class API:
    """
    Constants related to API routes
    """
    PREFIX = "/api"
    HEALTH_RESOURCE = "health"
    PLAN_RESOURCE = "plan"
    EXAMPLE_RESOURCE = "example"
    LOGIN_RESOURCE = "login"
    LLM_RESOURCE = "llm"
    HEALTH_ROUTE = "/api/health"
    PLAN_ROUTE = "/api/plan"
    EXAMPLE_ROUTE = "/api/example"
    LOGIN_ROUTE = "/api/login"
    LLM_ROUTE = "/api/llm"
    DIGITAL_TWIN_RESOURCE = "digital-twin"
    DIGITAL_TWIN_ROUTE = "/api/digital-twin"
    DIGITAL_TWIN_RESET_ROUTE = "/api/digital-twin/reset"
    DIGITAL_TWIN_DEPLOY_ROUTE = "/api/digital-twin/deploy"
    DIGITAL_TWIN_STOP_ROUTE = "/api/digital-twin/stop"
    DIGITAL_TWIN_STATUS_ROUTE = "/api/digital-twin/status"
    DIGITAL_TWIN_VALIDATE_ROUTE = "/api/digital-twin/validate"
    TAVILY_RESOURCE = "tavily"
    TAVILY_ROUTE = "/api/tavily"
    TAVILY_SEARCH_ROUTE = "/api/tavily/search"


class DB:
    """
    Constants related to the database configuration.
    """
    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 5432
    DEFAULT_DB_NAME = "ccs"
    DEFAULT_USER = "ccs"
    MANAGEMENT_USERS_TABLE = "management_users"
    SESSION_TOKENS_TABLE = "session_tokens"
    DIGITAL_TWIN_CONFIGS_TABLE = "digital_twin_configs"


class AUTH:
    """
    Constants related to authentication.
    """
    TOKEN_HEADER = "Authorization"
    TOKEN_PREFIX = "Bearer "
    TOKEN_LENGTH = 32


class SERVER:
    """
    Constants related to the server configuration
    """
    DEFAULT_PORT = 8888
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_NUM_THREADS = 100


class GENERAL:
    """
    General constants
    """
    APP_NAME = "CCS Incident Response Planner"


def _load_example_image() -> str:
    """
    Load the example system diagram as a base64 data URL.

    :return: a data URL string, or empty string if the file is not found
    """
    path = Path(__file__).resolve().parents[4] / "docs" / "example_system.png"
    try:
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:image/png;base64,{data}"
    except FileNotFoundError:
        return ""


class DOCKER:
    """
    Constants related to Docker digital-twin deployment.
    """
    NETWORK_PREFIX = "ccs_dt_net_"
    CONTAINER_PREFIX = "ccs_dt_"


class DIGITAL_TWIN:
    """
    Constants related to the digital twin configuration.
    """
    DEFAULT_CONFIG: dict[str, Any] = {
        "networks": [
            {
                "id": "perimeter",
                "name": "Perimeter",
                "subnet": "10.0.1.0/24",
                "gateway": "10.0.1.100",
            },
            {
                "id": "zone1",
                "name": "Zone 1",
                "subnet": "10.0.2.0/24",
                "gateway": "10.0.2.100",
            },
            {
                "id": "zone2",
                "name": "Zone 2",
                "subnet": "10.0.3.0/24",
                "gateway": "10.0.3.100",
            },
            {
                "id": "zone3",
                "name": "Zone 3",
                "subnet": "10.0.4.0/24",
                "gateway": "10.0.4.100",
            },
        ],
        "hosts": [
            {
                "id": "gateway",
                "name": "Gateway",
                "docker_image": "ccs-dt-gateway:latest",
                "ip_addresses": {"perimeter": "10.0.1.254"},
                "routes": [
                    {"destination": "10.0.2.0/24",
                     "via": "10.0.1.253"},
                    {"destination": "10.0.3.0/24",
                     "via": "10.0.1.253"},
                    {"destination": "10.0.4.0/24",
                     "via": "10.0.1.253"},
                ],
                "use_image_entrypoint": True,
                "capabilities": ["NET_ADMIN", "NET_RAW"],
            },
            {
                "id": "firewall",
                "name": "Firewall",
                "docker_image": "ccs-dt-firewall:latest",
                "ip_addresses": {"perimeter": "10.0.1.253"},
                "routes": [
                    {"destination": "10.0.2.0/24",
                     "via": "10.0.1.252"},
                    {"destination": "10.0.3.0/24",
                     "via": "10.0.1.252"},
                    {"destination": "10.0.4.0/24",
                     "via": "10.0.1.252"},
                ],
                "use_image_entrypoint": True,
                "capabilities": ["NET_ADMIN", "NET_RAW"],
                "sysctls": {"net.ipv4.ip_forward": "1"},
            },
            {
                "id": "ids",
                "name": "IDS",
                "docker_image": "ccs-dt-ids:latest",
                "ip_addresses": {
                    "perimeter": "10.0.1.252",
                    "zone1": "10.0.2.252",
                    "zone2": "10.0.3.252",
                    "zone3": "10.0.4.252",
                },
                "routes": [],
                "use_image_entrypoint": True,
                "capabilities": ["NET_ADMIN", "NET_RAW"],
                "sysctls": {"net.ipv4.ip_forward": "1"},
            },
            {
                "id": "server_1",
                "name": "Server 1",
                "docker_image": "ccs-dt-server1:latest",
                "ip_addresses": {
                    "zone1": "10.0.2.1",
                    "zone2": "10.0.3.1",
                    "zone3": "10.0.4.1",
                },
                "routes": [
                    {"destination": "10.0.1.0/24",
                     "via": "10.0.2.252"},
                ],
                "use_image_entrypoint": True,
            },
            {
                "id": "server_2",
                "name": "Server 2",
                "docker_image": "ccs-dt-server2:latest",
                "ip_addresses": {
                    "zone1": "10.0.2.2",
                    "zone2": "10.0.3.2",
                    "zone3": "10.0.4.2",
                },
                "routes": [
                    {"destination": "10.0.1.0/24",
                     "via": "10.0.2.252"},
                ],
                "use_image_entrypoint": True,
            },
            {
                "id": "server_3",
                "name": "Server 3",
                "docker_image": "ccs-dt-server3:latest",
                "ip_addresses": {
                    "zone2": "10.0.3.3",
                    "zone3": "10.0.4.3",
                },
                "routes": [
                    {"destination": "10.0.1.0/24",
                     "via": "10.0.3.252"},
                ],
                "use_image_entrypoint": True,
            },
            {
                "id": "server_4",
                "name": "Server 4",
                "docker_image": "ccs-dt-server4:latest",
                "ip_addresses": {
                    "zone2": "10.0.3.4",
                    "zone3": "10.0.4.4",
                },
                "routes": [
                    {"destination": "10.0.1.0/24",
                     "via": "10.0.3.252"},
                ],
                "use_image_entrypoint": True,
            },
            {
                "id": "server_5",
                "name": "Server 5",
                "docker_image": "ccs-dt-server5:latest",
                "ip_addresses": {"zone3": "10.0.4.5"},
                "routes": [
                    {"destination": "10.0.1.0/24",
                     "via": "10.0.4.252"},
                ],
                "use_image_entrypoint": True,
            },
            {
                "id": "server_6",
                "name": "Server 6",
                "docker_image": "ccs-dt-server6:latest",
                "ip_addresses": {"zone3": "10.0.4.6"},
                "routes": [
                    {"destination": "10.0.1.0/24",
                     "via": "10.0.4.252"},
                ],
                "use_image_entrypoint": True,
                "privileged": True,
            },
        ],
        "links": [
            {"source": "gateway", "target": "firewall"},
            {"source": "firewall", "target": "ids"},
            {"source": "ids", "target": "server_2"},
            {"source": "ids", "target": "server_3"},
            {"source": "server_1", "target": "server_2"},
            {"source": "server_1", "target": "server_4"},
            {"source": "server_1", "target": "server_6"},
            {"source": "server_2", "target": "server_3"},
            {"source": "server_2", "target": "server_5"},
            {"source": "server_3", "target": "server_6"},
            {"source": "server_4", "target": "server_5"},
            {"source": "server_5", "target": "server_6"},
        ],
        "specification_commands": [
            {
                "host": "server_1",
                "command": (
                    "bash -c 'echo > /dev/tcp/10.0.2.2/21'"
                ),
                "description": (
                    "Verify Server 2 FTP is reachable"
                    " from Server 1"
                ),
            },
            {
                "host": "server_1",
                "command": (
                    "bash -c 'echo > /dev/tcp/10.0.3.3/22'"
                ),
                "description": (
                    "Verify Server 3 SSH is reachable"
                    " from Server 1"
                ),
            },
            {
                "host": "server_5",
                "command": (
                    "python3 -c \"import socket;"
                    " s=socket.create_connection("
                    "('10.0.4.6', 5432), timeout=3);"
                    " s.close()\""
                ),
                "description": (
                    "Verify Server 6 PostgreSQL is running"
                ),
            },
            {
                "host": "server_1",
                "command": (
                    "bash -c 'echo > /dev/tcp/10.0.3.4/25'"
                ),
                "description": (
                    "Verify Server 4 Postfix SMTP is"
                    " accepting connections"
                ),
            },
            # Positive reachability — one test per topology link
            {
                "host": "gateway",
                "command": "ping -c 1 -W 2 10.0.1.253",
                "description": (
                    "Firewall reachable from Gateway"
                    " (perimeter)"
                ),
            },
            {
                "host": "firewall",
                "command": "ping -c 1 -W 2 10.0.1.252",
                "description": (
                    "IDS reachable from Firewall"
                    " (perimeter)"
                ),
            },
            {
                "host": "ids",
                "command": "ping -c 1 -W 2 10.0.2.2",
                "description": (
                    "Server 2 reachable from IDS"
                    " (zone1)"
                ),
            },
            {
                "host": "ids",
                "command": "ping -c 1 -W 2 10.0.3.3",
                "description": (
                    "Server 3 reachable from IDS"
                    " (zone2)"
                ),
            },
            {
                "host": "server_1",
                "command": "ping -c 1 -W 2 10.0.2.2",
                "description": (
                    "Server 2 reachable from Server 1"
                    " (zone1)"
                ),
            },
            {
                "host": "server_1",
                "command": "ping -c 1 -W 2 10.0.3.4",
                "description": (
                    "Server 4 reachable from Server 1"
                    " (zone2)"
                ),
            },
            {
                "host": "server_1",
                "command": "ping -c 1 -W 2 10.0.4.6",
                "description": (
                    "Server 6 reachable from Server 1"
                    " (zone3)"
                ),
            },
            {
                "host": "server_2",
                "command": "ping -c 1 -W 2 10.0.3.3",
                "description": (
                    "Server 3 reachable from Server 2"
                    " (zone2)"
                ),
            },
            {
                "host": "server_2",
                "command": "ping -c 1 -W 2 10.0.4.5",
                "description": (
                    "Server 5 reachable from Server 2"
                    " (zone3)"
                ),
            },
            {
                "host": "server_3",
                "command": "ping -c 1 -W 2 10.0.4.6",
                "description": (
                    "Server 6 reachable from Server 3"
                    " (zone3)"
                ),
            },
            {
                "host": "server_4",
                "command": "ping -c 1 -W 2 10.0.4.5",
                "description": (
                    "Server 5 reachable from Server 4"
                    " (zone3)"
                ),
            },
            {
                "host": "server_5",
                "command": "ping -c 1 -W 2 10.0.4.6",
                "description": (
                    "Server 6 reachable from Server 5"
                    " (zone3)"
                ),
            },
            {
                "host": "gateway",
                "command": "ping -c 1 -W 2 10.0.4.6",
                "description": (
                    "Server 6 reachable from Gateway"
                    " (end-to-end routing)"
                ),
            },
            # Negative reachability — zone isolation
            {
                "host": "server_5",
                "command": "! ping -c 1 -W 2 10.0.2.1",
                "description": (
                    "Server 1 not reachable from"
                    " Server 5 (zone isolation)"
                ),
            },
            {
                "host": "server_5",
                "command": "! ping -c 1 -W 2 10.0.3.3",
                "description": (
                    "Server 3 not reachable from"
                    " Server 5 (zone isolation)"
                ),
            },
            {
                "host": "server_6",
                "command": "! ping -c 1 -W 2 10.0.2.2",
                "description": (
                    "Server 2 not reachable from"
                    " Server 6 (zone isolation)"
                ),
            },
            {
                "host": "server_3",
                "command": "! ping -c 1 -W 2 10.0.2.1",
                "description": (
                    "Server 1 not reachable from"
                    " Server 3 (zone isolation)"
                ),
            },
        ],
    }


class EXAMPLES:
    """
    Example incident data for populating the response planner form.
    """
    SYSTEM_DESCRIPTION = (
        "The system is the cloud infrastructure of a mid-size SaaS "
        "company, consisting of 6 servers behind a gateway with "
        "Snort IDS. The network is segmented into a perimeter zone "
        "(10.0.1.0/24) and three internal zones: Zone 1 "
        "(10.0.2.0/24), Zone 2 (10.0.3.0/24), and Zone 3 "
        "(10.0.4.0/24). The network topology is shown in the "
        "attached figure.\n\n"
        "Gateway (10.0.1.254, Ubuntu 22): Snort IDS v2.9\n"
        "Firewall (10.0.1.253, Ubuntu 22): iptables packet "
        "filtering\n"
        "IDS (10.0.1.252, Ubuntu 22): rsyslog log aggregation, "
        "tcpdump\n"
        "Server 1 (10.0.2.1, Debian 11): Nginx reverse proxy, "
        "PHP-FPM customer portal, dnsmasq internal DNS\n"
        "Server 2 (10.0.2.2, Debian 11): vsftpd FTP, cron nightly "
        "backups\n"
        "Server 3 (10.0.3.3, Ubuntu 20): SSH, cron CI/CD build "
        "pipeline\n"
        "Server 4 (10.0.3.4, Debian 11): Postfix SMTP mail "
        "server\n"
        "Server 5 (10.0.4.5, Debian 11): SSH, Python REST API, "
        "Redis session cache\n"
        "Server 6 (10.0.4.6, Debian 8): PostgreSQL database, "
        "Samba file shares"
    )
    SYSTEM_DESCRIPTION_IMAGE = _load_example_image()
    SECURITY_ALERTS = (
        "02/06-10:15:22.341201 [**] [1:2006546:3] ET SCAN SSH "
        "Brute Force Login Attempt [**] [Classification: Attempted "
        "Information Leak] [Priority: 2] {TCP} "
        "192.168.1.50:44321 -> 10.0.3.3:22\n\n"
        "02/06-10:42:15.889102 [**] [1:2014473:3] ET EXPLOIT "
        "Possible SQL Injection Attempt (UNION SELECT) [**] "
        "[Classification: Attempted Administrator Privilege Gain] "
        "[Priority: 1] {TCP} 10.0.3.3:55210 -> 10.0.2.1:80"
    )
    OPERATOR_FEEDBACK = (
        "Note that the Snort IDS alerts only cover the SSH brute "
        "force on server 3 and the SQL injection on server 1. "
        "However, the SQL injection alert shows the attack on "
        "server 1 originates from server 3, which indicates that "
        "server 3 is compromised as well."
    )
    SPECIFICATION = (
        "- Server 2 FTP service must remain accessible from "
        "the gateway\n"
        "- Server 3 CI/CD build pipeline must remain accessible "
        "from the gateway\n"
        "- Server 6 PostgreSQL must not be taken offline (all "
        "services depend on it)\n"
        "- Server 4 Postfix mail delivery must not be interrupted "
        "(SLA obligation)\n"
        "- All servers must remain reachable from the gateway "
        "through the routing chain "
        "(gateway -> firewall -> IDS -> zones)\n"
        "- All topology links between adjacent hosts must remain "
        "operational\n"
        "- Zone 3 hosts (Server 5, Server 6) must not have direct "
        "routes to Zone 1 (10.0.2.0/24) or Zone 2 (10.0.3.0/24)\n"
        "- Zone 2 hosts (Server 3, Server 4) must not have direct "
        "routes to Zone 1 (10.0.2.0/24)"
    )
