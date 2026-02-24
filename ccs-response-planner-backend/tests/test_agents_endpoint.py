"""Tests for the /api/agents endpoints."""
import json
import time
from typing import Any
from unittest.mock import MagicMock, patch

from flask.testing import FlaskClient

from ccs_response_planner_backend.agents.dt_prompt_utils import (
    format_container_list,
    format_container_table,
    format_network_connectivity,
)
from ccs_response_planner_backend.agents.report_agent.prompt import (
    SYSTEM_PROMPT_TEMPLATE,
)
from ccs_response_planner_backend.constants.constants import DIGITAL_TWIN


def _parse_ndjson(data: bytes) -> list[dict[str, Any]]:
    """
    Parse newline-delimited JSON bytes into a list of dicts.

    :param data: raw NDJSON response bytes
    :return: a list of parsed event dicts
    """
    lines = data.decode("utf-8").strip().split("\n")
    return [json.loads(line) for line in lines if line.strip()]


def _get_job_events(
    client: FlaskClient,
    resp,
    auth_headers: dict[str, str],
    max_wait: float = 2.0,
) -> list[dict[str, Any]]:
    """
    Poll a background job until done, then return its events.

    :param client: Flask test client
    :param resp: response from the POST that started the job
    :param auth_headers: authorization headers
    :param max_wait: maximum seconds to wait
    :return: list of event dicts from the job
    """
    assert resp.status_code == 202
    data = resp.get_json()
    job_id = data["job_id"]
    deadline = time.monotonic() + max_wait
    while time.monotonic() < deadline:
        events_resp = client.get(
            f"/api/agents/jobs/{job_id}/events?after=0",
            headers=auth_headers,
        )
        assert events_resp.status_code == 200
        events_data = events_resp.get_json()
        if events_data["done"]:
            return events_data["events"]
        time.sleep(0.05)
    raise TimeoutError(
        f"Job {job_id} did not complete in {max_wait}s",
    )


def test_step_returns_401_without_token(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/report/step without a token returns 401.
    """
    resp = client.post(
        "/api/agents/report/step",
        data=json.dumps({"system_description": "test"}),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_step_returns_400_missing_fields(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report/step with no fields returns 400.
    """
    resp = client.post(
        "/api/agents/report/step",
        data=json.dumps({}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._start_sandbox",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._redeploy_dt",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.ReportAgent",
)
def test_step_streams_tool_proposal(
    mock_agent_cls: MagicMock,
    _mock_redeploy: MagicMock,
    _mock_sandbox: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report/step streams text then tool_proposal.
    """
    mock_agent = MagicMock()
    mock_agent.step_stream.return_value = iter([
        {"type": "text", "delta": "I will search"},
        {
            "type": "tool_proposal",
            "tool_name": "tavily_search",
            "tool_args": {"query": "test"},
            "rationale": "I will search",
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/report/step",
        data=json.dumps({
            "system_description": "test system",
            "security_alerts": "test alerts",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert len(events) == 2
    assert events[0]["type"] == "text"
    assert events[0]["delta"] == "I will search"
    assert events[1]["type"] == "tool_proposal"
    assert events[1]["tool_name"] == "tavily_search"


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._start_sandbox",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._redeploy_dt",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.ReportAgent",
)
def test_step_streams_assessment(
    mock_agent_cls: MagicMock,
    _mock_redeploy: MagicMock,
    _mock_sandbox: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report/step streams text then assessment.
    """
    mock_assessment = {
        "incident_summary": "Based on analysis",
        "attack_vector_analysis": "SQL injection",
        "indicators_of_compromise": [],
        "severity": "High",
        "severity_justification": "Database compromised",
        "affected_assets": [],
    }
    mock_agent = MagicMock()
    mock_agent.step_stream.return_value = iter([
        {"type": "text", "delta": "Based on analysis"},
        {
            "type": "assessment",
            "assessment": mock_assessment,
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/report/step",
        data=json.dumps({
            "system_description": "test system",
            "security_alerts": "test alerts",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert len(events) == 2
    assert events[0]["type"] == "text"
    assert events[1]["type"] == "assessment"
    assert events[1]["assessment"]["severity"] == "High"
    assert events[1]["assessment"]["incident_summary"] == (
        "Based on analysis"
    )


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._start_sandbox",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._redeploy_dt",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.ReportAgent",
)
def test_step_streams_error_on_failure(
    mock_agent_cls: MagicMock,
    _mock_redeploy: MagicMock,
    _mock_sandbox: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report/step streams an error event on failure.
    """
    mock_agent = MagicMock()
    mock_agent.step_stream.side_effect = RuntimeError(
        "agent failed",
    )
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/report/step",
        data=json.dumps({
            "system_description": "test",
            "security_alerts": "alerts",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert "agent failed" in events[0]["message"]


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._start_sandbox",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._redeploy_dt",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.ReportAgent",
)
def test_step_uses_session_id_as_job_id(
    mock_agent_cls: MagicMock,
    _mock_redeploy: MagicMock,
    _mock_sandbox: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report/step with session_id uses it as job_id.
    """
    mock_agent = MagicMock()
    mock_agent.step_stream.return_value = iter([
        {"type": "text", "delta": "hello"},
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/report/step",
        data=json.dumps({
            "system_description": "test",
            "security_alerts": "alerts",
            "session_id": 99,
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 202
    data = resp.get_json()
    assert data["job_id"] == "99"


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.ReportAgent",
)
def test_tool_uses_session_id_as_job_id(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report/tool with session_id uses it
    as job_id for streaming tools.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool_stream.return_value = iter([
        {
            "type": "done",
            "container": "i1_server_1",
            "command": "whoami",
            "exit_code": 0,
            "output": "root",
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/report/tool",
        data=json.dumps({
            "tool_name": "dt_exec",
            "tool_args": {
                "container": "i1_server_1",
                "command": "whoami",
            },
            "session_id": 77,
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 202
    data = resp.get_json()
    assert data["job_id"] == "77"


def test_tool_returns_401_without_token(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/report/tool without a token returns 401.
    """
    resp = client.post(
        "/api/agents/report/tool",
        data=json.dumps({
            "tool_name": "tavily_search",
            "tool_args": {},
        }),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_tool_returns_400_missing_fields(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report/tool with no tool_name returns 400.
    """
    resp = client.post(
        "/api/agents/report/tool",
        data=json.dumps({}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


def test_tool_returns_400_unknown_tool(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report/tool with unknown tool returns 400.
    """
    resp = client.post(
        "/api/agents/report/tool",
        data=json.dumps({
            "tool_name": "nonexistent_tool",
            "tool_args": {},
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Unknown tool" in data["error"]


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.ReportAgent",
)
def test_tool_executes_and_returns_result(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report/tool executes and returns result.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool.return_value = {
        "tool_name": "tavily_search",
        "result": {"query": "test", "results": []},
    }
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/report/tool",
        data=json.dumps({
            "tool_name": "tavily_search",
            "tool_args": {"query": "test"},
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["tool_name"] == "tavily_search"
    assert "result" in data


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.ReportAgent",
)
def test_tool_returns_500_on_error(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report/tool returns 500 on tool error.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool.side_effect = RuntimeError("boom")
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/report/tool",
        data=json.dumps({
            "tool_name": "tavily_search",
            "tool_args": {"query": "test"},
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 500
    data = resp.get_json()
    assert "error" in data


def test_prompt_returns_401_without_token(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/report/prompt without a token returns 401.
    """
    resp = client.post(
        "/api/agents/report/prompt",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_prompt_returns_rendered_prompt(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report/prompt renders the system prompt.
    """
    resp = client.post(
        "/api/agents/report/prompt",
        data=json.dumps({
            "system_description": "My system",
            "security_alerts": "My alerts",
            "operator_feedback": "My feedback",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "prompt" in data
    assert "My system" in data["prompt"]
    assert "My alerts" in data["prompt"]
    assert "My feedback" in data["prompt"]


def test_prompt_uses_na_for_empty_fields(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report/prompt uses N/A for empty fields.
    """
    resp = client.post(
        "/api/agents/report/prompt",
        data=json.dumps({}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    dt_config = DIGITAL_TWIN.DEFAULT_CONFIG
    expected = SYSTEM_PROMPT_TEMPLATE.format(
        system_description="N/A",
        security_alerts="N/A",
        operator_feedback="N/A",
        dt_container_list=format_container_list(dt_config),
        dt_container_table=format_container_table(dt_config),
        dt_network_connectivity=format_network_connectivity(
            dt_config,
        ),
        revision_notice="",
    )
    assert data["prompt"] == expected


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.ReportAgent",
)
def test_tool_injects_incident_id_for_dt_exec(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report/tool with dt_exec injects incident_id.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool_stream.return_value = iter([
        {"type": "done", "container": "i1_server_1",
         "command": "whoami", "exit_code": 0,
         "output": "root"},
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/report/tool",
        data=json.dumps({
            "tool_name": "dt_exec",
            "tool_args": {
                "container": "i1_server_1",
                "command": "whoami",
            },
            "incident_id": 7,
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    _get_job_events(client, resp, auth_headers)
    call_args = mock_agent.execute_tool_stream.call_args
    assert call_args[0][1]["incident_id"] == 7


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.ReportAgent",
)
def test_tool_no_incident_id_for_non_dt_tool(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report/tool with non-DT tool omits incident_id.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool.return_value = {
        "tool_name": "tavily_search",
        "result": {"query": "test", "results": []},
    }
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/report/tool",
        data=json.dumps({
            "tool_name": "tavily_search",
            "tool_args": {"query": "test"},
            "incident_id": 7,
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    call_args = mock_agent.execute_tool.call_args
    assert "incident_id" not in call_args[0][1]


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.ReportAgent",
)
def test_tool_injects_incident_id_for_generate_attack_image(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report/tool with generate_attack_image
    injects incident_id into tool_args.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool.return_value = {
        "image": "data:image/png;base64,abc",
        "prompt": "test attack path",
    }
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/report/tool",
        data=json.dumps({
            "tool_name": "generate_attack_image",
            "tool_args": {"prompt": "test attack path"},
            "incident_id": 5,
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    call_args = mock_agent.execute_tool.call_args
    assert call_args[0][1]["incident_id"] == 5


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.ReportAgent",
)
def test_info_tool_dt_exec_streams_ndjson(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report/tool with dt_exec streams NDJSON.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool_stream.return_value = iter([
        {"type": "output_chunk", "text": "root\n"},
        {
            "type": "done",
            "container": "i1_server_1",
            "command": "whoami",
            "exit_code": 0,
            "output": "root\n",
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/report/tool",
        data=json.dumps({
            "tool_name": "dt_exec",
            "tool_args": {
                "container": "i1_server_1",
                "command": "whoami",
            },
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert any(e["type"] == "output_chunk" for e in events)
    assert events[-1]["type"] == "done"
    assert events[-1]["exit_code"] == 0


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.ValidationAgent",
)
def test_validation_tool_dt_exec_streams_ndjson(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/validation/tool with dt_exec streams NDJSON.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool_stream.return_value = iter([
        {
            "type": "done",
            "container": "i1_firewall",
            "command": "iptables -L",
            "exit_code": 0,
            "output": "Chain INPUT\n",
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/validation/tool",
        data=json.dumps({
            "tool_name": "dt_exec",
            "tool_args": {
                "container": "i1_firewall",
                "command": "iptables -L",
            },
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert events[-1]["type"] == "done"


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.CodeAgent",
)
def test_code_tool_dt_exec_streams_ndjson(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/code/tool with dt_exec streams NDJSON.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool_stream.return_value = iter([
        {
            "type": "done",
            "container": "i1_server_1",
            "command": "ls",
            "exit_code": 0,
            "output": "file.txt\n",
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/code/tool",
        data=json.dumps({
            "tool_name": "dt_exec",
            "tool_args": {
                "container": "i1_server_1",
                "command": "ls",
            },
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert events[-1]["type"] == "done"


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.CodeReviewerAgent",
)
def test_code_review_tool_dt_exec_streams_ndjson(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/code-review/tool with dt_exec streams NDJSON.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool_stream.return_value = iter([
        {
            "type": "done",
            "container": "i1_server_2",
            "command": "cat /etc/passwd",
            "exit_code": 0,
            "output": "root:x:0:0\n",
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/code-review/tool",
        data=json.dumps({
            "tool_name": "dt_exec",
            "tool_args": {
                "container": "i1_server_2",
                "command": "cat /etc/passwd",
            },
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert events[-1]["type"] == "done"


def test_code_manager_step_returns_401_without_token(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/code-manager/step without token returns 401.
    """
    resp = client.post(
        "/api/agents/code-manager/step",
        data=json.dumps({
            "system_description": "test",
        }),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_code_manager_step_returns_400_missing_fields(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/code-manager/step with no fields -> 400.
    """
    resp = client.post(
        "/api/agents/code-manager/step",
        data=json.dumps({}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._start_sandbox",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._redeploy_dt",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.CodeManagerAgent",
)
def test_code_manager_step_streams_tool_proposal(
    mock_agent_cls: MagicMock,
    _mock_redeploy: MagicMock,
    _mock_sandbox: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/code-manager/step streams tool_proposal.
    """
    mock_agent = MagicMock()
    mock_agent.step_stream.return_value = iter([
        {"type": "text", "delta": "Starting orchestration"},
        {
            "type": "tool_proposal",
            "tool_name": "run_code_agent",
            "tool_args": {},
            "rationale": "Starting orchestration",
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/code-manager/step",
        data=json.dumps({
            "system_description": "test system",
            "incident_report": "test report",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert len(events) == 2
    assert events[0]["type"] == "text"
    assert events[1]["type"] == "tool_proposal"
    assert events[1]["tool_name"] == "run_code_agent"


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._start_sandbox",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._redeploy_dt",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.CodeManagerAgent",
)
def test_code_manager_step_streams_orchestrator_report(
    mock_agent_cls: MagicMock,
    _mock_redeploy: MagicMock,
    _mock_sandbox: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/code-manager/step streams report.
    """
    mock_report = {
        "executive_summary": "Completed in 1 iteration",
        "iterations": 1,
        "final_verdict": "pass",
        "code_report_summary": "MDP generated",
        "review_report_summary": "All checks passed",
    }
    mock_agent = MagicMock()
    mock_agent.step_stream.return_value = iter([
        {
            "type": "orchestrator_report",
            "orchestrator_report": mock_report,
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/code-manager/step",
        data=json.dumps({
            "system_description": "test",
            "incident_report": "test",
            "conversation_history": [
                {"type": "tool_result"},
            ],
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert events[-1]["type"] == "orchestrator_report"
    assert events[-1]["orchestrator_report"][
        "final_verdict"
    ] == "pass"


def test_code_manager_tool_returns_401_without_token(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/code-manager/tool without token -> 401.
    """
    resp = client.post(
        "/api/agents/code-manager/tool",
        data=json.dumps({
            "tool_name": "run_code_agent",
            "tool_args": {},
        }),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_code_manager_tool_returns_400_missing_tool_name(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/code-manager/tool with no tool_name -> 400.
    """
    resp = client.post(
        "/api/agents/code-manager/tool",
        data=json.dumps({}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.CodeManagerAgent",
)
def test_code_manager_tool_streams_run_code_agent(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/code-manager/tool with run_code_agent
    streams NDJSON.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool_stream.return_value = iter([
        {
            "type": "output_chunk",
            "text": "[CodeAgent] Step 1...\n",
        },
        {
            "type": "done",
            "result": {
                "code_report": {
                    "executive_summary": "Done",
                },
            },
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/code-manager/tool",
        data=json.dumps({
            "tool_name": "run_code_agent",
            "tool_args": {},
            "system_description": "test",
            "incident_report": "test",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert any(
        e["type"] == "output_chunk" for e in events
    )
    assert events[-1]["type"] == "done"


def test_code_manager_prompt_returns_401_without_token(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/code-manager/prompt without token -> 401.
    """
    resp = client.post(
        "/api/agents/code-manager/prompt",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_code_manager_prompt_renders_prompt(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/code-manager/prompt renders the prompt.
    """
    resp = client.post(
        "/api/agents/code-manager/prompt",
        data=json.dumps({
            "system_description": "My system",
            "incident_report": "My incident",
            "operator_feedback": "My feedback",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "prompt" in data
    assert "My system" in data["prompt"]
    assert "My incident" in data["prompt"]
    assert "My feedback" in data["prompt"]


# ── PlanManagerAgent endpoint tests ──


def test_plan_manager_step_returns_401_without_token(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/plan-manager/step without token returns 401.
    """
    resp = client.post(
        "/api/agents/plan-manager/step",
        data=json.dumps({
            "system_description": "test",
        }),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_plan_manager_step_returns_400_missing_fields(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/plan-manager/step with no fields -> 400.
    """
    resp = client.post(
        "/api/agents/plan-manager/step",
        data=json.dumps({}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._start_sandbox",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._redeploy_dt",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.PlanManagerAgent",
)
def test_plan_manager_step_streams_tool_proposal(
    mock_agent_cls: MagicMock,
    _mock_redeploy: MagicMock,
    _mock_sandbox: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/plan-manager/step streams tool_proposal.
    """
    mock_agent = MagicMock()
    mock_agent.step_stream.return_value = iter([
        {"type": "text", "delta": "Starting pipeline"},
        {
            "type": "tool_proposal",
            "tool_name": "run_code_manager",
            "tool_args": {},
            "rationale": "Starting code manager",
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/plan-manager/step",
        data=json.dumps({
            "system_description": "test system",
            "incident_report": "test report",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert len(events) == 2
    assert events[0]["type"] == "text"
    assert events[1]["type"] == "tool_proposal"
    assert events[1]["tool_name"] == "run_code_manager"


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._start_sandbox",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._redeploy_dt",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.PlanManagerAgent",
)
def test_plan_manager_step_streams_report(
    mock_agent_cls: MagicMock,
    _mock_redeploy: MagicMock,
    _mock_sandbox: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/plan-manager/step streams report.
    """
    mock_report = {
        "executive_summary": "Pipeline completed",
        "iterations": 1,
        "final_verdict": "pass",
        "code_manager_summary": "Code OK",
        "planner_agent_summary": "RL OK",
        "validation_summary": "Validation OK",
    }
    mock_agent = MagicMock()
    mock_agent.step_stream.return_value = iter([
        {
            "type": "plan_manager_report",
            "plan_manager_report": mock_report,
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/plan-manager/step",
        data=json.dumps({
            "system_description": "test",
            "incident_report": "test",
            "conversation_history": [
                {"type": "tool_result"},
            ],
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert events[-1]["type"] == "plan_manager_report"
    assert events[-1]["plan_manager_report"][
        "final_verdict"
    ] == "pass"


def test_plan_manager_tool_returns_401_without_token(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/plan-manager/tool without token -> 401.
    """
    resp = client.post(
        "/api/agents/plan-manager/tool",
        data=json.dumps({
            "tool_name": "run_code_manager",
            "tool_args": {},
        }),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_plan_manager_tool_returns_400_missing_tool_name(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/plan-manager/tool with no tool_name -> 400.
    """
    resp = client.post(
        "/api/agents/plan-manager/tool",
        data=json.dumps({}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.PlanManagerAgent",
)
def test_plan_manager_tool_streams_run_code_manager(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/plan-manager/tool with run_code_manager
    streams NDJSON.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool_stream.return_value = iter([
        {
            "type": "output_chunk",
            "text": "[CodeManager] Step 1...\n",
        },
        {
            "type": "done",
            "result": {
                "code_report": {
                    "executive_summary": "Done",
                },
                "orchestrator_report": {
                    "executive_summary": "Done",
                },
            },
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/plan-manager/tool",
        data=json.dumps({
            "tool_name": "run_code_manager",
            "tool_args": {},
            "system_description": "test",
            "incident_report": "test",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert any(
        e["type"] == "output_chunk" for e in events
    )
    assert events[-1]["type"] == "done"


def test_plan_manager_prompt_returns_401_without_token(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/plan-manager/prompt without token -> 401.
    """
    resp = client.post(
        "/api/agents/plan-manager/prompt",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_plan_manager_prompt_renders_prompt(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/plan-manager/prompt renders the prompt.
    """
    resp = client.post(
        "/api/agents/plan-manager/prompt",
        data=json.dumps({
            "system_description": "My system",
            "incident_report": "My incident",
            "operator_feedback": "My feedback",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "prompt" in data
    assert "My system" in data["prompt"]
    assert "My incident" in data["prompt"]
    assert "My feedback" in data["prompt"]


# ── ReportManagerAgent endpoint tests ──


def test_report_manager_step_returns_401_without_token(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/report-manager/step without token -> 401.
    """
    resp = client.post(
        "/api/agents/report-manager/step",
        data=json.dumps({
            "system_description": "test",
        }),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_report_manager_step_returns_400_missing_fields(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report-manager/step with no fields -> 400.
    """
    resp = client.post(
        "/api/agents/report-manager/step",
        data=json.dumps({}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._start_sandbox",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._redeploy_dt",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.ReportManagerAgent",
)
def test_report_manager_step_streams_tool_proposal(
    mock_agent_cls: MagicMock,
    _mock_redeploy: MagicMock,
    _mock_sandbox: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report-manager/step streams tool_proposal.
    """
    mock_agent = MagicMock()
    mock_agent.step_stream.return_value = iter([
        {"type": "text", "delta": "Starting orchestration"},
        {
            "type": "tool_proposal",
            "tool_name": "run_report_agent",
            "tool_args": {},
            "rationale": "Starting orchestration",
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/report-manager/step",
        data=json.dumps({
            "system_description": "test system",
            "security_alerts": "test alerts",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert len(events) == 2
    assert events[0]["type"] == "text"
    assert events[1]["type"] == "tool_proposal"
    assert events[1]["tool_name"] == "run_report_agent"


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._start_sandbox",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._redeploy_dt",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.ReportManagerAgent",
)
def test_report_manager_step_streams_report(
    mock_agent_cls: MagicMock,
    _mock_redeploy: MagicMock,
    _mock_sandbox: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report-manager/step streams report.
    """
    mock_report = {
        "executive_summary": "Completed in 1 iteration",
        "iterations": 1,
        "final_verdict": "pass",
        "report_summary": "Assessment OK",
        "review_summary": "All checks passed",
    }
    mock_agent = MagicMock()
    mock_agent.step_stream.return_value = iter([
        {
            "type": "report_manager_report",
            "report_manager_report": mock_report,
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/report-manager/step",
        data=json.dumps({
            "system_description": "test",
            "security_alerts": "test",
            "conversation_history": [
                {"type": "tool_result"},
            ],
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert events[-1]["type"] == "report_manager_report"
    assert events[-1]["report_manager_report"][
        "final_verdict"
    ] == "pass"


def test_report_manager_tool_returns_401_without_token(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/report-manager/tool without token -> 401.
    """
    resp = client.post(
        "/api/agents/report-manager/tool",
        data=json.dumps({
            "tool_name": "run_report_agent",
            "tool_args": {},
        }),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_report_manager_tool_returns_400_missing_tool_name(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report-manager/tool no tool_name -> 400.
    """
    resp = client.post(
        "/api/agents/report-manager/tool",
        data=json.dumps({}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.ReportManagerAgent",
)
def test_report_manager_tool_streams_run_report_agent(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report-manager/tool with run_report_agent
    streams NDJSON.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool_stream.return_value = iter([
        {
            "type": "output_chunk",
            "text": "[ReportAgent] Step 1...\n",
        },
        {
            "type": "done",
            "result": {
                "assessment": {
                    "incident_summary": "Done",
                },
            },
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/report-manager/tool",
        data=json.dumps({
            "tool_name": "run_report_agent",
            "tool_args": {},
            "system_description": "test",
            "security_alerts": "test",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert any(
        e["type"] == "output_chunk" for e in events
    )
    assert events[-1]["type"] == "done"


def test_report_manager_prompt_returns_401_without_token(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/report-manager/prompt without token -> 401.
    """
    resp = client.post(
        "/api/agents/report-manager/prompt",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_report_manager_prompt_renders_prompt(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report-manager/prompt renders the prompt.
    """
    resp = client.post(
        "/api/agents/report-manager/prompt",
        data=json.dumps({
            "system_description": "My system",
            "security_alerts": "My alerts",
            "operator_feedback": "My feedback",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "prompt" in data
    assert "My system" in data["prompt"]
    assert "My alerts" in data["prompt"]
    assert "My feedback" in data["prompt"]


# ── ReportReviewerAgent endpoint tests ──


def test_report_review_step_returns_401_without_token(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/report-review/step without token -> 401.
    """
    resp = client.post(
        "/api/agents/report-review/step",
        data=json.dumps({
            "incident_report": {"incident_summary": "test"},
        }),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_report_review_step_returns_400_missing_report(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report-review/step without
    incident_report returns 400.
    """
    resp = client.post(
        "/api/agents/report-review/step",
        data=json.dumps({}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._start_sandbox",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._redeploy_dt",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.ReportReviewerAgent",
)
def test_report_review_step_streams_tool_proposal(
    mock_agent_cls: MagicMock,
    _mock_redeploy: MagicMock,
    _mock_sandbox: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report-review/step streams text then
    tool_proposal.
    """
    mock_agent = MagicMock()
    mock_agent.step_stream.return_value = iter([
        {"type": "text", "delta": "I will verify"},
        {
            "type": "tool_proposal",
            "tool_name": "tavily_search",
            "tool_args": {"query": "test"},
            "rationale": "I will verify",
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/report-review/step",
        data=json.dumps({
            "incident_report": {
                "incident_summary": "test",
            },
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert len(events) == 2
    assert events[0]["type"] == "text"
    assert events[1]["type"] == "tool_proposal"
    assert events[1]["tool_name"] == "tavily_search"


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._start_sandbox",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._redeploy_dt",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.ReportReviewerAgent",
)
def test_report_review_step_streams_report_review(
    mock_agent_cls: MagicMock,
    _mock_redeploy: MagicMock,
    _mock_sandbox: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report-review/step streams report_review.
    """
    mock_review = {
        "executive_summary": "Report needs revision",
        "findings": [],
        "missing_elements": [],
        "evidence_gaps": [],
        "strengths": ["Good severity analysis"],
        "overall_verdict": "needs_revision",
    }
    mock_agent = MagicMock()
    mock_agent.step_stream.return_value = iter([
        {
            "type": "report_review",
            "report_review": mock_review,
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/report-review/step",
        data=json.dumps({
            "incident_report": {
                "incident_summary": "test",
            },
            "conversation_history": [
                {"type": "tool_result"},
            ],
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert events[-1]["type"] == "report_review"
    assert events[-1]["report_review"][
        "overall_verdict"
    ] == "needs_revision"


def test_report_review_tool_returns_401_without_token(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/report-review/tool without token -> 401.
    """
    resp = client.post(
        "/api/agents/report-review/tool",
        data=json.dumps({
            "tool_name": "tavily_search",
            "tool_args": {},
        }),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_report_review_tool_returns_400_missing_tool_name(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report-review/tool with no tool_name -> 400.
    """
    resp = client.post(
        "/api/agents/report-review/tool",
        data=json.dumps({}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.ReportReviewerAgent",
)
def test_report_review_tool_dt_exec_streams_ndjson(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report-review/tool with dt_exec streams
    NDJSON.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool_stream.return_value = iter([
        {
            "type": "done",
            "container": "i1_server_1",
            "command": "whoami",
            "exit_code": 0,
            "output": "root\n",
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/report-review/tool",
        data=json.dumps({
            "tool_name": "dt_exec",
            "tool_args": {
                "container": "i1_server_1",
                "command": "whoami",
            },
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert events[-1]["type"] == "done"


def test_report_review_prompt_returns_401_without_token(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/report-review/prompt without token -> 401.
    """
    resp = client.post(
        "/api/agents/report-review/prompt",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_report_review_prompt_renders_prompt(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/report-review/prompt renders the prompt.
    """
    resp = client.post(
        "/api/agents/report-review/prompt",
        data=json.dumps({
            "system_description": "My system",
            "security_alerts": "My alerts",
            "operator_feedback": "My feedback",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "prompt" in data
    assert "My system" in data["prompt"]
    assert "My alerts" in data["prompt"]
    assert "My feedback" in data["prompt"]


# ═══════════════════════════════════════════════════════════════
# Orchestrator Agent endpoints
# ═══════════════════════════════════════════════════════════════


def test_orchestrator_step_returns_401_without_token(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/orchestrator/step without token -> 401.
    """
    resp = client.post(
        "/api/agents/orchestrator/step",
        data=json.dumps({
            "system_description": "test",
        }),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_orchestrator_step_returns_400_missing_fields(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/orchestrator/step with no fields -> 400.
    """
    resp = client.post(
        "/api/agents/orchestrator/step",
        data=json.dumps({}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._start_sandbox",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._redeploy_dt",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.OrchestratorAgent",
)
def test_orchestrator_step_streams_report(
    mock_agent_cls: MagicMock,
    _mock_redeploy: MagicMock,
    _mock_sandbox: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/orchestrator/step streams report.
    """
    mock_report = {
        "executive_summary": "Completed in 1 iteration",
        "iterations": 1,
        "final_verdict": "pass",
        "assessment_summary": "Assessment OK",
        "response_plan_summary": "Plan OK",
    }
    mock_agent = MagicMock()
    mock_agent.step_stream.return_value = iter([
        {
            "type": "orchestrator_agent_report",
            "orchestrator_agent_report": mock_report,
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/orchestrator/step",
        data=json.dumps({
            "system_description": "test",
            "security_alerts": "test",
            "conversation_history": [
                {"type": "tool_result"},
            ],
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert events[-1]["type"] == "orchestrator_agent_report"
    assert events[-1]["orchestrator_agent_report"][
        "final_verdict"
    ] == "pass"


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.OrchestratorAgent",
)
def test_orchestrator_tool_streams_run_report_manager(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/orchestrator/tool with run_report_manager
    streams NDJSON.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool_stream.return_value = iter([
        {
            "type": "output_chunk",
            "text": "[ReportManager] Step 1...\n",
        },
        {
            "type": "done",
            "result": {
                "report_manager_report": {
                    "executive_summary": "Done",
                },
                "assessment": {
                    "incident_summary": "Test",
                },
            },
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/orchestrator/tool",
        data=json.dumps({
            "tool_name": "run_report_manager",
            "tool_args": {},
            "system_description": "test",
            "security_alerts": "test",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert any(
        e["type"] == "output_chunk" for e in events
    )
    assert events[-1]["type"] == "done"


def test_orchestrator_tool_returns_401_without_token(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/orchestrator/tool without token -> 401.
    """
    resp = client.post(
        "/api/agents/orchestrator/tool",
        data=json.dumps({
            "tool_name": "run_report_manager",
            "tool_args": {},
        }),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_orchestrator_prompt_returns_401_without_token(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/orchestrator/prompt without token -> 401.
    """
    resp = client.post(
        "/api/agents/orchestrator/prompt",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_orchestrator_prompt_renders_prompt(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/orchestrator/prompt renders the prompt.
    """
    resp = client.post(
        "/api/agents/orchestrator/prompt",
        data=json.dumps({
            "system_description": "My system",
            "security_alerts": "My alerts",
            "operator_feedback": "My feedback",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "prompt" in data
    assert "My system" in data["prompt"]
    assert "My alerts" in data["prompt"]
    assert "My feedback" in data["prompt"]


# ── Pentest Agent ─────────────────────────────────────────────


def test_pentest_step_requires_auth(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/pentest/step requires auth.
    """
    resp = client.post(
        "/api/agents/pentest/step",
        data=json.dumps({
            "system_description": "Test system",
            "attack_path": "Test path",
        }),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_pentest_step_requires_inputs(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/pentest/step returns 400 without inputs.
    """
    resp = client.post(
        "/api/agents/pentest/step",
        data=json.dumps({}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 400


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.PentestAgent",
)
def test_pentest_tool_dt_exec_streams_ndjson(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/pentest/tool with dt_exec streams NDJSON.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool_stream.return_value = iter([
        {
            "type": "done",
            "container": "i1_firewall",
            "command": "iptables -L",
            "exit_code": 0,
            "output": "Chain INPUT\n",
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/pentest/tool",
        data=json.dumps({
            "tool_name": "dt_exec",
            "tool_args": {
                "container": "i1_firewall",
                "command": "iptables -L",
            },
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert events[-1]["type"] == "done"


def test_pentest_tool_requires_auth(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/pentest/tool requires auth.
    """
    resp = client.post(
        "/api/agents/pentest/tool",
        data=json.dumps({
            "tool_name": "dt_exec",
            "tool_args": {
                "container": "x", "command": "y",
            },
        }),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_pentest_prompt_requires_auth(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/pentest/prompt requires auth.
    """
    resp = client.post(
        "/api/agents/pentest/prompt",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_pentest_prompt_renders_prompt(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/pentest/prompt renders the prompt.
    """
    resp = client.post(
        "/api/agents/pentest/prompt",
        data=json.dumps({
            "system_description": "My pentest system",
            "attack_path": (
                "SSH brute force to server_3"
            ),
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "prompt" in data
    assert "My pentest system" in data["prompt"]
    assert (
        "SSH brute force to server_3"
        in data["prompt"]
    )


# ── Host Analyzer Agent ──────────────────────────────────────


def test_host_analyzer_step_requires_auth(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/host-analyzer/step requires auth.
    """
    resp = client.post(
        "/api/agents/host-analyzer/step",
        data=json.dumps({
            "system_description": "Test system",
            "host_description": "Test host",
        }),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_host_analyzer_step_requires_inputs(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/host-analyzer/step returns 400
    without inputs.
    """
    resp = client.post(
        "/api/agents/host-analyzer/step",
        data=json.dumps({}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 400


@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".agents.routes.HostAnalyzerAgent",
)
def test_host_analyzer_tool_dt_exec_streams_ndjson(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/host-analyzer/tool with dt_exec
    streams NDJSON.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool_stream.return_value = iter([
        {
            "type": "done",
            "container": "i1_server_3",
            "command": "cat /var/log/auth.log",
            "exit_code": 0,
            "output": "auth log data\n",
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/host-analyzer/tool",
        data=json.dumps({
            "tool_name": "dt_exec",
            "tool_args": {
                "container": "i1_server_3",
                "command": "cat /var/log/auth.log",
            },
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert events[-1]["type"] == "done"


def test_host_analyzer_tool_requires_auth(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/host-analyzer/tool requires auth.
    """
    resp = client.post(
        "/api/agents/host-analyzer/tool",
        data=json.dumps({
            "tool_name": "dt_exec",
            "tool_args": {
                "container": "x", "command": "y",
            },
        }),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_host_analyzer_prompt_requires_auth(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/host-analyzer/prompt requires auth.
    """
    resp = client.post(
        "/api/agents/host-analyzer/prompt",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_host_analyzer_prompt_renders_prompt(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/host-analyzer/prompt renders the
    prompt.
    """
    resp = client.post(
        "/api/agents/host-analyzer/prompt",
        data=json.dumps({
            "system_description": "My HA system",
            "host_description": "Server 3 SSH host",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "prompt" in data
    assert "My HA system" in data["prompt"]
    assert "Server 3 SSH host" in data["prompt"]


# ── Action Validator Agent ───────────────────────────────────


def test_action_validator_step_requires_auth(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/action-validator/step requires auth.
    """
    resp = client.post(
        "/api/agents/action-validator/step",
        data=json.dumps({
            "system_description": "Test system",
            "action_to_validate": "Block attacker IP",
        }),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_action_validator_step_requires_inputs(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/action-validator/step returns 400
    without inputs.
    """
    resp = client.post(
        "/api/agents/action-validator/step",
        data=json.dumps({}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 400


@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".agents.routes.ActionValidatorAgent",
)
def test_action_validator_tool_dt_exec_streams_ndjson(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/action-validator/tool with dt_exec
    streams NDJSON.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool_stream.return_value = iter([
        {
            "type": "done",
            "container": "i1_firewall",
            "command": "iptables -L",
            "exit_code": 0,
            "output": "Chain INPUT\n",
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/action-validator/tool",
        data=json.dumps({
            "tool_name": "dt_exec",
            "tool_args": {
                "container": "i1_firewall",
                "command": "iptables -L",
            },
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    events = _get_job_events(client, resp, auth_headers)
    assert events[-1]["type"] == "done"


def test_action_validator_tool_requires_auth(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/action-validator/tool requires auth.
    """
    resp = client.post(
        "/api/agents/action-validator/tool",
        data=json.dumps({
            "tool_name": "dt_exec",
            "tool_args": {
                "container": "x", "command": "y",
            },
        }),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_action_validator_prompt_requires_auth(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/action-validator/prompt requires auth.
    """
    resp = client.post(
        "/api/agents/action-validator/prompt",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_action_validator_prompt_renders_prompt(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/action-validator/prompt renders the
    prompt.
    """
    resp = client.post(
        "/api/agents/action-validator/prompt",
        data=json.dumps({
            "system_description": "My AV system",
            "action_to_validate": (
                "Block attacker at firewall"
            ),
            "code_report": "{}",
            "planner_report": "{}",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "prompt" in data
    assert "My AV system" in data["prompt"]
    assert (
        "Block attacker at firewall"
        in data["prompt"]
    )
