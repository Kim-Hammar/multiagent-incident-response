"""Tests for the /api/agents/validation endpoints."""
import json
from typing import Any
from unittest.mock import MagicMock, patch

from flask.testing import FlaskClient


def _parse_ndjson(data: bytes) -> list[dict[str, Any]]:
    """
    Parse newline-delimited JSON bytes into a list of dicts.

    :param data: raw NDJSON response bytes
    :return: a list of parsed event dicts
    """
    lines = data.decode("utf-8").strip().split("\n")
    return [json.loads(line) for line in lines if line.strip()]


def test_validation_step_401_without_token(
    client: FlaskClient,
) -> None:
    """
    POST /api/agents/validation/step without a token returns 401.
    """
    resp = client.post(
        "/api/agents/validation/step",
        data=json.dumps({
            "system_description": "test",
        }),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_validation_step_400_missing_fields(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/validation/step with no fields returns 400.
    """
    resp = client.post(
        "/api/agents/validation/step",
        data=json.dumps({}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.ValidationAgent",
)
def test_validation_step_streams_events(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/validation/step streams text then
    tool_proposal.
    """
    mock_agent = MagicMock()
    mock_agent.step_stream.return_value = iter([
        {"type": "text", "delta": "Applying action"},
        {
            "type": "tool_proposal",
            "tool_name": "dt_exec",
            "tool_args": {
                "container": "firewall",
                "command": "iptables -A INPUT -s 10.0.1.10 "
                           "-j DROP",
            },
            "rationale": "Applying action",
        },
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/validation/step",
        data=json.dumps({
            "system_description": "test system",
            "incident_report": "test report",
            "response_plan": "1. Block attacker",
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
    assert events[1]["tool_name"] == "dt_exec"


def test_validation_tool_400_unknown_tool(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/validation/tool with unknown tool returns 400.
    """
    resp = client.post(
        "/api/agents/validation/tool",
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
    ".routes.ValidationAgent",
)
def test_validation_tool_executes_dt_exec(
    mock_agent_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/validation/tool executes dt_exec.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool.return_value = {
        "tool_name": "dt_exec",
        "result": {
            "container": "firewall",
            "command": "iptables -L",
            "exit_code": 0,
            "output": "Chain INPUT...",
        },
    }
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/validation/tool",
        data=json.dumps({
            "tool_name": "dt_exec",
            "tool_args": {
                "container": "firewall",
                "command": "iptables -L",
            },
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["tool_name"] == "dt_exec"
    assert "result" in data


def test_validation_prompt_renders(
    client: FlaskClient, auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/validation/prompt renders the system prompt.
    """
    resp = client.post(
        "/api/agents/validation/prompt",
        data=json.dumps({
            "system_description": "My system",
            "incident_report": "My report",
            "response_plan": "My plan",
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "prompt" in data
    assert "My system" in data["prompt"]
    assert "My report" in data["prompt"]
    assert "My plan" in data["prompt"]
