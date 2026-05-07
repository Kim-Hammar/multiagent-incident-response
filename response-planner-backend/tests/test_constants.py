"""Tests for backend constants."""
from response_planner_backend.constants.constants import (
    API, AUTH, DB, DIGITAL_TWIN, DOCKER, EXAMPLES, EXAMPLES_2,
    GENERAL, SERVER,
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
    assert GENERAL.APP_NAME == "Incident Response Planner"


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


def test_tavily_resource() -> None:
    assert API.TAVILY_RESOURCE == "tavily"


def test_tavily_route_starts_with_api_prefix() -> None:
    assert API.TAVILY_ROUTE.startswith(API.PREFIX)
    assert API.TAVILY_ROUTE == "/api/tavily"


def test_tavily_search_route_starts_with_api_prefix() -> None:
    assert API.TAVILY_SEARCH_ROUTE.startswith(API.PREFIX)
    assert API.TAVILY_SEARCH_ROUTE == "/api/tavily/search"


def test_nvd_route_starts_with_api_prefix() -> None:
    assert API.NVD_ROUTE.startswith(API.PREFIX)
    assert API.NVD_ROUTE == "/api/nvd"


def test_nvd_search_route_starts_with_api_prefix() -> None:
    assert API.NVD_SEARCH_ROUTE.startswith(API.PREFIX)
    assert API.NVD_SEARCH_ROUTE == "/api/nvd/search"


def test_mitre_route_starts_with_api_prefix() -> None:
    assert API.MITRE_ROUTE.startswith(API.PREFIX)
    assert API.MITRE_ROUTE == "/api/mitre"


def test_mitre_search_route_starts_with_api_prefix() -> None:
    assert API.MITRE_SEARCH_ROUTE.startswith(API.PREFIX)
    assert API.MITRE_SEARCH_ROUTE == "/api/mitre/search"


def test_virustotal_route_starts_with_api_prefix() -> None:
    assert API.VIRUSTOTAL_ROUTE.startswith(API.PREFIX)
    assert API.VIRUSTOTAL_ROUTE == "/api/virustotal"


def test_virustotal_scan_route_starts_with_api_prefix() -> None:
    assert API.VIRUSTOTAL_SCAN_ROUTE.startswith(API.PREFIX)
    assert API.VIRUSTOTAL_SCAN_ROUTE == "/api/virustotal/scan"


def test_abuseipdb_route_starts_with_api_prefix() -> None:
    assert API.ABUSEIPDB_ROUTE.startswith(API.PREFIX)
    assert API.ABUSEIPDB_ROUTE == "/api/abuseipdb"


def test_abuseipdb_check_route_starts_with_api_prefix() -> None:
    assert API.ABUSEIPDB_CHECK_ROUTE.startswith(API.PREFIX)
    assert API.ABUSEIPDB_CHECK_ROUTE == "/api/abuseipdb/check"


def test_otx_route_starts_with_api_prefix() -> None:
    assert API.OTX_ROUTE.startswith(API.PREFIX)
    assert API.OTX_ROUTE == "/api/otx"


def test_otx_search_route_starts_with_api_prefix() -> None:
    assert API.OTX_SEARCH_ROUTE.startswith(API.PREFIX)
    assert API.OTX_SEARCH_ROUTE == "/api/otx/search"


def test_docker_network_prefix() -> None:
    assert DOCKER.NETWORK_PREFIX == "dt_net_"


def test_docker_container_prefix() -> None:
    assert DOCKER.CONTAINER_PREFIX == "dt_"


def test_digital_twin_default_config_has_networks() -> None:
    """
    The default DT config must include a non-empty networks list.
    """
    nets = DIGITAL_TWIN.DEFAULT_CONFIG["networks"]
    assert isinstance(nets, list)
    assert len(nets) == 4
    for net in nets:
        assert "id" in net
        assert "subnet" in net


def test_digital_twin_default_config_hosts() -> None:
    """
    All hosts in the default config should use dt- image names.
    """
    hosts = DIGITAL_TWIN.DEFAULT_CONFIG["hosts"]
    assert len(hosts) == 10
    for host in hosts:
        assert "dt-" in host["docker_image"], (
            f"Host {host['id']} uses image {host['docker_image']} "
            f"which does not contain 'dt-'"
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
    The default DT config must include 34 specification commands
    (4 service + 22 positive reachability + 8 negative reachability).
    """
    cmds = DIGITAL_TWIN.DEFAULT_CONFIG["specification_commands"]
    assert isinstance(cmds, list)
    assert len(cmds) == 34
    for cmd in cmds:
        assert "command" in cmd
        assert "description" in cmd


def test_dt_exec_route_starts_with_api_prefix() -> None:
    assert API.DT_EXEC_ROUTE.startswith(API.PREFIX)
    assert API.DT_EXEC_ROUTE == "/api/dt-exec"


def test_dt_exec_run_route_starts_with_api_prefix() -> None:
    assert API.DT_EXEC_RUN_ROUTE.startswith(API.PREFIX)
    assert API.DT_EXEC_RUN_ROUTE == "/api/dt-exec/run"


def test_dt_logs_route_starts_with_api_prefix() -> None:
    assert API.DT_LOGS_ROUTE.startswith(API.PREFIX)
    assert API.DT_LOGS_ROUTE == "/api/dt-logs"


def test_dt_logs_fetch_route_starts_with_api_prefix() -> None:
    assert API.DT_LOGS_FETCH_ROUTE.startswith(API.PREFIX)
    assert API.DT_LOGS_FETCH_ROUTE == "/api/dt-logs/fetch"


def test_dt_python_route_starts_with_api_prefix() -> None:
    assert API.DT_PYTHON_ROUTE.startswith(API.PREFIX)
    assert API.DT_PYTHON_ROUTE == "/api/dt-python"


def test_dt_python_run_route_starts_with_api_prefix() -> None:
    assert API.DT_PYTHON_RUN_ROUTE.startswith(API.PREFIX)
    assert API.DT_PYTHON_RUN_ROUTE == "/api/dt-python/run"


def test_dt_python_start_route_starts_with_api_prefix() -> None:
    assert API.DT_PYTHON_START_ROUTE.startswith(API.PREFIX)
    assert API.DT_PYTHON_START_ROUTE == "/api/dt-python/start"


def test_dt_python_stop_route_starts_with_api_prefix() -> None:
    assert API.DT_PYTHON_STOP_ROUTE.startswith(API.PREFIX)
    assert API.DT_PYTHON_STOP_ROUTE == "/api/dt-python/stop"


def test_agents_resource() -> None:
    assert API.AGENTS_RESOURCE == "agents"


def test_agents_route_starts_with_api_prefix() -> None:
    assert API.AGENTS_ROUTE.startswith(API.PREFIX)
    assert API.AGENTS_ROUTE == "/api/agents"


def test_agents_report_step_route_starts_with_api_prefix() -> None:
    assert API.AGENTS_REPORT_STEP_ROUTE.startswith(API.PREFIX)
    assert API.AGENTS_REPORT_STEP_ROUTE == "/api/agents/report/step"


def test_agents_report_tool_route_starts_with_api_prefix() -> None:
    assert API.AGENTS_REPORT_TOOL_ROUTE.startswith(API.PREFIX)
    assert API.AGENTS_REPORT_TOOL_ROUTE == "/api/agents/report/tool"


def test_agents_report_prompt_route_starts_with_api_prefix() -> None:
    assert API.AGENTS_REPORT_PROMPT_ROUTE.startswith(API.PREFIX)
    assert API.AGENTS_REPORT_PROMPT_ROUTE == "/api/agents/report/prompt"


def test_specification_commands_include_reachability() -> None:
    """
    Specification commands must include both positive and negative
    reachability checks using ping.
    """
    cmds = DIGITAL_TWIN.DEFAULT_CONFIG["specification_commands"]
    ping_cmds = [c for c in cmds if "ping" in c["command"]]
    positive = [c for c in ping_cmds
                if not c["command"].startswith("!")]
    negative = [c for c in ping_cmds
                if c["command"].startswith("!")]
    assert len(positive) == 22
    assert len(negative) == 8


def test_examples_2_system_description() -> None:
    assert isinstance(EXAMPLES_2.SYSTEM_DESCRIPTION, str)
    assert "Tomcat" in EXAMPLES_2.SYSTEM_DESCRIPTION
    assert "10.1.1.0/24" in EXAMPLES_2.SYSTEM_DESCRIPTION


def test_examples_2_security_alerts() -> None:
    assert isinstance(EXAMPLES_2.SECURITY_ALERTS, str)
    assert "CVE-2020-9484" in EXAMPLES_2.SECURITY_ALERTS
    assert "198.51.100.45" in EXAMPLES_2.SECURITY_ALERTS


def test_examples_2_operator_feedback() -> None:
    assert isinstance(EXAMPLES_2.OPERATOR_FEEDBACK, str)
    assert "xmrig" in EXAMPLES_2.OPERATOR_FEEDBACK


def test_examples_2_specification() -> None:
    assert isinstance(EXAMPLES_2.SPECIFICATION, str)
    assert "PostgreSQL" in EXAMPLES_2.SPECIFICATION


def test_examples_2_incident_report() -> None:
    assert isinstance(EXAMPLES_2.INCIDENT_REPORT, str)
    assert "CVE-2020-9484" in EXAMPLES_2.INCIDENT_REPORT
    assert "CVE-2019-9193" in EXAMPLES_2.INCIDENT_REPORT


def test_examples_2_response_plan() -> None:
    assert isinstance(EXAMPLES_2.RESPONSE_PLAN, str)
    assert "Action 1" in EXAMPLES_2.RESPONSE_PLAN
    assert "Action 10" in EXAMPLES_2.RESPONSE_PLAN


def test_examples_2_system_description_image() -> None:
    img = EXAMPLES_2.SYSTEM_DESCRIPTION_IMAGE
    assert isinstance(img, str)
    if img:
        assert img.startswith("data:image/png;base64,")


def test_incident_2_config_has_networks() -> None:
    """
    The incident 2 DT config must include 3 networks.
    """
    nets = DIGITAL_TWIN.INCIDENT_2_CONFIG["networks"]
    assert isinstance(nets, list)
    assert len(nets) == 3
    for net in nets:
        assert "id" in net
        assert "subnet" in net


def test_incident_2_config_hosts() -> None:
    """
    All hosts in the incident 2 config should use dt- image names.
    """
    hosts = DIGITAL_TWIN.INCIDENT_2_CONFIG["hosts"]
    assert len(hosts) == 7
    for host in hosts:
        assert "dt-" in host["docker_image"], (
            f"Host {host['id']} uses image {host['docker_image']} "
            f"which does not contain 'dt-'"
        )


def test_incident_2_config_links() -> None:
    """
    The incident 2 DT config must include 11 links.
    """
    links = DIGITAL_TWIN.INCIDENT_2_CONFIG["links"]
    assert isinstance(links, list)
    assert len(links) == 11


def test_incident_2_config_has_specification_commands() -> None:
    """
    The incident 2 DT config must include 25 specification commands
    (5 service + 15 positive reachability + 5 negative reachability).
    """
    cmds = DIGITAL_TWIN.INCIDENT_2_CONFIG["specification_commands"]
    assert isinstance(cmds, list)
    assert len(cmds) == 25
    for cmd in cmds:
        assert "command" in cmd
        assert "description" in cmd


def test_incident_2_specification_commands_reachability() -> None:
    """
    Specification commands must include both positive and negative
    reachability checks using ping.
    """
    cmds = DIGITAL_TWIN.INCIDENT_2_CONFIG["specification_commands"]
    ping_cmds = [c for c in cmds if "ping" in c["command"]]
    positive = [c for c in ping_cmds
                if not c["command"].startswith("!")]
    negative = [c for c in ping_cmds
                if c["command"].startswith("!")]
    assert len(positive) == 15
    assert len(negative) == 5


def test_agents_report_manager_step_route() -> None:
    assert API.AGENTS_REPORT_MANAGER_STEP_ROUTE.startswith(
        API.PREFIX,
    )
    assert API.AGENTS_REPORT_MANAGER_STEP_ROUTE == (
        "/api/agents/report-manager/step"
    )


def test_agents_report_manager_tool_route() -> None:
    assert API.AGENTS_REPORT_MANAGER_TOOL_ROUTE.startswith(
        API.PREFIX,
    )
    assert API.AGENTS_REPORT_MANAGER_TOOL_ROUTE == (
        "/api/agents/report-manager/tool"
    )


def test_agents_report_manager_prompt_route() -> None:
    assert API.AGENTS_REPORT_MANAGER_PROMPT_ROUTE.startswith(
        API.PREFIX,
    )
    assert API.AGENTS_REPORT_MANAGER_PROMPT_ROUTE == (
        "/api/agents/report-manager/prompt"
    )


def test_agents_report_review_step_route() -> None:
    assert API.AGENTS_REPORT_REVIEW_STEP_ROUTE.startswith(
        API.PREFIX,
    )
    assert API.AGENTS_REPORT_REVIEW_STEP_ROUTE == (
        "/api/agents/report-review/step"
    )


def test_agents_report_review_tool_route() -> None:
    assert API.AGENTS_REPORT_REVIEW_TOOL_ROUTE.startswith(
        API.PREFIX,
    )
    assert API.AGENTS_REPORT_REVIEW_TOOL_ROUTE == (
        "/api/agents/report-review/tool"
    )


def test_agents_report_review_prompt_route() -> None:
    assert API.AGENTS_REPORT_REVIEW_PROMPT_ROUTE.startswith(
        API.PREFIX,
    )
    assert API.AGENTS_REPORT_REVIEW_PROMPT_ROUTE == (
        "/api/agents/report-review/prompt"
    )


def test_agents_orchestrator_step_route() -> None:
    assert API.AGENTS_ORCHESTRATOR_STEP_ROUTE.startswith(
        API.PREFIX,
    )
    assert API.AGENTS_ORCHESTRATOR_STEP_ROUTE == (
        "/api/agents/orchestrator/step"
    )


def test_agents_orchestrator_tool_route() -> None:
    assert API.AGENTS_ORCHESTRATOR_TOOL_ROUTE.startswith(
        API.PREFIX,
    )
    assert API.AGENTS_ORCHESTRATOR_TOOL_ROUTE == (
        "/api/agents/orchestrator/tool"
    )


def test_agents_orchestrator_prompt_route() -> None:
    assert API.AGENTS_ORCHESTRATOR_PROMPT_ROUTE.startswith(
        API.PREFIX,
    )
    assert API.AGENTS_ORCHESTRATOR_PROMPT_ROUTE == (
        "/api/agents/orchestrator/prompt"
    )


def test_incident_2_subnets_do_not_overlap_incident_1() -> None:
    """
    Incident 2 subnets must not overlap with incident 1 subnets
    so both digital twins can be deployed in parallel.
    """
    i1_subnets = {
        n["subnet"]
        for n in DIGITAL_TWIN.DEFAULT_CONFIG["networks"]
    }
    i2_subnets = {
        n["subnet"]
        for n in DIGITAL_TWIN.INCIDENT_2_CONFIG["networks"]
    }
    overlap = i1_subnets & i2_subnets
    assert overlap == set(), (
        f"Overlapping subnets: {overlap}"
    )
