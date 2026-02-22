"""Tests for the OrchestratorAgent."""
from unittest.mock import MagicMock, patch

from ccs_response_planner_backend.agents.orchestrator_agent.agent import (
    OrchestratorAgent,
)
from ccs_response_planner_backend.agents.orchestrator_agent.tools import (
    STREAMING_TOOL_DISPATCH,
    TOOL_DISPATCH,
)
from ccs_response_planner_backend.agents.orchestrator_agent.tool_declarations import (  # noqa: E501
    ALL_DECLARATIONS,
    ITERATING_DECLARATIONS,
)


# ── Tool dispatch registry ────────────────────────────────────


def test_tool_dispatch_is_empty() -> None:
    """
    TOOL_DISPATCH must be empty (all tools are streaming).
    """
    assert len(TOOL_DISPATCH) == 0


def test_streaming_dispatch_has_two_tools() -> None:
    """
    STREAMING_TOOL_DISPATCH must contain both sub-agent tools.
    """
    expected = {
        "run_report_manager",
        "run_plan_manager",
    }
    assert set(STREAMING_TOOL_DISPATCH.keys()) == expected


# ── Declaration lists ─────────────────────────────────────────


def test_iterating_declarations_count() -> None:
    """
    ITERATING_DECLARATIONS has exactly 2 tools.
    """
    assert len(ITERATING_DECLARATIONS) == 2
    names = {d.name for d in ITERATING_DECLARATIONS}
    assert names == {
        "run_report_manager",
        "run_plan_manager",
    }


def test_all_declarations_count() -> None:
    """
    ALL_DECLARATIONS has exactly 3 tools.
    """
    assert len(ALL_DECLARATIONS) == 3
    names = {d.name for d in ALL_DECLARATIONS}
    assert names == {
        "run_report_manager",
        "run_plan_manager",
        "produce_orchestrator_agent_report",
    }


# ── _has_planned gating ──────────────────────────────────────


def test_has_planned_false_when_empty() -> None:
    """
    _has_planned returns False when history is empty.
    """
    assert OrchestratorAgent._has_planned([]) is False


def test_has_planned_false_without_plan_manager_result() -> None:
    """
    _has_planned returns False when no plan manager result exists.
    """
    history = [
        {
            "type": "tool_result",
            "tool_name": "run_report_manager",
            "result": {},
        },
    ]
    assert OrchestratorAgent._has_planned(history) is False


def test_has_planned_true_with_plan_manager_result() -> None:
    """
    _has_planned returns True when plan manager result exists.
    """
    history = [
        {
            "type": "tool_result",
            "tool_name": "run_report_manager",
            "result": {},
        },
        {
            "type": "tool_result",
            "tool_name": "run_plan_manager",
            "result": {},
        },
    ]
    assert OrchestratorAgent._has_planned(history) is True


# ── _parse_orchestrator_agent_report ──────────────────────────


def test_parse_valid_json() -> None:
    """
    _parse_orchestrator_agent_report parses valid JSON.
    """
    agent = OrchestratorAgent()
    text = (
        '{"executive_summary": "Done", '
        '"iterations": 1, '
        '"final_verdict": "pass", '
        '"assessment_summary": "OK", '
        '"response_plan_summary": "OK"}'
    )
    result = agent._parse_orchestrator_agent_report(text)
    assert result["type"] == "orchestrator_agent_report"
    report = result["orchestrator_agent_report"]
    assert report["executive_summary"] == "Done"
    assert report["iterations"] == 1
    assert report["final_verdict"] == "pass"


def test_parse_json_with_code_fences() -> None:
    """
    _parse_orchestrator_agent_report strips markdown code fences.
    """
    agent = OrchestratorAgent()
    text = (
        '```json\n'
        '{"executive_summary": "test", '
        '"iterations": 2, '
        '"final_verdict": "pass", '
        '"assessment_summary": "", '
        '"response_plan_summary": ""}\n'
        '```'
    )
    result = agent._parse_orchestrator_agent_report(text)
    report = result["orchestrator_agent_report"]
    assert report["iterations"] == 2


def test_parse_fallback_on_invalid_json() -> None:
    """
    _parse_orchestrator_agent_report falls back for non-JSON text.
    """
    agent = OrchestratorAgent()
    result = agent._parse_orchestrator_agent_report(
        "Not valid JSON at all",
    )
    assert result["type"] == "orchestrator_agent_report"
    report = result["orchestrator_agent_report"]
    assert report["executive_summary"] == (
        "Not valid JSON at all"
    )
    assert report["iterations"] == 0
    assert report["final_verdict"] == "unknown"
    assert report["assessment_summary"] == ""
    assert report["response_plan_summary"] == ""


# ── step_stream with mock Gemini ──────────────────────────────


def _make_mock_chunk(
    parts: list[dict],
    usage_metadata: dict | None = None,
) -> MagicMock:
    """
    Create a mock Gemini streaming chunk.

    :param parts: list of part dicts
    :param usage_metadata: optional usage metadata
    :return: a mock chunk
    """
    chunk = MagicMock()
    chunk.usage_metadata = usage_metadata

    mock_parts = []
    for p in parts:
        part = MagicMock()
        part.text = p.get("text")
        part.thought = p.get("thought", False)
        part.thought_signature = p.get(
            "thought_signature",
        )

        if "function_call" in p:
            fc = MagicMock()
            fc.name = p["function_call"]["name"]
            fc.args = p["function_call"].get("args", {})
            part.function_call = fc
        else:
            part.function_call = MagicMock()
            part.function_call.name = None

        mock_parts.append(part)

    candidate = MagicMock()
    candidate.content.parts = mock_parts
    chunk.candidates = [candidate]
    return chunk


@patch.dict("os.environ", {"GEMINI_API_KEY": "test"})
@patch(
    "ccs_response_planner_backend.agents."
    "orchestrator_agent.agent.genai",
)
def test_step_stream_yields_tool_proposal(
    mock_genai: MagicMock,
) -> None:
    """
    step_stream yields a tool_proposal event.
    """
    chunk = _make_mock_chunk([{
        "text": "Let me run the report manager",
    }, {
        "function_call": {
            "name": "run_report_manager",
            "args": {},
        },
    }])
    mock_client = MagicMock()
    mock_client.models.generate_content_stream.return_value = [
        chunk,
    ]
    mock_genai.Client.return_value = mock_client

    agent = OrchestratorAgent()
    events = list(agent.step_stream(
        system_description="test",
        security_alerts="alerts",
        operator_feedback="",
        conversation_history=[],
    ))

    tool_proposals = [
        e for e in events
        if e.get("type") == "tool_proposal"
    ]
    assert len(tool_proposals) == 1
    assert tool_proposals[0]["tool_name"] == (
        "run_report_manager"
    )


@patch.dict("os.environ", {"GEMINI_API_KEY": "test"})
@patch(
    "ccs_response_planner_backend.agents."
    "orchestrator_agent.agent.genai",
)
def test_step_stream_yields_orchestrator_agent_report(
    mock_genai: MagicMock,
) -> None:
    """
    step_stream yields an orchestrator_agent_report event.
    """
    chunk = _make_mock_chunk([{
        "function_call": {
            "name": "produce_orchestrator_agent_report",
            "args": {
                "executive_summary": "Done",
                "iterations": 1,
                "final_verdict": "pass",
                "assessment_summary": "Assessment OK",
                "response_plan_summary": "Plan OK",
            },
        },
    }])
    mock_client = MagicMock()
    mock_client.models.generate_content_stream.return_value = [
        chunk,
    ]
    mock_genai.Client.return_value = mock_client

    agent = OrchestratorAgent()
    history = [
        {
            "type": "tool_result",
            "tool_name": "run_plan_manager",
            "result": {},
        },
    ]
    events = list(agent.step_stream(
        system_description="test",
        security_alerts="alerts",
        operator_feedback="",
        conversation_history=history,
    ))

    reports = [
        e for e in events
        if e.get("type") == "orchestrator_agent_report"
    ]
    assert len(reports) == 1
    report = reports[0]["orchestrator_agent_report"]
    assert report["final_verdict"] == "pass"
    assert report["iterations"] == 1


@patch.dict("os.environ", {"GEMINI_API_KEY": "test"})
@patch(
    "ccs_response_planner_backend.agents."
    "orchestrator_agent.agent.genai",
)
def test_step_stream_includes_thinking_trace(
    mock_genai: MagicMock,
) -> None:
    """
    step_stream includes thinking_trace on tool proposals.
    """
    chunk = _make_mock_chunk([
        {"text": "thinking...", "thought": True},
        {
            "function_call": {
                "name": "run_report_manager",
                "args": {},
            },
        },
    ])
    mock_client = MagicMock()
    mock_client.models.generate_content_stream.return_value = [
        chunk,
    ]
    mock_genai.Client.return_value = mock_client

    agent = OrchestratorAgent()
    events = list(agent.step_stream(
        system_description="test",
        security_alerts="alerts",
        operator_feedback="",
        conversation_history=[],
    ))

    thinking = [
        e for e in events
        if e.get("type") == "thinking"
    ]
    assert len(thinking) == 1
    assert thinking[0]["delta"] == "thinking..."

    proposals = [
        e for e in events
        if e.get("type") == "tool_proposal"
    ]
    assert proposals[0]["thinking_trace"] == "thinking..."


@patch.dict("os.environ", {"GEMINI_API_KEY": "test"})
@patch(
    "ccs_response_planner_backend.agents."
    "orchestrator_agent.agent.genai",
)
def test_step_stream_yields_context_usage(
    mock_genai: MagicMock,
) -> None:
    """
    step_stream yields context_usage from usage_metadata.
    """
    usage = MagicMock()
    usage.prompt_token_count = 100
    usage.candidates_token_count = 200
    usage.total_token_count = 300
    chunk = _make_mock_chunk(
        [{"text": "some text"}],
        usage_metadata=usage,
    )
    mock_client = MagicMock()
    mock_client.models.generate_content_stream.return_value = [
        chunk,
    ]
    mock_genai.Client.return_value = mock_client

    agent = OrchestratorAgent()
    events = list(agent.step_stream(
        system_description="test",
        security_alerts="alerts",
        operator_feedback="",
        conversation_history=[],
    ))

    ctx = [
        e for e in events
        if e.get("type") == "context_usage"
    ]
    assert len(ctx) == 1
    assert ctx[0]["prompt_tokens"] == 100
    assert ctx[0]["total_tokens"] == 300


# ── _summarize_tool_result ────────────────────────────────────


def test_summarize_report_manager_result() -> None:
    """
    _summarize_tool_result keeps only the report_manager_report
    and drops the full assessment.
    """
    result = {
        "report_manager_report": {
            "executive_summary": "Done",
            "iterations": 2,
            "final_verdict": "pass",
            "report_summary": "RS",
            "review_summary": "RVS",
        },
        "assessment": {
            "incident_summary": "Very long...",
            "attack_vector_analysis": "Long...",
            "indicators_of_compromise": [
                {"type": "ip", "value": "1.2.3.4"},
            ],
        },
    }
    summary = OrchestratorAgent._summarize_tool_result(
        "run_report_manager", result,
    )
    assert "assessment" not in summary
    report = summary["report_manager_report"]
    assert report["executive_summary"] == "Done"
    assert report["final_verdict"] == "pass"
    assert report["iterations"] == 2


def test_summarize_plan_manager_result() -> None:
    """
    _summarize_tool_result keeps only the plan_manager_report
    and drops the full response_plan code.
    """
    result = {
        "plan_manager_report": {
            "executive_summary": "Plan OK",
            "iterations": 1,
            "final_verdict": "pass",
            "code_manager_summary": "CM",
            "planner_agent_summary": "RL",
            "validation_summary": "V",
        },
        "response_plan": "class Env:\n  ...(10k lines)...",
    }
    summary = OrchestratorAgent._summarize_tool_result(
        "run_plan_manager", result,
    )
    assert "response_plan" not in summary
    report = summary["plan_manager_report"]
    assert report["executive_summary"] == "Plan OK"
    assert report["final_verdict"] == "pass"


def test_summarize_unknown_tool_passes_through() -> None:
    """
    _summarize_tool_result passes unknown tools through.
    """
    result = {"foo": "bar"}
    summary = OrchestratorAgent._summarize_tool_result(
        "some_other_tool", result,
    )
    assert summary == result


# ── execute_tool / execute_tool_stream ────────────────────────


def test_execute_tool_unknown_returns_error() -> None:
    """
    execute_tool with unknown tool returns error.
    """
    agent = OrchestratorAgent()
    result = agent.execute_tool("nonexistent", {})
    assert "error" in result
    assert "Unknown tool" in result["error"]


def test_execute_tool_stream_unknown_yields_error() -> None:
    """
    execute_tool_stream with unknown tool yields error.
    """
    agent = OrchestratorAgent()
    events = list(agent.execute_tool_stream(
        "nonexistent", {},
    ))
    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert "Unknown streaming tool" in (
        events[0]["message"]
    )
