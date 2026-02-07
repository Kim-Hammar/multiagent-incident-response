"""Tests for backend constants."""
from ccs_response_planner_backend.constants.constants import (
    API, EXAMPLES, GENERAL, SERVER,
)


def test_api_prefix_is_string() -> None:
    assert isinstance(API.PREFIX, str)
    assert API.PREFIX == "/api"


def test_health_route_starts_with_api_prefix() -> None:
    assert API.HEALTH_ROUTE.startswith(API.PREFIX)
    assert API.HEALTH_ROUTE == "/api/health"


def test_plan_route_starts_with_api_prefix() -> None:
    assert API.PLAN_ROUTE.startswith(API.PREFIX)
    assert API.PLAN_ROUTE == "/api/plan"


def test_default_port() -> None:
    assert isinstance(SERVER.DEFAULT_PORT, int)
    assert SERVER.DEFAULT_PORT == 8888


def test_default_host() -> None:
    assert isinstance(SERVER.DEFAULT_HOST, str)
    assert SERVER.DEFAULT_HOST == "127.0.0.1"


def test_default_num_threads() -> None:
    assert isinstance(SERVER.DEFAULT_NUM_THREADS, int)
    assert SERVER.DEFAULT_NUM_THREADS == 100


def test_example_route_starts_with_api_prefix() -> None:
    assert API.EXAMPLE_ROUTE.startswith(API.PREFIX)
    assert API.EXAMPLE_ROUTE == "/api/example"


def test_app_name() -> None:
    assert isinstance(GENERAL.APP_NAME, str)
    assert GENERAL.APP_NAME == "CCS Incident Response Planner"


def test_examples_system_description() -> None:
    assert isinstance(EXAMPLES.SYSTEM_DESCRIPTION, str)
    assert len(EXAMPLES.SYSTEM_DESCRIPTION) > 0


def test_examples_security_alerts() -> None:
    assert isinstance(EXAMPLES.SECURITY_ALERTS, str)
    assert len(EXAMPLES.SECURITY_ALERTS) > 0


def test_examples_operator_feedback() -> None:
    assert isinstance(EXAMPLES.OPERATOR_FEEDBACK, str)
    assert len(EXAMPLES.OPERATOR_FEEDBACK) > 0
