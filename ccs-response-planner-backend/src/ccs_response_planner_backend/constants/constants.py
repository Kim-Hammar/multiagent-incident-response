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
    NVD_RESOURCE = "nvd"
    NVD_ROUTE = "/api/nvd"
    NVD_SEARCH_ROUTE = "/api/nvd/search"
    MITRE_RESOURCE = "mitre"
    MITRE_ROUTE = "/api/mitre"
    MITRE_SEARCH_ROUTE = "/api/mitre/search"
    VIRUSTOTAL_RESOURCE = "virustotal"
    VIRUSTOTAL_ROUTE = "/api/virustotal"
    VIRUSTOTAL_SCAN_ROUTE = "/api/virustotal/scan"
    ABUSEIPDB_RESOURCE = "abuseipdb"
    ABUSEIPDB_ROUTE = "/api/abuseipdb"
    ABUSEIPDB_CHECK_ROUTE = "/api/abuseipdb/check"
    OTX_RESOURCE = "otx"
    OTX_ROUTE = "/api/otx"
    OTX_SEARCH_ROUTE = "/api/otx/search"
    DT_EXEC_RESOURCE = "dt-exec"
    DT_EXEC_ROUTE = "/api/dt-exec"
    DT_EXEC_RUN_ROUTE = "/api/dt-exec/run"
    DT_LOGS_RESOURCE = "dt-logs"
    DT_LOGS_ROUTE = "/api/dt-logs"
    DT_LOGS_FETCH_ROUTE = "/api/dt-logs/fetch"
    DT_PYTHON_RESOURCE = "dt-python"
    DT_PYTHON_ROUTE = "/api/dt-python"
    DT_PYTHON_RUN_ROUTE = "/api/dt-python/run"
    DT_PYTHON_START_ROUTE = "/api/dt-python/start"
    DT_PYTHON_STOP_ROUTE = "/api/dt-python/stop"
    AGENTS_RESOURCE = "agents"
    AGENTS_ROUTE = "/api/agents"
    AGENTS_INFO_STEP_ROUTE = "/api/agents/information/step"
    AGENTS_INFO_TOOL_ROUTE = "/api/agents/information/tool"
    AGENTS_INFO_PROMPT_ROUTE = "/api/agents/information/prompt"
    AGENTS_PENTEST_STEP_ROUTE = "/api/agents/pentest/step"
    AGENTS_PENTEST_TOOL_ROUTE = "/api/agents/pentest/tool"
    AGENTS_PENTEST_PROMPT_ROUTE = "/api/agents/pentest/prompt"
    AGENTS_VALIDATION_STEP_ROUTE = "/api/agents/validation/step"
    AGENTS_VALIDATION_TOOL_ROUTE = "/api/agents/validation/tool"
    AGENTS_VALIDATION_PROMPT_ROUTE = "/api/agents/validation/prompt"
    AGENTS_CODE_STEP_ROUTE = "/api/agents/code/step"
    AGENTS_CODE_TOOL_ROUTE = "/api/agents/code/tool"
    AGENTS_CODE_PROMPT_ROUTE = "/api/agents/code/prompt"
    AGENTS_CODE_REVIEW_STEP_ROUTE = "/api/agents/code-review/step"
    AGENTS_CODE_REVIEW_TOOL_ROUTE = "/api/agents/code-review/tool"
    AGENTS_CODE_REVIEW_PROMPT_ROUTE = (
        "/api/agents/code-review/prompt"
    )
    AGENTS_RL_STEP_ROUTE = "/api/agents/rl/step"
    AGENTS_RL_TOOL_ROUTE = "/api/agents/rl/tool"
    AGENTS_RL_PROMPT_ROUTE = "/api/agents/rl/prompt"
    AGENTS_CODE_MANAGER_STEP_ROUTE = (
        "/api/agents/code-manager/step"
    )
    AGENTS_CODE_MANAGER_TOOL_ROUTE = (
        "/api/agents/code-manager/tool"
    )
    AGENTS_CODE_MANAGER_PROMPT_ROUTE = (
        "/api/agents/code-manager/prompt"
    )
    AGENTS_PLAN_MANAGER_STEP_ROUTE = (
        "/api/agents/plan-manager/step"
    )
    AGENTS_PLAN_MANAGER_TOOL_ROUTE = (
        "/api/agents/plan-manager/tool"
    )
    AGENTS_PLAN_MANAGER_PROMPT_ROUTE = (
        "/api/agents/plan-manager/prompt"
    )
    AGENTS_DP_STEP_ROUTE = "/api/agents/dp/step"
    AGENTS_DP_TOOL_ROUTE = "/api/agents/dp/tool"
    AGENTS_DP_PROMPT_ROUTE = "/api/agents/dp/prompt"
    AGENTS_REPORTS_ROUTE = "/api/agents/reports"
    AGENTS_REPORT_ROUTE = "/api/agents/reports/<int:report_id>"
    EXAMPLES_RESOURCE = "examples"
    EXAMPLES_ROUTE = "/api/examples"
    DIGITAL_TWIN_CONFIGS_ROUTE = "/api/digital-twin/configs"
    DIGITAL_TWIN_CONFIG_VALIDATION_RESULTS_ROUTE = (
        "/api/digital-twin/configs/<int:config_id>"
        "/validation-results"
    )


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
    AGENT_REPORTS_TABLE = "agent_reports"
    EXAMPLE_INCIDENTS_TABLE = "example_incidents"


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


class LLM:
    """
    Constants related to LLM models.
    """
    IMAGE_GENERATION_MODEL = "gemini-3-pro-image-preview"


class GENERAL:
    """
    General constants
    """
    APP_NAME = "CCS Incident Response Planner"


def _load_example_image(filename: str = "incident_1.png") -> str:
    """
    Load the example system diagram as a base64 data URL.

    :param filename: name of the image file in the docs/ directory
    :return: a data URL string, or empty string if the file is not found
    """
    path = Path(__file__).resolve().parents[4] / "docs" / filename
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
    PYTHON_SANDBOX_IMAGE = "ccs-dt-python-sandbox:latest"
    PYTHON_SANDBOX_CONTAINER = "ccs_python_sandbox"
    ATTACKER_IMAGE = "ccs-dt-attacker:latest"


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
                "id": "i1_attacker",
                "name": "Attacker",
                "description": "External attacker host",
                "docker_image": "ccs-dt-attacker:latest",
                "ip_addresses": {"perimeter": "10.0.1.10"},
                "routes": [
                    {"destination": "10.0.2.0/24",
                     "via": "10.0.1.253"},
                    {"destination": "10.0.3.0/24",
                     "via": "10.0.1.253"},
                    {"destination": "10.0.4.0/24",
                     "via": "10.0.1.253"},
                ],
                "use_image_entrypoint": False,
                "capabilities": ["NET_ADMIN", "NET_RAW"],
            },
            {
                "id": "i1_gateway",
                "name": "Gateway",
                "description": "Snort IDS v2.9",
                "docker_image": "ccs-dt-i1-gateway:latest",
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
                "id": "i1_firewall",
                "name": "Firewall",
                "description": "iptables packet filtering",
                "docker_image": "ccs-dt-i1-firewall:latest",
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
                "id": "i1_ids",
                "name": "Log Collector",
                "description": "rsyslog, tcpdump",
                "docker_image": "ccs-dt-i1-ids:latest",
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
                "id": "i1_server_1",
                "name": "Server 1",
                "description": (
                    "Nginx, PHP-FPM portal, dnsmasq DNS"
                ),
                "docker_image": "ccs-dt-i1-server1:latest",
                "ip_addresses": {"zone1": "10.0.2.1"},
                "routes": [
                    {"destination": "10.0.3.4/32",
                     "via": "10.0.2.252"},
                    {"destination": "10.0.4.6/32",
                     "via": "10.0.2.252"},
                    {"destination": "10.0.1.0/24",
                     "via": "10.0.2.252"},
                ],
                "use_image_entrypoint": True,
                "capabilities": ["NET_ADMIN"],
            },
            {
                "id": "i1_server_2",
                "name": "Server 2",
                "description": "vsftpd FTP, cron backups",
                "docker_image": "ccs-dt-i1-server2:latest",
                "ip_addresses": {"zone1": "10.0.2.2"},
                "routes": [
                    {"destination": "10.0.3.3/32",
                     "via": "10.0.2.252"},
                    {"destination": "10.0.4.5/32",
                     "via": "10.0.2.252"},
                    {"destination": "10.0.1.0/24",
                     "via": "10.0.2.252"},
                ],
                "use_image_entrypoint": True,
                "capabilities": ["NET_ADMIN"],
            },
            {
                "id": "i1_server_3",
                "name": "Server 3",
                "description": (
                    "SSH, cron CI/CD build pipeline"
                ),
                "docker_image": "ccs-dt-i1-server3:latest",
                "ip_addresses": {"zone2": "10.0.3.3"},
                "routes": [
                    {"destination": "10.0.2.2/32",
                     "via": "10.0.3.252"},
                    {"destination": "10.0.4.6/32",
                     "via": "10.0.3.252"},
                    {"destination": "10.0.1.0/24",
                     "via": "10.0.3.252"},
                ],
                "post_deploy_commands": [
                    "iptables -I INPUT -s 10.0.3.4 -j DROP",
                    "iptables -I OUTPUT -d 10.0.3.4 -j DROP",
                ],
                "use_image_entrypoint": True,
                "capabilities": ["NET_ADMIN"],
            },
            {
                "id": "i1_server_4",
                "name": "Server 4",
                "description": "Postfix SMTP mail server",
                "docker_image": "ccs-dt-i1-server4:latest",
                "ip_addresses": {"zone2": "10.0.3.4"},
                "routes": [
                    {"destination": "10.0.2.1/32",
                     "via": "10.0.3.252"},
                    {"destination": "10.0.4.5/32",
                     "via": "10.0.3.252"},
                    {"destination": "10.0.1.0/24",
                     "via": "10.0.3.252"},
                ],
                "post_deploy_commands": [
                    "iptables -I INPUT -s 10.0.3.3 -j DROP",
                    "iptables -I OUTPUT -d 10.0.3.3 -j DROP",
                ],
                "use_image_entrypoint": True,
                "capabilities": ["NET_ADMIN"],
            },
            {
                "id": "i1_server_5",
                "name": "Server 5",
                "description": (
                    "SSH, Python REST API, Redis cache"
                ),
                "docker_image": "ccs-dt-i1-server5:latest",
                "ip_addresses": {"zone3": "10.0.4.5"},
                "routes": [
                    {"destination": "10.0.2.2/32",
                     "via": "10.0.4.252"},
                    {"destination": "10.0.3.4/32",
                     "via": "10.0.4.252"},
                    {"destination": "10.0.1.0/24",
                     "via": "10.0.4.252"},
                ],
                "use_image_entrypoint": True,
                "capabilities": ["NET_ADMIN"],
            },
            {
                "id": "i1_server_6",
                "name": "Server 6",
                "description": (
                    "PostgreSQL database, Samba file shares"
                ),
                "docker_image": "ccs-dt-i1-server6:latest",
                "ip_addresses": {"zone3": "10.0.4.6"},
                "routes": [
                    {"destination": "10.0.2.1/32",
                     "via": "10.0.4.252"},
                    {"destination": "10.0.3.3/32",
                     "via": "10.0.4.252"},
                    {"destination": "10.0.1.0/24",
                     "via": "10.0.4.252"},
                ],
                "use_image_entrypoint": True,
                "privileged": True,
            },
        ],
        "links": [
            {"source": "i1_attacker", "target": "i1_gateway"},
            {"source": "i1_gateway", "target": "i1_firewall"},
            {"source": "i1_firewall", "target": "i1_ids"},
            {"source": "i1_ids", "target": "i1_server_2"},
            {"source": "i1_ids", "target": "i1_server_3"},
            {"source": "i1_server_1", "target": "i1_server_2"},
            {"source": "i1_server_1", "target": "i1_server_4"},
            {"source": "i1_server_1", "target": "i1_server_6"},
            {"source": "i1_server_2", "target": "i1_server_3"},
            {"source": "i1_server_2", "target": "i1_server_5"},
            {"source": "i1_server_3", "target": "i1_server_6"},
            {"source": "i1_server_4", "target": "i1_server_5"},
            {"source": "i1_server_5", "target": "i1_server_6"},
        ],
        "specification_commands": [
            {
                "host": "i1_server_1",
                "command": (
                    "bash -c 'echo > /dev/tcp/10.0.2.2/21'"
                ),
                "description": (
                    "Verify Server 2 FTP is reachable"
                    " from Server 1"
                ),
            },
            {
                "host": "i1_server_2",
                "command": (
                    "bash -c 'echo > /dev/tcp/10.0.3.3/22'"
                ),
                "description": (
                    "Verify Server 3 SSH is reachable"
                    " from Server 2"
                ),
            },
            {
                "host": "i1_server_5",
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
                "host": "i1_server_1",
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
                "host": "i1_gateway",
                "command": "ping -c 1 -W 2 10.0.1.253",
                "description": (
                    "Firewall reachable from Gateway"
                    " (perimeter)"
                ),
            },
            {
                "host": "i1_firewall",
                "command": "ping -c 1 -W 2 10.0.1.252",
                "description": (
                    "Log Collector reachable from Firewall"
                    " (perimeter)"
                ),
            },
            {
                "host": "i1_ids",
                "command": "ping -c 1 -W 2 10.0.2.2",
                "description": (
                    "Server 2 reachable from Log Collector"
                    " (zone1)"
                ),
            },
            {
                "host": "i1_ids",
                "command": "ping -c 1 -W 2 10.0.3.3",
                "description": (
                    "Server 3 reachable from Log Collector"
                    " (zone2)"
                ),
            },
            {
                "host": "i1_server_1",
                "command": "ping -c 1 -W 2 10.0.2.2",
                "description": (
                    "Server 2 reachable from Server 1"
                    " (zone1)"
                ),
            },
            {
                "host": "i1_server_1",
                "command": "ping -c 1 -W 2 10.0.3.4",
                "description": (
                    "Server 4 reachable from Server 1"
                    " (cross-zone)"
                ),
            },
            {
                "host": "i1_server_1",
                "command": "ping -c 1 -W 2 10.0.4.6",
                "description": (
                    "Server 6 reachable from Server 1"
                    " (cross-zone)"
                ),
            },
            {
                "host": "i1_server_2",
                "command": "ping -c 1 -W 2 10.0.3.3",
                "description": (
                    "Server 3 reachable from Server 2"
                    " (cross-zone)"
                ),
            },
            {
                "host": "i1_server_2",
                "command": "ping -c 1 -W 2 10.0.4.5",
                "description": (
                    "Server 5 reachable from Server 2"
                    " (cross-zone)"
                ),
            },
            {
                "host": "i1_server_3",
                "command": "ping -c 1 -W 2 10.0.4.6",
                "description": (
                    "Server 6 reachable from Server 3"
                    " (cross-zone)"
                ),
            },
            {
                "host": "i1_server_4",
                "command": "ping -c 1 -W 2 10.0.4.5",
                "description": (
                    "Server 5 reachable from Server 4"
                    " (cross-zone)"
                ),
            },
            {
                "host": "i1_server_5",
                "command": "ping -c 1 -W 2 10.0.4.6",
                "description": (
                    "Server 6 reachable from Server 5"
                    " (zone3)"
                ),
            },
            # Positive reachability — perimeter to allowed servers
            {
                "host": "i1_attacker",
                "command": "ping -c 1 -W 2 10.0.2.2",
                "description": (
                    "Server 2 reachable from Attacker"
                    " (perimeter, allowed by firewall)"
                ),
            },
            {
                "host": "i1_attacker",
                "command": "ping -c 1 -W 2 10.0.3.3",
                "description": (
                    "Server 3 reachable from Attacker"
                    " (perimeter, allowed by firewall)"
                ),
            },
            {
                "host": "i1_gateway",
                "command": "ping -c 1 -W 2 10.0.2.2",
                "description": (
                    "Server 2 reachable from Gateway"
                    " (perimeter, allowed by firewall)"
                ),
            },
            {
                "host": "i1_gateway",
                "command": "ping -c 1 -W 2 10.0.3.3",
                "description": (
                    "Server 3 reachable from Gateway"
                    " (perimeter, allowed by firewall)"
                ),
            },
            # Negative reachability — firewall blocks
            {
                "host": "i1_gateway",
                "command": "! ping -c 1 -W 2 10.0.4.6",
                "description": (
                    "Server 6 not reachable from"
                    " Gateway (firewall blocks)"
                ),
            },
            {
                "host": "i1_attacker",
                "command": "! ping -c 1 -W 2 10.0.2.1",
                "description": (
                    "Server 1 not reachable from"
                    " Attacker (firewall blocks)"
                ),
            },
            {
                "host": "i1_attacker",
                "command": "! ping -c 1 -W 2 10.0.4.6",
                "description": (
                    "Server 6 not reachable from"
                    " Attacker (firewall blocks)"
                ),
            },
            # Negative reachability — zone isolation
            {
                "host": "i1_server_5",
                "command": "! ping -c 1 -W 2 10.0.2.1",
                "description": (
                    "Server 1 not reachable from"
                    " Server 5 (zone isolation)"
                ),
            },
            {
                "host": "i1_server_5",
                "command": "! ping -c 1 -W 2 10.0.3.3",
                "description": (
                    "Server 3 not reachable from"
                    " Server 5 (zone isolation)"
                ),
            },
            {
                "host": "i1_server_6",
                "command": "! ping -c 1 -W 2 10.0.2.2",
                "description": (
                    "Server 2 not reachable from"
                    " Server 6 (zone isolation)"
                ),
            },
            {
                "host": "i1_server_3",
                "command": "! ping -c 1 -W 2 10.0.2.1",
                "description": (
                    "Server 1 not reachable from"
                    " Server 3 (zone isolation)"
                ),
            },
            {
                "host": "i1_server_3",
                "command": "! ping -c 1 -W 2 10.0.3.4",
                "description": (
                    "Server 4 not reachable from"
                    " Server 3 (zone2 isolation)"
                ),
            },
        ],
    }

    INCIDENT_2_CONFIG: dict[str, Any] = {
        "networks": [
            {
                "id": "internet",
                "name": "Internet",
                "subnet": "10.1.0.0/24",
                "gateway": "10.1.0.100",
            },
            {
                "id": "dmz",
                "name": "DMZ",
                "subnet": "10.1.1.0/24",
                "gateway": "10.1.1.100",
            },
            {
                "id": "lan",
                "name": "Internal LAN",
                "subnet": "10.1.2.0/24",
                "gateway": "10.1.2.100",
            },
        ],
        "hosts": [
            {
                "id": "i2_attacker",
                "name": "Attacker",
                "description": "External attacker host",
                "docker_image": "ccs-dt-attacker:latest",
                "ip_addresses": {"internet": "10.1.0.10"},
                "routes": [
                    {"destination": "10.1.1.0/24",
                     "via": "10.1.0.1"},
                    {"destination": "10.1.2.0/24",
                     "via": "10.1.0.1"},
                ],
                "use_image_entrypoint": False,
                "capabilities": ["NET_ADMIN", "NET_RAW"],
            },
            {
                "id": "i2_server_1",
                "name": "Server 1",
                "description": (
                    "Gateway/router, iptables firewall"
                ),
                "docker_image": "ccs-dt-i2-server1:latest",
                "ip_addresses": {
                    "internet": "10.1.0.1",
                    "dmz": "10.1.1.1",
                    "lan": "10.1.2.1",
                },
                "routes": [],
                "use_image_entrypoint": True,
                "capabilities": ["NET_ADMIN", "NET_RAW"],
                "sysctls": {"net.ipv4.ip_forward": "1"},
            },
            {
                "id": "i2_server_2",
                "name": "Server 2",
                "description": "Nginx HTTP web server",
                "docker_image": "ccs-dt-i2-server2:latest",
                "ip_addresses": {"dmz": "10.1.1.10"},
                "routes": [
                    {"destination": "10.1.2.10/32",
                     "via": "10.1.1.1"},
                    {"destination": "10.1.0.0/24",
                     "via": "10.1.1.1"},
                ],
                "use_image_entrypoint": True,
                "capabilities": ["NET_ADMIN"],
            },
            {
                "id": "i2_server_3",
                "name": "Server 3",
                "description": "SSH jump host",
                "docker_image": "ccs-dt-i2-server3:latest",
                "ip_addresses": {"dmz": "10.1.1.20"},
                "routes": [
                    {"destination": "10.1.2.0/24",
                     "via": "10.1.1.1"},
                    {"destination": "10.1.0.0/24",
                     "via": "10.1.1.1"},
                ],
                "use_image_entrypoint": True,
                "capabilities": ["NET_ADMIN"],
            },
            {
                "id": "i2_server_4",
                "name": "Server 4",
                "description": "PostgreSQL database",
                "docker_image": "ccs-dt-i2-server4:latest",
                "ip_addresses": {"lan": "10.1.2.10"},
                "routes": [
                    {"destination": "10.1.1.10/32",
                     "via": "10.1.2.1"},
                    {"destination": "10.1.0.0/24",
                     "via": "10.1.2.1"},
                ],
                "use_image_entrypoint": True,
                "capabilities": ["NET_ADMIN"],
            },
            {
                "id": "i2_server_5",
                "name": "Server 5",
                "description": "dnsmasq DNS server",
                "docker_image": "ccs-dt-i2-server5:latest",
                "ip_addresses": {"lan": "10.1.2.50"},
                "routes": [
                    {"destination": "10.1.1.0/24",
                     "via": "10.1.2.1"},
                ],
                "use_image_entrypoint": True,
                "capabilities": ["NET_ADMIN"],
            },
            {
                "id": "i2_server_6",
                "name": "Server 6",
                "description": "Samba file shares",
                "docker_image": "ccs-dt-i2-server6:latest",
                "ip_addresses": {"lan": "10.1.2.60"},
                "routes": [
                    {"destination": "10.1.1.0/24",
                     "via": "10.1.2.1"},
                ],
                "use_image_entrypoint": True,
                "capabilities": ["NET_ADMIN"],
            },
        ],
        "links": [
            {"source": "i2_attacker", "target": "i2_server_1"},
            {"source": "i2_server_1", "target": "i2_server_2"},
            {"source": "i2_server_1", "target": "i2_server_3"},
            {"source": "i2_server_1", "target": "i2_server_4"},
            {"source": "i2_server_1", "target": "i2_server_5"},
            {"source": "i2_server_1", "target": "i2_server_6"},
            {"source": "i2_server_2", "target": "i2_server_3"},
            {"source": "i2_server_2", "target": "i2_server_4"},
            {"source": "i2_server_4", "target": "i2_server_5"},
            {"source": "i2_server_4", "target": "i2_server_6"},
            {"source": "i2_server_5", "target": "i2_server_6"},
        ],
        "specification_commands": [
            # Service checks (5)
            {
                "host": "i2_attacker",
                "command": (
                    "bash -c 'echo > /dev/tcp/10.1.1.10/80'"
                ),
                "description": (
                    "Verify Server 2 HTTP is reachable"
                ),
            },
            {
                "host": "i2_attacker",
                "command": (
                    "bash -c 'echo > /dev/tcp/10.1.1.20/22'"
                ),
                "description": (
                    "Verify Server 3 SSH is reachable"
                ),
            },
            {
                "host": "i2_server_2",
                "command": (
                    "python3 -c \"import socket;"
                    " s=socket.create_connection("
                    "('10.1.2.10', 5432), timeout=3);"
                    " s.close()\""
                ),
                "description": (
                    "Verify Server 4 PostgreSQL is"
                    " reachable from Server 2"
                ),
            },
            {
                "host": "i2_server_4",
                "command": (
                    "bash -c 'echo > /dev/tcp/10.1.2.50/53'"
                ),
                "description": (
                    "Verify Server 5 DNS is reachable"
                    " from Server 4"
                ),
            },
            {
                "host": "i2_server_4",
                "command": (
                    "bash -c 'echo > /dev/tcp/10.1.2.60/445'"
                ),
                "description": (
                    "Verify Server 6 Samba is reachable"
                    " from Server 4"
                ),
            },
            # Positive reachability (10)
            {
                "host": "i2_attacker",
                "command": "ping -c 1 -W 2 10.1.0.1",
                "description": (
                    "Server 1 reachable from Attacker"
                    " (internet)"
                ),
            },
            {
                "host": "i2_server_1",
                "command": "ping -c 1 -W 2 10.1.1.10",
                "description": (
                    "Server 2 reachable from Server 1"
                    " (dmz)"
                ),
            },
            {
                "host": "i2_server_1",
                "command": "ping -c 1 -W 2 10.1.1.20",
                "description": (
                    "Server 3 reachable from Server 1"
                    " (dmz)"
                ),
            },
            {
                "host": "i2_server_1",
                "command": "ping -c 1 -W 2 10.1.2.10",
                "description": (
                    "Server 4 reachable from Server 1"
                    " (lan)"
                ),
            },
            {
                "host": "i2_server_1",
                "command": "ping -c 1 -W 2 10.1.2.50",
                "description": (
                    "Server 5 reachable from Server 1"
                    " (lan)"
                ),
            },
            {
                "host": "i2_server_1",
                "command": "ping -c 1 -W 2 10.1.2.60",
                "description": (
                    "Server 6 reachable from Server 1"
                    " (lan)"
                ),
            },
            {
                "host": "i2_server_2",
                "command": "ping -c 1 -W 2 10.1.2.10",
                "description": (
                    "Server 4 reachable from Server 2"
                    " (dmz-to-db)"
                ),
            },
            {
                "host": "i2_server_4",
                "command": "ping -c 1 -W 2 10.1.2.50",
                "description": (
                    "Server 5 reachable from Server 4"
                    " (lan)"
                ),
            },
            {
                "host": "i2_server_4",
                "command": "ping -c 1 -W 2 10.1.2.60",
                "description": (
                    "Server 6 reachable from Server 4"
                    " (lan)"
                ),
            },
            {
                "host": "i2_server_5",
                "command": "ping -c 1 -W 2 10.1.2.60",
                "description": (
                    "Server 6 reachable from Server 5"
                    " (lan)"
                ),
            },
            # Negative reachability (7)
            {
                "host": "i2_attacker",
                "command": "! ping -c 1 -W 2 10.1.2.10",
                "description": (
                    "Server 4 not reachable from"
                    " Attacker (firewall blocks)"
                ),
            },
            {
                "host": "i2_attacker",
                "command": "! ping -c 1 -W 2 10.1.2.50",
                "description": (
                    "Server 5 not reachable from"
                    " Attacker (firewall blocks)"
                ),
            },
            {
                "host": "i2_attacker",
                "command": "! ping -c 1 -W 2 10.1.2.60",
                "description": (
                    "Server 6 not reachable from"
                    " Attacker (firewall blocks)"
                ),
            },
            {
                "host": "i2_server_2",
                "command": "! ping -c 1 -W 2 10.1.2.50",
                "description": (
                    "Server 5 not reachable from"
                    " Server 2 (firewall blocks)"
                ),
            },
            {
                "host": "i2_server_2",
                "command": "! ping -c 1 -W 2 10.1.2.60",
                "description": (
                    "Server 6 not reachable from"
                    " Server 2 (firewall blocks)"
                ),
            },
            {
                "host": "i2_server_5",
                "command": "! ping -c 1 -W 2 10.1.0.10",
                "description": (
                    "Attacker not reachable from"
                    " Server 5 (lan outbound blocked)"
                ),
            },
            {
                "host": "i2_server_6",
                "command": "! ping -c 1 -W 2 10.1.0.10",
                "description": (
                    "Attacker not reachable from"
                    " Server 6 (lan outbound blocked)"
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
        "(10.0.2.0/24, Servers 1-2), Zone 2 "
        "(10.0.3.0/24, Servers 3-4), and Zone 3 "
        "(10.0.4.0/24, Servers 5-6). The network topology is shown "
        "in the attached figure.\n\n"
        "Routing architecture:\n"
        "- Perimeter-to-internal traffic: Attacker/Gateway -> "
        "Firewall (10.0.1.253) -> Log Collector (10.0.1.252) -> "
        "internal zone. The Firewall only has an interface on the "
        "perimeter network and only forwards traffic to Server 2 "
        "(10.0.2.2) and Server 3 (10.0.3.3). All other internal "
        "servers are not directly reachable from the perimeter and "
        "can only be accessed by pivoting through an internal "
        "host.\n"
        "- Cross-zone internal traffic: routes directly through "
        "the Log Collector (which has interfaces on all four "
        "networks: 10.0.1.252, 10.0.2.252, 10.0.3.252, "
        "10.0.4.252), bypassing the Firewall entirely. For "
        "example, Server 3 (Zone 2) -> Log Collector "
        "(10.0.3.252/10.0.4.252) -> Server 6 (Zone 3).\n"
        "- Implication: iptables rules on the Firewall only "
        "affect perimeter ingress/egress. To block internal "
        "lateral movement between zones, rules must be applied "
        "on the Log Collector or on the servers themselves.\n\n"
        "Each server resides on exactly one internal zone. "
        "The adjacency links are: "
        "S1-S2 (Zone 1), S1-S4 (cross-zone), S1-S6 (cross-zone), "
        "S2-S3 (cross-zone), S2-S5 (cross-zone), "
        "S3-S6 (cross-zone), S4-S5 (cross-zone), S5-S6 (Zone 3). "
        "S3 and S4 share Zone 2 but are isolated from each other "
        "by iptables rules. All connections not listed above are "
        "blocked.\n\n"
        "Gateway (10.0.1.254, Ubuntu 22): Snort IDS v2.9 "
        "(Snort alert logs are on this host)\n"
        "Firewall (10.0.1.253, Ubuntu 22): iptables packet "
        "filtering\n"
        "Log Collector (10.0.1.252, Ubuntu 22): rsyslog log "
        "aggregation, tcpdump\n"
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
        "[Priority: 1] {TCP} 10.0.4.6:55210 -> 10.0.2.1:80"
    )
    OPERATOR_FEEDBACK = (
        "Note that the Snort IDS alerts only cover the SSH brute "
        "force on server 3 and the SQL injection on server 1. "
        "However, the SQL injection alert shows the attack on "
        "server 1 originates from server 6, which indicates that "
        "server 6 is compromised as well."
    )
    SPECIFICATION = (
        "- Server 2 FTP service must remain accessible from "
        "Server 1\n"
        "- Server 3 CI/CD build pipeline (SSH) must remain "
        "accessible from Server 2\n"
        "- Server 6 PostgreSQL must not be taken offline (all "
        "services depend on it)\n"
        "- Server 4 Postfix mail delivery must not be interrupted "
        "(SLA obligation)\n"
        "- All topology links between adjacent hosts must remain "
        "operational\n"
        "- Servers may only communicate with their designated "
        "adjacent neighbors (network segmentation)\n"
        "- Server 3 and Server 4 must not communicate with each "
        "other despite sharing Zone 2"
    )
    INCIDENT_REPORT = (
        "Incident Summary:\n"
        "A multi-stage attack was detected targeting the SaaS "
        "infrastructure. The attacker (192.168.1.50) performed "
        "an SSH brute-force attack against Server 3 "
        "(10.0.3.3:22) starting at 10:15 on 02/06, successfully "
        "gaining shell access. From Server 3 the attacker "
        "pivoted laterally through the internal network, "
        "ultimately compromising Server 6 (10.0.4.6). From "
        "Server 6, a SQL injection attack (UNION SELECT) was "
        "launched against the customer portal on Server 1 "
        "(10.0.2.1:80) at 10:42.\n\n"
        "Attack Vector Analysis:\n"
        "1. Initial access: SSH brute-force on Server 3 from "
        "the perimeter (192.168.1.50 -> 10.0.3.3:22). The "
        "firewall allows perimeter-to-Server 3 traffic.\n"
        "2. Lateral movement: The attacker pivoted from Server 3 "
        "(Zone 2) to Server 6 (Zone 3) via the cross-zone route "
        "through the Log Collector.\n"
        "3. SQL injection: From Server 6 (10.0.4.6), the "
        "attacker targeted Server 1's Nginx/PHP portal with "
        "UNION SELECT injection, attempting privilege "
        "escalation.\n\n"
        "Affected Assets:\n"
        "- Server 3 (10.0.3.3): Compromised via SSH brute-force."
        " CI/CD build pipeline at risk.\n"
        "- Server 6 (10.0.4.6): Compromised via lateral "
        "movement. PostgreSQL database and Samba shares at "
        "risk.\n"
        "- Server 1 (10.0.2.1): Targeted by SQL injection from "
        "Server 6. Customer portal integrity at risk.\n\n"
        "Indicators of Compromise:\n"
        "- Attacker IP: 192.168.1.50 (external)\n"
        "- Brute-force source port: 44321\n"
        "- SQL injection source: 10.0.4.6:55210\n"
        "- Attack techniques: T1110 (Brute Force), T1021 "
        "(Remote Services), T1190 (Exploit Public-Facing "
        "Application)\n\n"
        "Severity: Critical\n"
        "Multiple servers compromised with active lateral "
        "movement and database access. Immediate containment "
        "required."
    )
    RESPONSE_PLAN = (
        "Action 1 — Contain the attack (block attacker at "
        "perimeter):\n"
        "Add an iptables rule on the firewall (10.0.1.253) to "
        "DROP all traffic from the attacker IP 192.168.1.50. "
        "This prevents further access from the external "
        "attacker.\n"
        "Command: iptables -I FORWARD -s 192.168.1.50 -j DROP\n"
        "\n"
        "Action 2 — Contain the attack (isolate compromised "
        "Server 3):\n"
        "Block outbound traffic from Server 3 to other zones "
        "to prevent further lateral movement. Server 3 reaches "
        "Server 6 (10.0.4.6) and Server 2 (10.0.2.2) via "
        "cross-zone routes through the Log Collector. Blocking those "
        "subnets on Server 3 severs the attacker's lateral "
        "movement path.\n"
        "Commands on Server 3:\n"
        "  iptables -I OUTPUT -d 10.0.4.0/24 -j DROP\n"
        "  iptables -I OUTPUT -d 10.0.2.0/24 -j DROP\n"
        "\n"
        "Action 3 — Preserve forensic evidence:\n"
        "Collect authentication logs and bash history from "
        "Server 3 and Server 6 before any cleanup. Save copies "
        "to the Log Collector for analysis.\n"
        "Commands on Server 3:\n"
        "  cp /var/log/auth.log /tmp/forensics_auth.log\n"
        "  cp /root/.bash_history /tmp/forensics_bash_history\n"
        "Commands on Server 6:\n"
        "  cp /var/log/auth.log /tmp/forensics_auth.log\n"
        "  cp /root/.bash_history /tmp/forensics_bash_history\n"
        "\n"
        "Action 4 — Evict the attacker from Server 3:\n"
        "Kill any active SSH sessions from the attacker, remove "
        "any unauthorized SSH keys, and change the root "
        "password.\n"
        "Commands on Server 3:\n"
        "  pkill -u root sshd || true\n"
        "  rm -f /root/.ssh/authorized_keys\n"
        "  echo 'root:$(openssl rand -base64 16)' | chpasswd\n"
        "\n"
        "Action 5 — Evict the attacker from Server 6:\n"
        "Kill any suspicious processes, remove unauthorized SSH "
        "keys, and change the root password.\n"
        "Commands on Server 6:\n"
        "  pkill -u root sshd || true\n"
        "  rm -f /root/.ssh/authorized_keys\n"
        "  echo 'root:$(openssl rand -base64 16)' | chpasswd\n"
        "\n"
        "Action 6 — Harden Server 3 (patch SSH):\n"
        "Disable password authentication for SSH to prevent "
        "future brute-force attacks. Only allow key-based "
        "authentication.\n"
        "Commands on Server 3:\n"
        "  sed -i 's/^#*PasswordAuthentication.*/Password"
        "Authentication no/' /etc/ssh/sshd_config\n"
        "  service ssh restart || /etc/init.d/ssh restart\n"
        "\n"
        "Action 7 — Harden Server 1 (mitigate SQL injection):\n"
        "Add a Web Application Firewall rule on Server 1 to "
        "block SQL injection patterns in HTTP requests.\n"
        "Commands on Server 1:\n"
        "  Append a location block to the Nginx config that "
        "rejects requests containing UNION SELECT patterns.\n"
        "\n"
        "Action 8 — Verify service restoration:\n"
        "Run the specification commands to confirm all required "
        "services are still operational after the response "
        "actions. Check that FTP on Server 2, SSH on Server 3, "
        "PostgreSQL on Server 6, and SMTP on Server 4 are all "
        "reachable and functional."
    )


class EXAMPLES_2:
    """
    Example incident 2 data: Tomcat RCE + PostgreSQL lateral movement.
    """
    SYSTEM_DESCRIPTION = (
        "The system is the on-premises network of a mid-size "
        "enterprise, consisting of 6 servers behind a central "
        "firewall. The network is segmented into three zones: "
        "Internet (10.1.0.0/24), DMZ (10.1.1.0/24), and "
        "Internal LAN (10.1.2.0/24). The network topology is "
        "shown in the attached figure.\n\n"
        "Server 1 is the central firewall connecting all three "
        "zones. It forwards traffic between zones according to "
        "strict iptables rules. Only HTTP/HTTPS/8080 traffic "
        "from the Internet is allowed into the DMZ (to "
        "Server 2). SSH from the Internet is allowed to "
        "Server 3. The DMZ web server (Server 2) can reach "
        "the database (Server 4) on port 5432 only. No direct "
        "Internet-to-LAN traffic is permitted.\n\n"
        "The adjacency links are: "
        "Attacker-S1 (Internet), S1-S2 (DMZ), S1-S3 (DMZ), "
        "S1-S4 (LAN), S1-S5 (LAN), S1-S6 (LAN), "
        "S2-S3 (DMZ peers), S2-S4 (DMZ-to-DB), "
        "S4-S5 (LAN), S4-S6 (LAN), S5-S6 (LAN). "
        "All connections not listed above are blocked by "
        "the firewall.\n\n"
        "Server 1 (10.1.0.1 / 10.1.1.1 / 10.1.2.1, "
        "Ubuntu 22): Central firewall, iptables, Suricata "
        "IDS\n"
        "Server 2 (10.1.1.10, Ubuntu 22): Nginx reverse "
        "proxy, Apache Tomcat 9.0.30, Java web application\n"
        "Server 3 (10.1.1.20, Debian 11): SSH jump host, "
        "key-based authentication only\n"
        "Server 4 (10.1.2.10, Debian 11): PostgreSQL "
        "database, SSH\n"
        "Server 5 (10.1.2.50, Debian 11): dnsmasq DNS/DHCP "
        "server\n"
        "Server 6 (10.1.2.60, Debian 11): Samba file server, "
        "rsync nightly backups"
    )
    SYSTEM_DESCRIPTION_IMAGE = _load_example_image("incident_2.png")
    SECURITY_ALERTS = (
        "02/10-14:32:07.881442 [**] [1:2027369:2] ET EXPLOIT "
        "Apache Tomcat Deserialization RCE Attempt "
        "(CVE-2020-9484) [**] [Classification: Attempted "
        "Administrator Privilege Gain] [Priority: 1] {TCP} "
        "198.51.100.45:48210 -> 10.1.1.10:8080\n\n"
        "Tomcat access.log (Server 2, 10.1.1.10):\n"
        "198.51.100.45 - - [10/Feb/2026:14:32:08 +0000] "
        "\"POST /api/v1/upload HTTP/1.1\" 200 412 \"-\" "
        "\"python-requests/2.28.1\"\n"
        "198.51.100.45 - - [10/Feb/2026:14:33:15 +0000] "
        "\"GET /shell.jsp HTTP/1.1\" 200 89 \"-\" "
        "\"Mozilla/5.0\"\n\n"
        "PostgreSQL log (Server 4, 10.1.2.10):\n"
        "2026-02-10 14:45:22.103 UTC [5432] app_svc@"
        "crm_production LOG: statement: CREATE TABLE "
        "cmd_exec(cmd_output text);\n"
        "2026-02-10 14:45:23.207 UTC [5432] app_svc@"
        "crm_production LOG: statement: COPY cmd_exec "
        "FROM PROGRAM 'id';\n\n"
        "Syslog (Server 4, 10.1.2.10):\n"
        "Feb 10 14:55:01 server4 kernel: CPU 98%: process "
        "'kworker/0:2' pid 31337\n"
        "Feb 10 14:55:12 server4 kernel: xmrig[31337]: "
        "segfault at 0x0 ip 00007f3a2b rsp 00007ffd3c "
        "error 4 in xmrig[400000+1c6000]\n"
        "Feb 10 14:58:33 server4 dnsmasq[892]: query[TXT] "
        "aHR0cDovL2V4ZmlsLmV4YW1wbGUu.t.evil.example.com "
        "from 10.1.2.10\n"
        "Feb 10 14:58:34 server4 dnsmasq[892]: query[TXT] "
        "Y29tL2NvbGxlY3Q/ZD1jcmVkcw==.t.evil.example.com "
        "from 10.1.2.10"
    )
    OPERATOR_FEEDBACK = (
        "The Suricata alert on the firewall caught the "
        "initial Tomcat deserialization exploit from "
        "198.51.100.45. The Tomcat access.log confirms "
        "a malicious upload followed by a JSP webshell "
        "access. The attacker then used the plaintext "
        "database credentials found in Server 2's "
        "db_config.xml to connect to PostgreSQL on "
        "Server 4, where they leveraged COPY FROM PROGRAM "
        "for OS command execution. The syslog entries on "
        "Server 4 show a crypto-miner (xmrig) consuming "
        "98% CPU and DNS tunneling queries to "
        "evil.example.com for data exfiltration."
    )
    SPECIFICATION = (
        "- PostgreSQL on Server 4 must remain accessible "
        "from Server 2 (application dependency)\n"
        "- Web server (Server 2) downtime must not exceed "
        "10 minutes; serve a maintenance page via Nginx "
        "while Tomcat is offline\n"
        "- Firewall rules on Server 1 must remain intact "
        "and operational\n"
        "- SSH on Server 3 must remain operational for "
        "administrator access\n"
        "- DNS service on Server 5 must not be disrupted\n"
        "- Backup jobs on Server 6 must continue running\n"
        "- All topology links between adjacent hosts must "
        "remain operational\n"
        "- Internet hosts must not be able to reach LAN "
        "servers (4, 5, 6) directly"
    )
    INCIDENT_REPORT = (
        "Incident Summary:\n"
        "A five-stage attack was detected targeting the "
        "enterprise network. The attacker (198.51.100.45) "
        "exploited CVE-2020-9484 (Apache Tomcat session "
        "deserialization) on the DMZ web server "
        "(Server 2, 10.1.1.10) at 14:32 on 02/10, "
        "uploading a JSP webshell for persistent access. "
        "From Server 2, the attacker retrieved plaintext "
        "PostgreSQL credentials from db_config.xml and "
        "pivoted to the internal database server "
        "(Server 4, 10.1.2.10). On Server 4, the attacker "
        "leveraged CVE-2019-9193 (PostgreSQL COPY FROM "
        "PROGRAM) to execute OS commands, deployed a "
        "crypto-miner (xmrig), and established DNS "
        "tunneling for data exfiltration.\n\n"
        "Attack Vector Analysis:\n"
        "1. Initial access: Exploitation of CVE-2020-9484 "
        "on Tomcat 9.0.30 via a crafted serialized session "
        "file upload (198.51.100.45 -> 10.1.1.10:8080). "
        "The FileStore PersistentManager deserialized the "
        "malicious payload.\n"
        "2. Persistence: JSP webshell deployed at "
        "/shell.jsp and cron job installed at "
        "/etc/cron.d/.cleanup.sh for callback "
        "persistence.\n"
        "3. Credential theft: Plaintext database "
        "credentials (app_svc / SuperSecret123!) extracted "
        "from /opt/tomcat/conf/db_config.xml on "
        "Server 2.\n"
        "4. Lateral movement: The attacker connected from "
        "Server 2 to Server 4's PostgreSQL (port 5432) "
        "using the stolen credentials and exploited COPY "
        "FROM PROGRAM to gain OS-level command "
        "execution.\n"
        "5. Impact: Crypto-miner (xmrig) deployed as "
        "/tmp/.kworker consuming 98% CPU, and DNS "
        "tunneling established to evil.example.com for "
        "exfiltrating CRM database contents.\n\n"
        "Affected Assets:\n"
        "- Server 2 (10.1.1.10): Compromised via Tomcat "
        "deserialization. Webshell + cron persistence "
        "installed.\n"
        "- Server 4 (10.1.2.10): Compromised via "
        "PostgreSQL COPY FROM PROGRAM. Crypto-miner + DNS "
        "tunneling active.\n\n"
        "Indicators of Compromise:\n"
        "- Attacker IP: 198.51.100.45 (external)\n"
        "- Webshell: /opt/tomcat/webapps/ROOT/shell.jsp\n"
        "- Cron persistence: /etc/cron.d/.cleanup.sh\n"
        "- Crypto-miner: /tmp/.kworker (xmrig)\n"
        "- DNS tunneling: *.t.evil.example.com TXT "
        "queries\n"
        "- Stolen credentials: app_svc / SuperSecret123!\n"
        "- PostgreSQL artifact: cmd_exec table in "
        "crm_production\n"
        "- MITRE ATT&CK: T1190 (Exploit Public-Facing "
        "Application), T1505.003 (Web Shell), T1053.003 "
        "(Cron), T1552.001 (Credentials In Files), "
        "T1210 (Exploitation of Remote Services), "
        "T1496 (Resource Hijacking), T1048.001 "
        "(Exfiltration Over DNS)\n\n"
        "Severity: Critical\n"
        "Two servers compromised with active crypto-mining "
        "and data exfiltration. Immediate containment "
        "required."
    )
    RESPONSE_PLAN = (
        "Action 1 — Block attacker at firewall:\n"
        "Add an iptables rule on Server 1 (10.1.0.1) to "
        "DROP all traffic from the attacker IP "
        "198.51.100.45. This stops further exploitation "
        "from the external attacker.\n"
        "Command on Server 1:\n"
        "  iptables -I FORWARD -s 198.51.100.45 -j DROP\n"
        "\n"
        "Action 2 — Contain Server 2 (DMZ web server):\n"
        "Block outbound traffic from Server 2 to the "
        "Internal LAN to prevent further lateral movement. "
        "Switch Nginx to serve a static maintenance page "
        "while Tomcat is taken offline.\n"
        "Commands on Server 1:\n"
        "  iptables -I FORWARD -s 10.1.1.10 "
        "-d 10.1.2.0/24 -j DROP\n"
        "Commands on Server 2:\n"
        "  cp /etc/nginx/sites-available/maintenance "
        "/etc/nginx/sites-enabled/default\n"
        "  nginx -s reload\n"
        "\n"
        "Action 3 — Kill crypto-miner and block DNS "
        "tunneling on Server 4:\n"
        "Terminate the xmrig process and block outbound "
        "DNS tunneling traffic to the malicious domain.\n"
        "Commands on Server 4:\n"
        "  pkill -f kworker_fake || true\n"
        "  kill $(pgrep -f '.kworker') 2>/dev/null "
        "|| true\n"
        "  iptables -I OUTPUT -d evil.example.com "
        "-j DROP 2>/dev/null || true\n"
        "\n"
        "Action 4 — Preserve forensic evidence:\n"
        "Collect attack artifacts from Server 2 and "
        "Server 4 before cleanup.\n"
        "Commands on Server 2:\n"
        "  tar czf /tmp/forensics_s2.tar.gz "
        "/opt/tomcat/logs/access.log "
        "/opt/tomcat/webapps/ROOT/shell.jsp "
        "/etc/cron.d/.cleanup.sh "
        "/root/.bash_history 2>/dev/null\n"
        "Commands on Server 4:\n"
        "  tar czf /tmp/forensics_s4.tar.gz "
        "/var/log/postgresql/ /var/log/syslog "
        "/root/.bash_history 2>/dev/null\n"
        "\n"
        "Action 5 — Eradicate webshell and persistence "
        "on Server 2:\n"
        "Remove the JSP webshell, cron persistence, and "
        "any uploaded malicious files.\n"
        "Commands on Server 2:\n"
        "  rm -f /opt/tomcat/webapps/ROOT/shell.jsp\n"
        "  rm -f /etc/cron.d/.cleanup.sh\n"
        "  find /opt/tomcat/webapps/ -name '*.jsp' "
        "-newer /opt/tomcat/webapps/ROOT/index.jsp "
        "-delete\n"
        "\n"
        "Action 6 — Eradicate attacker foothold on "
        "Server 4:\n"
        "Drop the cmd_exec table used for OS command "
        "execution, rotate the compromised database "
        "credentials, and remove the crypto-miner "
        "binary.\n"
        "Commands on Server 4:\n"
        "  sudo -u postgres psql -d crm_production "
        "-c \"DROP TABLE IF EXISTS cmd_exec;\"\n"
        "  sudo -u postgres psql -c \"ALTER USER app_svc "
        "WITH PASSWORD 'new_secure_password_here';\"\n"
        "  rm -f /tmp/.kworker /tmp/.kworker_fake\n"
        "\n"
        "Action 7 — Harden Server 2 (patch Tomcat):\n"
        "Remove the vulnerable FileStore session "
        "persistence configuration and upgrade Tomcat to "
        "a patched version.\n"
        "Commands on Server 2:\n"
        "  Remove the PersistentManager configuration "
        "from context.xml to disable FileStore session "
        "deserialization.\n"
        "  Update Tomcat to version >= 9.0.35 to patch "
        "CVE-2020-9484.\n"
        "\n"
        "Action 8 — Harden Server 4 (revoke SUPERUSER):\n"
        "Revoke unnecessary SUPERUSER privileges from the "
        "application database user to prevent future COPY "
        "FROM PROGRAM abuse.\n"
        "Commands on Server 4:\n"
        "  sudo -u postgres psql -c \"ALTER USER app_svc "
        "NOSUPERUSER;\"\n"
        "\n"
        "Action 9 — Restore Server 2 to production:\n"
        "Re-enable the Nginx reverse proxy to Tomcat and "
        "restore DMZ-to-DB connectivity on the firewall.\n"
        "Commands on Server 1:\n"
        "  iptables -D FORWARD -s 10.1.1.10 "
        "-d 10.1.2.0/24 -j DROP\n"
        "Commands on Server 2:\n"
        "  cp /etc/nginx/sites-available/production "
        "/etc/nginx/sites-enabled/default\n"
        "  nginx -s reload\n"
        "\n"
        "Action 10 — Verify service restoration:\n"
        "Run the specification commands to confirm all "
        "required services are operational after the "
        "response actions. Check HTTP on Server 2, SSH on "
        "Server 3, PostgreSQL on Server 4, DNS on "
        "Server 5, and Samba on Server 6."
    )
