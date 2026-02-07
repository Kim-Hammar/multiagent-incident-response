"""
Shared constants for the CCS Response Planner backend.
"""


class API:
    """
    Constants related to API routes
    """
    PREFIX = "/api"
    HEALTH_RESOURCE = "health"
    PLAN_RESOURCE = "plan"
    EXAMPLE_RESOURCE = "example"
    LOGIN_RESOURCE = "login"
    HEALTH_ROUTE = "/api/health"
    PLAN_ROUTE = "/api/plan"
    EXAMPLE_ROUTE = "/api/example"
    LOGIN_ROUTE = "/api/login"


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


class EXAMPLES:
    """
    Example incident data for populating the response planner form.
    """
    SYSTEM_DESCRIPTION = (
        "The system is a small corporate network consisting of: "
        "a web server (Apache HTTP on 10.0.0.1), "
        "a database server (PostgreSQL on 10.0.0.2), "
        "a firewall/gateway (pfSense on 10.0.0.254), "
        "and five employee workstations (10.0.0.100-104). "
        "The web server hosts a public-facing customer portal "
        "and communicates with the database over a private VLAN."
    )
    SECURITY_ALERTS = (
        "[2025-06-10 02:13:07] ALERT Snort: "
        "Brute-force SSH login attempt on 10.0.0.1 "
        "from 192.168.1.50 (350 attempts in 10 min)\n"
        "[2025-06-10 02:15:22] ALERT OSSEC: "
        "New user account 'backdoor' created on 10.0.0.1\n"
        "[2025-06-10 02:17:45] ALERT Snort: "
        "Outbound connection from 10.0.0.1 to known C2 server "
        "203.0.113.66:4444\n"
        "[2025-06-10 02:20:01] WARNING Firewall: "
        "Unusual spike in outbound traffic from 10.0.0.1 "
        "(500 MB in 5 min)"
    )
    OPERATOR_FEEDBACK = (
        "The web server on 10.0.0.1 cannot be taken offline "
        "immediately because it hosts a critical customer portal "
        "with active sessions. Any isolation must preserve "
        "database connectivity on 10.0.0.2 until a maintenance "
        "window at 06:00 UTC. Prioritize blocking the C2 channel "
        "and removing the unauthorized 'backdoor' account first."
    )
