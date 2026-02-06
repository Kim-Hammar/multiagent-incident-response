"""
Shared constants for the CCS Response Planner backend.
"""


class API:
    """
    Constants related to API routes
    """
    PREFIX = "/api"
    HEALTH_ROUTE = "/api/health"
    PLAN_ROUTE = "/api/plan"


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
