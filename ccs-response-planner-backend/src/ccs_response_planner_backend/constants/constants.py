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
    NETWORK_NAME = "ccs_dt_network"
    CONTAINER_PREFIX = "ccs_dt_"
    SUBNET = "10.0.0.0/24"
    GATEWAY = "10.0.0.100"


class DIGITAL_TWIN:
    """
    Constants related to the digital twin configuration.
    """
    DEFAULT_CONFIG: dict[str, Any] = {
        "hosts": [
            {
                "id": "gateway",
                "name": "Gateway",
                "docker_image": "ubuntu:22.04",
                "ip_addresses": ["10.0.0.254"],
            },
            {
                "id": "firewall",
                "name": "Firewall",
                "docker_image": "ubuntu:22.04",
                "ip_addresses": ["10.0.0.253"],
            },
            {
                "id": "ids",
                "name": "IDS (Snort)",
                "docker_image": "ubuntu:22.04",
                "ip_addresses": ["10.0.0.252"],
            },
            {
                "id": "server_1",
                "name": "Server 1",
                "docker_image": "debian:9.2",
                "ip_addresses": ["10.0.0.1"],
            },
            {
                "id": "server_2",
                "name": "Server 2",
                "docker_image": "debian:jessie",
                "ip_addresses": ["10.0.0.2"],
            },
            {
                "id": "server_3",
                "name": "Server 3",
                "docker_image": "ubuntu:20.04",
                "ip_addresses": ["10.0.0.3"],
            },
            {
                "id": "server_4",
                "name": "Server 4",
                "docker_image": "debian:jessie",
                "ip_addresses": ["10.0.0.4"],
            },
            {
                "id": "server_5",
                "name": "Server 5",
                "docker_image": "debian:jessie",
                "ip_addresses": ["10.0.0.5"],
            },
            {
                "id": "server_6",
                "name": "Server 6",
                "docker_image": "debian:jessie",
                "ip_addresses": ["10.0.0.6"],
            },
        ],
        "links": [
            {"source": "gateway", "target": "firewall"},
            {"source": "firewall", "target": "ids"},
            {"source": "ids", "target": "server_1"},
            {"source": "ids", "target": "server_2"},
            {"source": "ids", "target": "server_3"},
            {"source": "ids", "target": "server_4"},
            {"source": "ids", "target": "server_5"},
            {"source": "ids", "target": "server_6"},
            {"source": "server_1", "target": "server_2"},
            {"source": "server_3", "target": "server_4"},
            {"source": "server_5", "target": "server_6"},
            {"source": "server_1", "target": "server_3"},
            {"source": "server_3", "target": "server_5"},
        ],
    }


class EXAMPLES:
    """
    Example incident data for populating the response planner form.
    """
    SYSTEM_DESCRIPTION = (
        "The system consists of 6 servers providing network services "
        "to a client population through a cloud gateway.\n\n"
        "Gateway (Ubuntu 22): Snort IDS v2.9.17.1\n"
        "Server 1 (10.0.0.1, Debian 9.2): Apache 2 web server\n"
        "Server 2 (10.0.0.2, Debian Jessie): FTP server\n"
        "Server 3 (10.0.0.3, Ubuntu 20): SSH, Spark "
        "(known vulnerability: weak SSH password)\n"
        "Server 4 (10.0.0.4, Debian Jessie): PhpMailer\n"
        "Server 5 (10.0.0.5, Debian Jessie): SSH, Spring Boot\n"
        "Server 6 (10.0.0.6, Debian Jessie): PostgreSQL, Samba "
        "(known vulnerability: CVE-2017-7494)"
    )
    SYSTEM_DESCRIPTION_IMAGE = _load_example_image()
    SECURITY_ALERTS = (
        "02/06-10:15:22.341201 [**] [1:2006546:3] ET SCAN SSH "
        "Brute Force Login Attempt [**] [Classification: Attempted "
        "Information Leak] [Priority: 2] {TCP} "
        "192.168.1.50:44321 -> 10.0.0.3:22\n\n"
        "02/06-10:42:15.889102 [**] [1:2014473:3] ET EXPLOIT "
        "Possible SQL Injection Attempt (UNION SELECT) [**] "
        "[Classification: Attempted Administrator Privilege Gain] "
        "[Priority: 1] {TCP} 10.0.0.3:55210 -> 10.0.0.1:80"
    )
    OPERATOR_FEEDBACK = (
        "Note that the Snort IDS alerts only cover the SSH brute "
        "force on server 3 and the SQL injection on server 1. "
        "There is no alert for the Samba exploit on server 6 "
        "(CVE-2017-7494) because the IDS lacks a matching "
        "signature. However, the SQL injection alert shows the "
        "attack on server 1 originates from server 3, indicating "
        "server 3 is compromised. Prioritize containment of "
        "server 3 as the attacker's pivot point."
    )
