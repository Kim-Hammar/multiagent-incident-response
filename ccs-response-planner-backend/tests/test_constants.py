"""Tests for backend constants."""
from ccs_response_planner_backend.constants.constants import (
    API, AUTH, DB, DIGITAL_TWIN, DOCKER, EXAMPLES, GENERAL, SERVER,
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


def test_examples_specification() -> None:
    assert isinstance(EXAMPLES.SPECIFICATION, str)
    assert len(EXAMPLES.SPECIFICATION) > 0


def test_login_route_starts_with_api_prefix() -> None:
    assert API.LOGIN_ROUTE.startswith(API.PREFIX)
    assert API.LOGIN_ROUTE == "/api/login"


def test_db_default_host() -> None:
    assert isinstance(DB.DEFAULT_HOST, str)
    assert DB.DEFAULT_HOST == "localhost"


def test_db_default_port() -> None:
    assert isinstance(DB.DEFAULT_PORT, int)
    assert DB.DEFAULT_PORT == 5432


def test_db_table_names() -> None:
    assert DB.MANAGEMENT_USERS_TABLE == "management_users"
    assert DB.SESSION_TOKENS_TABLE == "session_tokens"


def test_auth_token_header() -> None:
    assert AUTH.TOKEN_HEADER == "Authorization"
    assert AUTH.TOKEN_PREFIX == "Bearer "
    assert AUTH.TOKEN_LENGTH == 32


def test_llm_resource() -> None:
    assert API.LLM_RESOURCE == "llm"


def test_llm_route_starts_with_api_prefix() -> None:
    assert API.LLM_ROUTE.startswith(API.PREFIX)
    assert API.LLM_ROUTE == "/api/llm"


def test_docker_network_name() -> None:
    assert DOCKER.NETWORK_NAME == "ccs_dt_network"


def test_docker_container_prefix() -> None:
    assert DOCKER.CONTAINER_PREFIX == "ccs_dt_"


def test_docker_subnet() -> None:
    assert DOCKER.SUBNET == "10.0.0.0/24"


def test_docker_gateway() -> None:
    assert DOCKER.GATEWAY == "10.0.0.100"


def test_digital_twin_default_config_hosts() -> None:
    """
    All hosts in the default config should use ccs-dt- image names.
    """
    hosts = DIGITAL_TWIN.DEFAULT_CONFIG["hosts"]
    assert len(hosts) == 9
    for host in hosts:
        assert "ccs-dt-" in host["docker_image"], (
            f"Host {host['id']} uses image {host['docker_image']} "
            f"which does not contain 'ccs-dt-'"
        )


def test_digital_twin_deploy_route() -> None:
    assert API.DIGITAL_TWIN_DEPLOY_ROUTE.startswith(API.PREFIX)
    assert API.DIGITAL_TWIN_DEPLOY_ROUTE == "/api/digital-twin/deploy"


def test_digital_twin_stop_route() -> None:
    assert API.DIGITAL_TWIN_STOP_ROUTE.startswith(API.PREFIX)
    assert API.DIGITAL_TWIN_STOP_ROUTE == "/api/digital-twin/stop"


def test_digital_twin_status_route() -> None:
    assert API.DIGITAL_TWIN_STATUS_ROUTE.startswith(API.PREFIX)
    assert API.DIGITAL_TWIN_STATUS_ROUTE == "/api/digital-twin/status"


def test_digital_twin_default_config_has_specification_commands() -> None:
    """
    The default DT config must include a non-empty specification_commands list.
    """
    cmds = DIGITAL_TWIN.DEFAULT_CONFIG["specification_commands"]
    assert isinstance(cmds, list)
    assert len(cmds) > 0
    for cmd in cmds:
        assert "command" in cmd
        assert "description" in cmd
