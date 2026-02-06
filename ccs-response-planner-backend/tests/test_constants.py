"""Tests for backend constants."""
from ccs_response_planner_backend.constants import (
    API_PREFIX,
    APP_NAME,
    DEFAULT_HOST,
    DEFAULT_NUM_THREADS,
    DEFAULT_PORT,
    HEALTH_ROUTE,
    PLAN_ROUTE,
)


def test_api_prefix_is_string() -> None:
    assert isinstance(API_PREFIX, str)
    assert API_PREFIX == "/api"


def test_health_route_starts_with_api_prefix() -> None:
    assert HEALTH_ROUTE.startswith(API_PREFIX)
    assert HEALTH_ROUTE == "/api/health"


def test_plan_route_starts_with_api_prefix() -> None:
    assert PLAN_ROUTE.startswith(API_PREFIX)
    assert PLAN_ROUTE == "/api/plan"


def test_default_port() -> None:
    assert isinstance(DEFAULT_PORT, int)
    assert DEFAULT_PORT == 8888


def test_default_host() -> None:
    assert isinstance(DEFAULT_HOST, str)
    assert DEFAULT_HOST == "127.0.0.1"


def test_default_num_threads() -> None:
    assert isinstance(DEFAULT_NUM_THREADS, int)
    assert DEFAULT_NUM_THREADS == 100


def test_app_name() -> None:
    assert isinstance(APP_NAME, str)
    assert APP_NAME == "CCS Incident Response Planner"
