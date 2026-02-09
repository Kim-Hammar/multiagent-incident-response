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
    ".routes.InformationAgent",
)
def test_step_streams_tool_proposal(
    mock_agent_cls: MagicMock,
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
    ".routes.InformationAgent",
)
def test_step_streams_assessment(
    mock_agent_cls: MagicMock,
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
    ".routes.InformationAgent",
)
def test_step_streams_error_on_failure(
    mock_agent_cls: MagicMock,
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
