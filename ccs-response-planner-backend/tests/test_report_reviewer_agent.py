"""Tests for the ReportReviewerAgent."""
import base64
import json
from unittest.mock import MagicMock, patch

from ccs_response_planner_backend.agents.report_reviewer_agent.tools import (
    STREAMING_TOOL_DISPATCH,
    TOOL_DISPATCH,
)


def test_tool_dispatch_has_all_tools() -> None:
    """
    TOOL_DISPATCH must contain all nine tool functions.

    ``generate_attack_image`` is intentionally excluded
    because the reviewer should not regenerate images.
    """
    expected = {
        "tavily_search",
        "nvd_search",
        "mitre_search",
        "virustotal_scan",
        "abuseipdb_check",
        "otx_search",
        "dt_exec",
        "dt_restart",
        "dt_python_exec",
    }
    assert set(TOOL_DISPATCH.keys()) == expected


def test_streaming_tool_dispatch_has_streaming_tools() -> None:
    """
    STREAMING_TOOL_DISPATCH must contain the streaming tools.
    """
    expected = {"dt_exec", "dt_restart"}
    assert set(STREAMING_TOOL_DISPATCH.keys()) == expected


def _make_part(
    text: str = "",
    fc_name: str = "",
    fc_args: dict | None = None,
    thought: bool = False,
    thought_signature: bytes | None = None,
) -> MagicMock:
    """
    Create a mock Gemini Part for the new google-genai SDK.

    :param text: text content of the part
    :param fc_name: function call name (empty = no call)
    :param fc_args: function call arguments
    :param thought: whether this is a thinking part
    :param thought_signature: optional thought signature bytes
    :return: a MagicMock mimicking a genai Part
    """
    part = MagicMock()
    part.text = text
    part.thought = thought
    part.thought_signature = thought_signature

    if fc_name:
        part.function_call = MagicMock()
        part.function_call.name = fc_name
        part.function_call.args = fc_args or {}
    else:
        part.function_call = MagicMock()
        part.function_call.name = ""
        part.function_call.args = None
    return part


def _mock_client_stream(
    mock_genai: MagicMock,
    chunks: list[list[MagicMock]],
) -> MagicMock:
    """
    Set up mock_genai.Client so generate_content_stream yields chunks.

    Each element in chunks is a list of parts for one chunk.

    :param mock_genai: the patched genai module
    :param chunks: list of part-lists, one per chunk
    :return: the mock client instance
    """
    stream_chunks = []
    for chunk_parts in chunks:
        candidate = MagicMock()
        candidate.content = MagicMock()
        candidate.content.parts = chunk_parts
        chunk = MagicMock()
        chunk.candidates = [candidate]
        chunk.usage_metadata = None
        stream_chunks.append(chunk)

    mock_client = MagicMock()
    mock_client.models.generate_content_stream.return_value = iter(
        stream_chunks,
    )
    mock_genai.Client.return_value = mock_client
    return mock_client


@patch(
    "ccs_response_planner_backend.agents.report_reviewer_agent"
    ".agent.genai",
)
def test_agent_step_stream_yields_tool_proposal(
    mock_genai: MagicMock,
) -> None:
    """
    ReportReviewerAgent.step_stream should yield text then
    a tool_proposal event when the model responds with a
    function call.
    """
    from ccs_response_planner_backend.agents.report_reviewer_agent.agent import (
        ReportReviewerAgent,
    )

    text_part = _make_part(text="I will verify the IOCs")
    fc_part = _make_part(
        fc_name="tavily_search", fc_args={"query": "test"},
    )

    _mock_client_stream(
        mock_genai, [[text_part], [fc_part]],
    )

    agent = ReportReviewerAgent()
    events = list(agent.step_stream(
        system_description="test system",
        security_alerts="test alerts",
        operator_feedback="",
        incident_report={
            "incident_summary": "Test incident",
            "attack_vector_analysis": "SSH brute force",
            "indicators_of_compromise": [],
            "severity": "High",
            "severity_justification": "Compromised",
            "affected_assets": [],
        },
        conversation_history=[],
    ))
    # First event is system_prompt
    non_prompt = [
        e for e in events if e["type"] != "system_prompt"
    ]
    assert len(non_prompt) == 2
    assert non_prompt[0] == {
        "type": "text", "delta": "I will verify the IOCs",
    }
    assert non_prompt[1]["type"] == "tool_proposal"
    assert non_prompt[1]["tool_name"] == "tavily_search"
    assert non_prompt[1]["tool_args"] == {"query": "test"}
    assert non_prompt[1]["rationale"] == (
        "I will verify the IOCs"
    )
    assert "_model_parts" in non_prompt[1]


@patch(
    "ccs_response_planner_backend.agents.report_reviewer_agent"
    ".agent.genai",
)
def test_agent_step_stream_yields_report_review(
    mock_genai: MagicMock,
) -> None:
    """
    ReportReviewerAgent.step_stream should yield a report_review
    event when the model calls produce_report_review.
    """
    from ccs_response_planner_backend.agents.report_reviewer_agent.agent import (
        ReportReviewerAgent,
    )

    review_args = {
        "executive_summary": "Report is mostly complete.",
        "findings": [
            {
                "category": "evidence_quality",
                "severity": "major",
                "description": "IP not verified",
                "recommendation": "Check AbuseIPDB",
            },
        ],
        "missing_elements": [],
        "evidence_gaps": [],
        "strengths": ["Good severity analysis"],
        "overall_verdict": "needs_revision",
    }
    fc_part = _make_part(
        fc_name="produce_report_review",
        fc_args=review_args,
    )

    _mock_client_stream(
        mock_genai, [[fc_part]],
    )

    agent = ReportReviewerAgent()
    events = list(agent.step_stream(
        system_description="test",
        security_alerts="alerts",
        operator_feedback="",
        incident_report={"incident_summary": "Test"},
        conversation_history=[
            {"type": "tool_result", "tool_name": "tavily_search",
             "result": {}},
        ],
    ))
    non_prompt = [
        e for e in events if e["type"] != "system_prompt"
    ]
    assert non_prompt[-1]["type"] == "report_review"
    review = non_prompt[-1]["report_review"]
    assert review["overall_verdict"] == "needs_revision"
    assert len(review["findings"]) == 1
    assert review["findings"][0]["category"] == (
        "evidence_quality"
    )


@patch(
    "ccs_response_planner_backend.agents.report_reviewer_agent"
    ".agent.genai",
)
def test_agent_step_stream_yields_thinking_events(
    mock_genai: MagicMock,
) -> None:
    """
    ReportReviewerAgent.step_stream should yield thinking events
    for thought parts, separate from regular text events.
    """
    from ccs_response_planner_backend.agents.report_reviewer_agent.agent import (
        ReportReviewerAgent,
    )

    thought_part = _make_part(
        text="Let me analyze the report", thought=True,
    )
    text_part = _make_part(text="I will verify")
    fc_part = _make_part(
        fc_name="tavily_search", fc_args={"query": "test"},
    )

    _mock_client_stream(
        mock_genai,
        [[thought_part], [text_part], [fc_part]],
    )

    agent = ReportReviewerAgent()
    events = list(agent.step_stream(
        system_description="test",
        security_alerts="alerts",
        operator_feedback="",
        incident_report={"incident_summary": "Test"},
        conversation_history=[],
    ))
    non_prompt = [
        e for e in events if e["type"] != "system_prompt"
    ]
    assert len(non_prompt) == 3
    assert non_prompt[0] == {
        "type": "thinking",
        "delta": "Let me analyze the report",
    }
    assert non_prompt[1] == {
        "type": "text", "delta": "I will verify",
    }
    assert non_prompt[2]["type"] == "tool_proposal"
    assert non_prompt[2]["thinking_trace"] == (
        "Let me analyze the report"
    )


def test_format_incident_report_with_full_data() -> None:
    """
    _format_incident_report should format all sections into
    readable markdown text.
    """
    from ccs_response_planner_backend.agents.report_reviewer_agent.agent import (
        ReportReviewerAgent,
    )

    report = {
        "incident_summary": "SSH brute-force attack detected.",
        "attack_vector_analysis": "Dictionary attack on port 22.",
        "indicators_of_compromise": [
            {
                "type": "ip",
                "value": "203.0.113.42",
                "context": "Source of brute-force attempts.",
            },
        ],
        "severity": "High",
        "severity_justification": "Active exploitation.",
        "affected_assets": [
            {"asset": "server_1", "impact": "Root compromised."},
        ],
    }
    formatted = ReportReviewerAgent._format_incident_report(
        report,
    )
    assert "### Incident Summary" in formatted
    assert "SSH brute-force" in formatted
    assert "### Attack Vector Analysis" in formatted
    assert "### Indicators of Compromise" in formatted
    assert "203.0.113.42" in formatted
    assert "### Severity" in formatted
    assert "**High**" in formatted
    assert "### Affected Assets" in formatted
    assert "server_1" in formatted


def test_format_incident_report_empty() -> None:
    """
    _format_incident_report should return N/A for empty data.
    """
    from ccs_response_planner_backend.agents.report_reviewer_agent.agent import (
        ReportReviewerAgent,
    )

    formatted = ReportReviewerAgent._format_incident_report({})
    assert formatted == "N/A"


def test_format_iteration_note_first() -> None:
    """
    _format_iteration_note returns empty string for iteration 1.
    """
    from ccs_response_planner_backend.agents.report_reviewer_agent.agent import (
        ReportReviewerAgent,
    )

    note = ReportReviewerAgent._format_iteration_note(1)
    assert note == ""


def test_format_iteration_note_second() -> None:
    """
    _format_iteration_note returns iteration note for iteration 2.
    """
    from ccs_response_planner_backend.agents.report_reviewer_agent.agent import (
        ReportReviewerAgent,
    )

    note = ReportReviewerAgent._format_iteration_note(2)
    assert "2nd review iteration" in note


def test_format_iteration_note_fourth() -> None:
    """
    _format_iteration_note returns 4th for iteration 4.
    """
    from ccs_response_planner_backend.agents.report_reviewer_agent.agent import (
        ReportReviewerAgent,
    )

    note = ReportReviewerAgent._format_iteration_note(4)
    assert "4th review iteration" in note


def test_parse_report_review_fallback() -> None:
    """
    _parse_report_review should fall back gracefully when
    the model output is not valid JSON.
    """
    from ccs_response_planner_backend.agents.report_reviewer_agent.agent import (
        ReportReviewerAgent,
    )

    agent = ReportReviewerAgent()
    raw = "This is not valid JSON at all."
    result = agent._parse_report_review(raw)
    assert result["type"] == "report_review"
    r = result["report_review"]
    assert r["executive_summary"] == raw
    assert r["findings"] == []
    assert r["missing_elements"] == []
    assert r["evidence_gaps"] == []
    assert r["strengths"] == []
    assert r["overall_verdict"] == ""


def test_parse_report_review_strips_code_fences() -> None:
    """
    _parse_report_review should strip markdown code fences
    and parse the inner JSON correctly.
    """
    from ccs_response_planner_backend.agents.report_reviewer_agent.agent import (
        ReportReviewerAgent,
    )

    inner = {
        "executive_summary": "Fenced",
        "findings": [],
        "missing_elements": [],
        "evidence_gaps": [],
        "strengths": [],
        "overall_verdict": "pass",
    }
    fenced = "```json\n" + json.dumps(inner) + "\n```"
    agent = ReportReviewerAgent()
    result = agent._parse_report_review(fenced)
    assert result["type"] == "report_review"
    assert result["report_review"]["overall_verdict"] == "pass"
    assert result["report_review"]["executive_summary"] == (
        "Fenced"
    )


def test_serialize_part_with_thought_signature() -> None:
    """
    _serialize_part should store thought_signature as base64.
    """
    from ccs_response_planner_backend.agents.report_reviewer_agent.agent import (
        ReportReviewerAgent,
    )

    sig_bytes = b"\x01\x02\x03\x04"
    part = _make_part(
        text="thinking", thought=True,
        thought_signature=sig_bytes,
    )
    serialized = ReportReviewerAgent._serialize_part(part)
    assert serialized["text"] == "thinking"
    assert serialized["thought"] is True
    assert serialized["thought_signature"] == (
        base64.b64encode(sig_bytes).decode("ascii")
    )


def test_decode_raw_parts_with_thought_signature() -> None:
    """
    _decode_raw_parts should decode base64 thought_signature
    back to bytes.
    """
    from ccs_response_planner_backend.agents.report_reviewer_agent.agent import (
        ReportReviewerAgent,
    )

    sig_bytes = b"\x01\x02\x03\x04"
    raw = [
        {
            "text": "hello",
            "thought": True,
            "thought_signature": base64.b64encode(
                sig_bytes,
            ).decode("ascii"),
        },
        {"function_call": {"name": "test", "args": {}}},
    ]
    decoded = ReportReviewerAgent._decode_raw_parts(raw)
    assert decoded[0]["text"] == "hello"
    assert decoded[0]["thought"] is True
    assert decoded[0]["thought_signature"] == sig_bytes
    assert decoded[1] == {
        "function_call": {"name": "test", "args": {}},
    }


def test_has_used_tool_with_tool_result() -> None:
    """
    _has_used_tool should return True when history has
    a tool_result entry.
    """
    from ccs_response_planner_backend.agents.report_reviewer_agent.agent import (
        ReportReviewerAgent,
    )

    history = [
        {"type": "tool_proposal", "tool_name": "tavily_search"},
        {"type": "tool_result", "tool_name": "tavily_search",
         "result": {}},
    ]
    assert ReportReviewerAgent._has_used_tool(history) is True


def test_has_used_tool_without_tool_result() -> None:
    """
    _has_used_tool should return False when history has
    no tool_result entries.
    """
    from ccs_response_planner_backend.agents.report_reviewer_agent.agent import (
        ReportReviewerAgent,
    )

    history = [
        {"type": "tool_proposal", "tool_name": "tavily_search"},
    ]
    assert ReportReviewerAgent._has_used_tool(history) is False


def test_execute_tool_unknown() -> None:
    """
    execute_tool should return error for unknown tools.
    """
    from ccs_response_planner_backend.agents.report_reviewer_agent.agent import (
        ReportReviewerAgent,
    )

    agent = ReportReviewerAgent()
    result = agent.execute_tool("unknown_tool", {})
    assert result["tool_name"] == "unknown_tool"
    assert "error" in result


@patch(
    "ccs_response_planner_backend.agents.report_agent"
    ".tools.TavilyClient",
)
def test_execute_tool_calls_dispatch(
    mock_client_cls: MagicMock,
) -> None:
    """
    execute_tool should call the dispatched tool function.
    """
    from ccs_response_planner_backend.agents.report_reviewer_agent.agent import (
        ReportReviewerAgent,
    )

    mock_client = MagicMock()
    mock_client.search.return_value = {
        "results": [],
        "response_time": 0.1,
    }
    mock_client_cls.return_value = mock_client
    agent = ReportReviewerAgent()
    result = agent.execute_tool(
        "tavily_search", {"query": "test"},
    )
    assert result["tool_name"] == "tavily_search"
    assert "result" in result
