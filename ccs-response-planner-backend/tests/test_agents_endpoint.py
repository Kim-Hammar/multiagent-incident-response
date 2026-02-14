"""Tests for the /api/agents endpoints."""
import json
from typing import Any
from unittest.mock import MagicMock, patch

from flask.testing import FlaskClient

from ccs_response_planner_backend.agents.information_agent.prompt import (
    SYSTEM_PROMPT_TEMPLATE,
)


def _parse_ndjson(data: bytes) -> list[dict[str, Any]]:
    """
    Parse newline-delimited JSON bytes into a list of dicts.

    :param data: raw NDJSON response bytes
    :return: a list of parsed event dicts
    """
    lines = data.decode("utf-8").strip().split("\n")
    return [json.loads(line) for line in lines if line.strip()]


def test_step_returns_401_without_token(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/information/step without a token returns 401.
    """
    resp = client.post(
        "/api/agents/information/step",
        data=json.dumps({"system_description": "test"}),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_step_returns_400_missing_fields(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/information/step with no fields returns 400.
    """
    resp = client.post(
        "/api/agents/information/step",
        data=json.dumps({}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._redeploy_dt",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.InformationAgent",
)
def test_step_streams_tool_proposal(
    mock_agent_cls: MagicMock,
    _mock_redeploy: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/information/step streams text then tool_proposal.
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
        "/api/agents/information/step",
        data=json.dumps({
            "system_description": "test system",
            "security_alerts": "test alerts",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.content_type == "application/x-ndjson"
    events = _parse_ndjson(resp.data)
    assert len(events) == 2
    assert events[0]["type"] == "text"
    assert events[0]["delta"] == "I will search"
    assert events[1]["type"] == "tool_proposal"
    assert events[1]["tool_name"] == "tavily_search"


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._redeploy_dt",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.InformationAgent",
)
def test_step_streams_assessment(
    mock_agent_cls: MagicMock,
    _mock_redeploy: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/information/step streams text then assessment.
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
        "/api/agents/information/step",
        data=json.dumps({
            "system_description": "test system",
            "security_alerts": "test alerts",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.content_type == "application/x-ndjson"
    events = _parse_ndjson(resp.data)
    assert len(events) == 2
    assert events[0]["type"] == "text"
    assert events[1]["type"] == "assessment"
    assert events[1]["assessment"]["severity"] == "High"
    assert events[1]["assessment"]["incident_summary"] == (
        "Based on analysis"
    )


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes._redeploy_dt",
    return_value=iter([]),
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.InformationAgent",
)
def test_step_streams_error_on_failure(
    mock_agent_cls: MagicMock,
    _mock_redeploy: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/information/step streams an error event on failure.
    """
    mock_agent = MagicMock()
    mock_agent.step_stream.side_effect = RuntimeError(
        "agent failed",
    )
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/information/step",
        data=json.dumps({
            "system_description": "test",
            "security_alerts": "alerts",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.content_type == "application/x-ndjson"
    events = _parse_ndjson(resp.data)
    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert "agent failed" in events[0]["message"]


def test_tool_returns_401_without_token(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/information/tool without a token returns 401.
    """
    resp = client.post(
        "/api/agents/information/tool",
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
    POST /api/agents/information/tool with no tool_name returns 400.
    """
    resp = client.post(
        "/api/agents/information/tool",
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
    POST /api/agents/information/tool with unknown tool returns 400.
    """
    resp = client.post(
        "/api/agents/information/tool",
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
    ".routes.InformationAgent",
)
def test_tool_executes_and_returns_result(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/information/tool executes and returns result.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool.return_value = {
        "tool_name": "tavily_search",
        "result": {"query": "test", "results": []},
    }
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/information/tool",
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
    ".routes.InformationAgent",
)
def test_tool_returns_500_on_error(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/information/tool returns 500 on tool error.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool.side_effect = RuntimeError("boom")
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/information/tool",
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
    POST /api/agents/information/prompt without a token returns 401.
    """
    resp = client.post(
        "/api/agents/information/prompt",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_prompt_returns_rendered_prompt(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/information/prompt renders the system prompt.
    """
    resp = client.post(
        "/api/agents/information/prompt",
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
    POST /api/agents/information/prompt uses N/A for empty fields.
    """
    resp = client.post(
        "/api/agents/information/prompt",
        data=json.dumps({}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    expected = SYSTEM_PROMPT_TEMPLATE.format(
        system_description="N/A",
        security_alerts="N/A",
        operator_feedback="N/A",
    )
    assert data["prompt"] == expected


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.InformationAgent",
)
def test_tool_injects_incident_id_for_dt_exec(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/information/tool with dt_exec injects incident_id.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool_stream.return_value = iter([
        {"type": "done", "container": "i1_server_1",
         "command": "whoami", "exit_code": 0,
         "output": "root"},
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/information/tool",
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
    assert resp.status_code == 200
    call_args = mock_agent.execute_tool_stream.call_args
    assert call_args[0][1]["incident_id"] == 7


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.InformationAgent",
)
def test_tool_no_incident_id_for_non_dt_tool(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/information/tool with non-DT tool omits incident_id.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool.return_value = {
        "tool_name": "tavily_search",
        "result": {"query": "test", "results": []},
    }
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/information/tool",
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
    ".routes.InformationAgent",
)
def test_tool_injects_incident_id_for_generate_attack_image(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/information/tool with generate_attack_image
    injects incident_id into tool_args.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool.return_value = {
        "image": "data:image/png;base64,abc",
        "prompt": "test attack path",
    }
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/information/tool",
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
    ".routes.PenetrationTestAgent",
)
def test_pentest_tool_injects_incident_id(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/pentest/tool with pentest_exec injects incident_id.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool_stream.return_value = iter([
        {"type": "done", "container": "attacker",
         "command": "nmap -sV 10.0.1.1",
         "exit_code": 0, "output": "scan results"},
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/pentest/tool",
        data=json.dumps({
            "tool_name": "pentest_exec",
            "tool_args": {
                "command": "nmap -sV 10.0.1.1",
            },
            "incident_id": 3,
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    call_args = mock_agent.execute_tool_stream.call_args
    assert call_args[0][1]["incident_id"] == 3


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.InformationAgent",
)
def test_info_tool_dt_exec_streams_ndjson(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/information/tool with dt_exec streams NDJSON.
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
        "/api/agents/information/tool",
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
    assert resp.status_code == 200
    assert resp.content_type == "application/x-ndjson"
    events = _parse_ndjson(resp.data)
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
    assert resp.status_code == 200
    assert resp.content_type == "application/x-ndjson"
    events = _parse_ndjson(resp.data)
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
    assert resp.status_code == 200
    assert resp.content_type == "application/x-ndjson"
    events = _parse_ndjson(resp.data)
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
    assert resp.status_code == 200
    assert resp.content_type == "application/x-ndjson"
    events = _parse_ndjson(resp.data)
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
    assert resp.status_code == 200
    assert resp.content_type == "application/x-ndjson"
    events = _parse_ndjson(resp.data)
    assert len(events) == 2
    assert events[0]["type"] == "text"
    assert events[1]["type"] == "tool_proposal"
    assert events[1]["tool_name"] == "run_code_agent"


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
    assert resp.status_code == 200
    events = _parse_ndjson(resp.data)
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
    assert resp.status_code == 200
    assert resp.content_type == "application/x-ndjson"
    events = _parse_ndjson(resp.data)
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
