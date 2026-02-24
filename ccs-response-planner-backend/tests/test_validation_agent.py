"""Tests for the /api/agents/validation endpoints."""
import json
import time
from typing import Any
from unittest.mock import MagicMock, patch

from flask.testing import FlaskClient


def _get_job_events(
    client: FlaskClient,
    resp,
    auth_headers: dict[str, str],
    max_wait: float = 2.0,
) -> list[dict[str, Any]]:
    """
    Poll a background job until done and return collected events.

    :param client: the Flask test client
    :param resp: the initial 202 response containing job_id
    :param auth_headers: authorization headers
    :param max_wait: maximum seconds to wait
    :return: a list of event dicts
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
    ".routes.ValidationAgent",
)
def test_validation_step_streams_events(
    mock_agent_cls: MagicMock,
    _mock_redeploy: MagicMock,
    _mock_sandbox: MagicMock,
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
                "container": "i1_firewall",
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
    events = _get_job_events(client, resp, auth_headers)
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
    POST /api/agents/validation/tool runs dt_exec as background job.
    """
    mock_agent = MagicMock()
    mock_agent.execute_tool_stream.return_value = iter([
        {
            "type": "done",
            "container": "i1_firewall",
            "command": "iptables -L",
            "exit_code": 0,
            "output": "Chain INPUT...",
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
    assert events[-1]["exit_code"] == 0


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
    ".routes.ValidationAgent",
)
@patch(
    "ccs_response_planner_backend.rest_api.resources.agents"
    ".routes.DatabaseFacade",
)
def test_validation_step_accepts_planner_report_id(
    mock_db: MagicMock,
    mock_agent_cls: MagicMock,
    _mock_redeploy: MagicMock,
    _mock_sandbox: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    POST /api/agents/validation/step with planner_report_id
    loads the policy and passes has_policy=True to the agent.
    """
    mock_db.get_policy_data.return_value = None
    mock_db.get_digital_twin_config.return_value = None
    mock_agent = MagicMock()
    mock_agent.step_stream.return_value = iter([
        {"type": "text", "delta": "checking"},
    ])
    mock_agent_cls.return_value = mock_agent
    resp = client.post(
        "/api/agents/validation/step",
        data=json.dumps({
            "system_description": "test system",
            "incident_report": "test report",
            "planner_report_id": 42,
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    _get_job_events(client, resp, auth_headers)
    mock_db.get_policy_data.assert_called_once_with(42)


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
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "prompt" in data
    assert "My system" in data["prompt"]
    assert "My report" in data["prompt"]
