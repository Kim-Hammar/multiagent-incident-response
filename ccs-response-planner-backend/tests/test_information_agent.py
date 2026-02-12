"""Tests for the InformationAgent and its standalone tool functions."""
import base64
import json
from unittest.mock import MagicMock, patch

import docker as docker_module

from ccs_response_planner_backend.agents.information_agent.tools import (
    TOOL_DISPATCH,
    abuseipdb_check,
    dt_exec,
    dt_python_exec,
    mitre_search,
    nvd_search,
    otx_search,
    tavily_search,
    virustotal_scan,
)


def test_tool_dispatch_has_all_tools() -> None:
    """
    TOOL_DISPATCH must contain all nine tool functions.
    """
    expected = {
        "tavily_search",
        "nvd_search",
        "mitre_search",
        "virustotal_scan",
        "abuseipdb_check",
        "otx_search",
        "dt_exec",
        "dt_python_exec",
        "generate_attack_image",
    }
    assert set(TOOL_DISPATCH.keys()) == expected


@patch(
    "ccs_response_planner_backend.agents.information_agent"
    ".tools.TavilyClient",
)
def test_tavily_search_returns_results(
    mock_client_cls: MagicMock,
) -> None:
    """
    tavily_search should return a dict with query and results.
    """
    mock_client = MagicMock()
    mock_client.search.return_value = {
        "results": [
            {
                "title": "Test",
                "url": "https://example.com",
                "content": "content",
                "score": 0.9,
            },
        ],
        "response_time": 0.5,
    }
    mock_client_cls.return_value = mock_client
    result = tavily_search("test query")
    assert result["query"] == "test query"
    assert len(result["results"]) == 1
    assert result["results"][0]["title"] == "Test"
    assert result["response_time"] == 0.5


@patch(
    "ccs_response_planner_backend.agents.information_agent"
    ".tools.nvdlib",
)
def test_nvd_search_by_cve_id(mock_nvdlib: MagicMock) -> None:
    """
    nvd_search with a cve_id should search by CVE ID.
    """
    mock_cve = MagicMock()
    mock_cve.id = "CVE-2021-44228"
    mock_cve.descriptions = []
    mock_cve.v31score = 10.0
    mock_cve.published = "2021-12-10"
    mock_nvdlib.searchCVE.return_value = [mock_cve]
    result = nvd_search(cve_id="CVE-2021-44228")
    assert result["query"] == "CVE-2021-44228"
    assert len(result["results"]) == 1
    assert result["results"][0]["id"] == "CVE-2021-44228"


@patch(
    "ccs_response_planner_backend.agents.information_agent"
    ".tools._get_attack_data",
)
def test_mitre_search_by_keyword(
    mock_get_data: MagicMock,
) -> None:
    """
    mitre_search with a search keyword should return matching techniques.
    """
    mock_technique = MagicMock()
    mock_technique.name = "Command Line Interface"
    mock_technique.description = "Adversaries use CLI"
    mock_technique.external_references = []
    mock_technique.kill_chain_phases = []
    mock_attack_data = MagicMock()
    mock_attack_data.get_techniques.return_value = [mock_technique]
    mock_get_data.return_value = mock_attack_data
    result = mitre_search(search="command")
    assert result["query"] == "command"
    assert len(result["results"]) == 1


@patch(
    "ccs_response_planner_backend.agents.information_agent"
    ".tools.vt",
)
def test_virustotal_scan(mock_vt: MagicMock) -> None:
    """
    virustotal_scan should look up an indicator and return results.
    """
    mock_obj = MagicMock()
    mock_obj.reputation = 0
    mock_obj.last_analysis_stats = {"malicious": 0}
    mock_obj.last_analysis_date = "2024-01-01"
    mock_client = MagicMock()
    mock_client.get_object.return_value = mock_obj
    mock_vt.Client.return_value = mock_client
    mock_vt.url_id.return_value = "url_id_hash"
    with patch.dict(
        "os.environ", {"VIRUSTOTAL_API_KEY": "test-key"},
    ):
        result = virustotal_scan("domain", "example.com")
    assert "result" in result
    assert result["result"]["type"] == "domain"
    assert result["result"]["value"] == "example.com"


@patch(
    "ccs_response_planner_backend.agents.information_agent"
    ".tools.http_requests",
)
def test_abuseipdb_check(
    mock_requests: MagicMock,
) -> None:
    """
    abuseipdb_check should check an IP and return results.
    """
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "data": {
            "ipAddress": "1.2.3.4",
            "abuseConfidenceScore": 50,
            "isp": "TestISP",
            "countryCode": "US",
            "totalReports": 10,
            "lastReportedAt": "2024-01-01",
            "isPublic": True,
        },
    }
    mock_requests.get.return_value = mock_resp
    with patch.dict(
        "os.environ", {"ABUSEIPDB_API_KEY": "test-key"},
    ):
        result = abuseipdb_check("1.2.3.4")
    assert "result" in result
    assert result["result"]["ip"] == "1.2.3.4"
    assert result["result"]["abuse_confidence_score"] == 50


@patch(
    "ccs_response_planner_backend.agents.information_agent"
    ".tools.OTXv2",
)
def test_otx_search(mock_otx_cls: MagicMock) -> None:
    """
    otx_search should search for an indicator and return results.
    """
    mock_otx = MagicMock()
    mock_otx.get_indicator_details_full.return_value = {
        "general": {
            "pulse_info": {
                "count": 2,
                "pulses": [
                    {
                        "name": "Pulse1",
                        "description": "desc",
                        "created": "2024-01-01",
                        "tags": ["tag1"],
                    },
                ],
            },
            "reputation": 0,
        },
    }
    mock_otx_cls.return_value = mock_otx
    with patch.dict(
        "os.environ", {"OTX_API_KEY": "test-key"},
    ):
        result = otx_search("IPv4", "1.2.3.4")
    assert "result" in result
    assert result["result"]["type"] == "IPv4"
    assert result["result"]["pulse_count"] == 2


@patch(
    "ccs_response_planner_backend.agents.shared_tools.docker",
)
def test_dt_exec_returns_output(
    mock_docker: MagicMock,
) -> None:
    """
    dt_exec should execute a command on a DT container and
    return the output with exit code.
    """
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_container.id = "abc123"
    mock_client.containers.get.return_value = mock_container
    mock_client.api.exec_create.return_value = {"Id": "ex1"}
    mock_client.api.exec_start.return_value = b"root  1  0.0\n"
    mock_client.api.exec_inspect.return_value = {"ExitCode": 0}
    mock_docker.from_env.return_value = mock_client
    result = dt_exec("i1_gateway", "ps aux")
    assert result["container"] == "i1_gateway"
    assert result["command"] == "ps aux"
    assert result["exit_code"] == 0
    assert "root" in result["output"]


@patch(
    "ccs_response_planner_backend.agents.shared_tools"
    ".DockerManager",
)
@patch(
    "ccs_response_planner_backend.agents.shared_tools.docker",
)
def test_dt_exec_container_not_found(
    mock_docker: MagicMock,
    mock_manager: MagicMock,
) -> None:
    """
    dt_exec should return an error when the container is not
    found and auto-deploy fails.
    """
    mock_client = MagicMock()
    mock_client.containers.get.side_effect = (
        docker_module.errors.NotFound("not found")
    )
    mock_docker.from_env.return_value = mock_client
    mock_docker.errors.NotFound = docker_module.errors.NotFound
    mock_manager.ensure_deployed.side_effect = (
        RuntimeError("deploy failed")
    )
    result = dt_exec("i1_gateway", "ps aux")
    assert "error" in result
    assert "not found" in result["error"].lower()
    assert "i1_gateway" in result["error"]


@patch(
    "ccs_response_planner_backend.agents.information_agent"
    ".tools.docker",
)
def test_dt_python_exec_returns_output(
    mock_docker: MagicMock,
) -> None:
    """
    dt_python_exec should execute Python code in the sandbox
    and return the output with exit code.
    """
    mock_client = MagicMock()
    mock_sandbox = MagicMock()
    mock_sandbox.id = "sandbox1"
    mock_sandbox.status = "running"
    mock_client.containers.get.return_value = mock_sandbox
    mock_client.api.exec_create.return_value = {"Id": "ex1"}
    mock_client.api.exec_start.return_value = b"hello\n"
    mock_client.api.exec_inspect.return_value = {"ExitCode": 0}
    mock_docker.from_env.return_value = mock_client
    mock_docker.errors.NotFound = docker_module.errors.NotFound
    result = dt_python_exec("print('hello')")
    assert result["code"] == "print('hello')"
    assert result["exit_code"] == 0
    assert "hello" in result["output"]


@patch(
    "ccs_response_planner_backend.agents.information_agent"
    ".tools.docker",
)
def test_dt_python_exec_starts_sandbox(
    mock_docker: MagicMock,
) -> None:
    """
    dt_python_exec should create the sandbox container when
    it does not exist yet.
    """
    mock_client = MagicMock()
    mock_sandbox = MagicMock()
    mock_sandbox.id = "sandbox1"
    mock_client.containers.get.side_effect = (
        docker_module.errors.NotFound("not found")
    )
    mock_client.containers.run.return_value = mock_sandbox
    mock_client.api.exec_create.return_value = {"Id": "ex1"}
    mock_client.api.exec_start.return_value = b"ok\n"
    mock_client.api.exec_inspect.return_value = {"ExitCode": 0}
    mock_docker.from_env.return_value = mock_client
    mock_docker.errors.NotFound = docker_module.errors.NotFound
    result = dt_python_exec("print('ok')")
    mock_client.containers.run.assert_called_once()
    assert result["exit_code"] == 0


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


def _mock_client_generate(
    mock_genai: MagicMock,
    parts: list[MagicMock],
) -> MagicMock:
    """
    Set up mock_genai.Client so generate_content returns parts.

    :param mock_genai: the patched genai module
    :param parts: list of mock Part objects
    :return: the mock client instance
    """
    candidate = MagicMock()
    candidate.content.parts = parts

    mock_response = MagicMock()
    mock_response.candidates = [candidate]

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_genai.Client.return_value = mock_client
    return mock_client


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
    "ccs_response_planner_backend.agents.information_agent"
    ".agent.genai",
)
def test_agent_step_returns_tool_proposal(
    mock_genai: MagicMock,
) -> None:
    """
    InformationAgent.step should return a tool_proposal when the
    model responds with a function call.
    """
    from ccs_response_planner_backend.agents.information_agent.agent import (
        InformationAgent,
    )

    text_part = _make_part(text="I will search for test")
    fc_part = _make_part(
        fc_name="tavily_search", fc_args={"query": "test"},
    )

    _mock_client_generate(mock_genai, [text_part, fc_part])

    agent = InformationAgent()
    result = agent.step(
        system_description="test system",
        security_alerts="test alerts",
        operator_feedback="",
        conversation_history=[],
    )
    assert result["type"] == "tool_proposal"
    assert result["tool_name"] == "tavily_search"
    assert result["tool_args"] == {"query": "test"}
    assert result["rationale"] == "I will search for test"
    assert "_model_parts" in result


@patch(
    "ccs_response_planner_backend.agents.information_agent"
    ".agent.genai",
)
def test_agent_step_returns_assessment(
    mock_genai: MagicMock,
) -> None:
    """
    InformationAgent.step should return a structured assessment
    when the model calls the produce_assessment tool.
    """
    from ccs_response_planner_backend.agents.information_agent.agent import (
        InformationAgent,
    )

    assessment_args = {
        "incident_summary": "Test incident",
        "attack_vector_analysis": "SSH brute force",
        "indicators_of_compromise": [
            {"type": "ip", "value": "1.2.3.4",
             "context": "attacker"},
        ],
        "severity": "High",
        "severity_justification": "Compromised server",
        "affected_assets": [
            {"asset": "server1", "impact": "full access"},
        ],
    }
    fc_part = _make_part(
        fc_name="produce_assessment", fc_args=assessment_args,
    )

    _mock_client_generate(mock_genai, [fc_part])

    agent = InformationAgent()
    result = agent.step(
        system_description="test system",
        security_alerts="test alerts",
        operator_feedback="",
        conversation_history=[],
    )
    assert result["type"] == "assessment"
    assert result["assessment"]["severity"] == "High"
    assert result["assessment"]["incident_summary"] == (
        "Test incident"
    )
    assert len(
        result["assessment"]["indicators_of_compromise"],
    ) == 1


@patch(
    "ccs_response_planner_backend.agents.information_agent"
    ".tools.TavilyClient",
)
def test_agent_execute_tool(
    mock_client_cls: MagicMock,
) -> None:
    """
    InformationAgent.execute_tool should call the tool and return results.
    """
    from ccs_response_planner_backend.agents.information_agent.agent import (
        InformationAgent,
    )

    mock_client = MagicMock()
    mock_client.search.return_value = {
        "results": [],
        "response_time": 0.1,
    }
    mock_client_cls.return_value = mock_client
    agent = InformationAgent()
    result = agent.execute_tool(
        "tavily_search", {"query": "test"},
    )
    assert result["tool_name"] == "tavily_search"
    assert "result" in result


@patch(
    "ccs_response_planner_backend.agents.information_agent"
    ".agent.genai",
)
def test_agent_step_stream_yields_text_then_tool_proposal(
    mock_genai: MagicMock,
) -> None:
    """
    InformationAgent.step_stream should yield text deltas and then
    a tool_proposal event when the model responds with a function call.
    """
    from ccs_response_planner_backend.agents.information_agent.agent import (
        InformationAgent,
    )

    text_part = _make_part(text="I will search")
    fc_part = _make_part(
        fc_name="tavily_search", fc_args={"query": "test"},
    )

    _mock_client_stream(
        mock_genai, [[text_part], [fc_part]],
    )

    agent = InformationAgent()
    events = list(agent.step_stream(
        system_description="test system",
        security_alerts="test alerts",
        operator_feedback="",
        conversation_history=[],
    ))
    assert len(events) == 2
    assert events[0] == {
        "type": "text", "delta": "I will search",
    }
    assert events[1]["type"] == "tool_proposal"
    assert events[1]["tool_name"] == "tavily_search"
    assert events[1]["tool_args"] == {"query": "test"}
    assert events[1]["rationale"] == "I will search"
    assert "_model_parts" in events[1]


@patch(
    "ccs_response_planner_backend.agents.information_agent"
    ".agent.genai",
)
def test_agent_step_stream_yields_text_then_assessment(
    mock_genai: MagicMock,
) -> None:
    """
    InformationAgent.step_stream should yield text deltas and then
    a structured assessment event when the model calls
    produce_assessment.
    """
    from ccs_response_planner_backend.agents.information_agent.agent import (
        InformationAgent,
    )

    assessment_args = {
        "incident_summary": "Stream test",
        "attack_vector_analysis": "Phishing",
        "indicators_of_compromise": [],
        "severity": "Medium",
        "severity_justification": "Limited scope",
        "affected_assets": [],
    }

    text_part = _make_part(text="Here is the assessment")
    fc_part = _make_part(
        fc_name="produce_assessment", fc_args=assessment_args,
    )

    _mock_client_stream(
        mock_genai, [[text_part], [fc_part]],
    )

    agent = InformationAgent()
    events = list(agent.step_stream(
        system_description="test system",
        security_alerts="test alerts",
        operator_feedback="",
        conversation_history=[],
    ))
    assert len(events) == 2
    assert events[0]["type"] == "text"
    assert events[0]["delta"] == "Here is the assessment"
    assert events[1]["type"] == "assessment"
    assert events[1]["assessment"]["severity"] == "Medium"
    assert events[1]["assessment"]["incident_summary"] == (
        "Stream test"
    )


@patch(
    "ccs_response_planner_backend.agents.information_agent"
    ".agent.genai",
)
def test_agent_step_stream_prepends_initial_message(
    mock_genai: MagicMock,
) -> None:
    """
    InformationAgent.step_stream should always prepend the initial
    user message so Gemini contents start with a user turn.
    """
    from ccs_response_planner_backend.agents.information_agent.agent import (
        INITIAL_USER_MESSAGE,
        InformationAgent,
    )

    text_part = _make_part(text="Assessment")

    mock_client = _mock_client_stream(
        mock_genai, [[text_part]],
    )

    agent = InformationAgent()
    history = [
        {
            "type": "tool_proposal",
            "tool_name": "tavily_search",
            "tool_args": {"query": "test"},
            "rationale": "Searching",
        },
        {
            "type": "tool_approval",
            "tool_name": "tavily_search",
            "approved": True,
        },
        {
            "type": "tool_result",
            "tool_name": "tavily_search",
            "result": {"query": "test", "results": []},
        },
    ]
    list(agent.step_stream(
        system_description="test",
        security_alerts="alerts",
        operator_feedback="",
        conversation_history=history,
    ))

    call_args = (
        mock_client.models.generate_content_stream.call_args
    )
    contents = call_args[1]["contents"]
    assert contents[0] == INITIAL_USER_MESSAGE
    assert contents[0]["role"] == "user"
    assert len(contents) == 3
    # tool_result turn has function_response + continuation text
    tool_result_parts = contents[2]["parts"]
    assert len(tool_result_parts) == 2
    assert "function_response" in tool_result_parts[0]
    assert "text" in tool_result_parts[1]


def test_agent_execute_tool_unknown() -> None:
    """
    InformationAgent.execute_tool should return error for unknown tools.
    """
    from ccs_response_planner_backend.agents.information_agent.agent import (
        InformationAgent,
    )

    agent = InformationAgent()
    result = agent.execute_tool("unknown_tool", {})
    assert result["tool_name"] == "unknown_tool"
    assert "error" in result


def test_agent_parse_assessment_fallback() -> None:
    """
    _parse_assessment should fall back gracefully when the
    model output is not valid JSON.
    """
    from ccs_response_planner_backend.agents.information_agent.agent import (
        InformationAgent,
    )

    agent = InformationAgent()
    raw = "This is not valid JSON at all."
    result = agent._parse_assessment(raw)
    assert result["type"] == "assessment"
    a = result["assessment"]
    assert a["incident_summary"] == raw
    assert a["severity"] == "Unknown"
    assert a["attack_vector_analysis"] == ""
    assert a["indicators_of_compromise"] == []
    assert a["affected_assets"] == []


def test_agent_parse_assessment_strips_code_fences() -> None:
    """
    _parse_assessment should strip markdown code fences and
    parse the inner JSON correctly.
    """
    from ccs_response_planner_backend.agents.information_agent.agent import (
        InformationAgent,
    )

    inner = {
        "incident_summary": "Fenced",
        "attack_vector_analysis": "",
        "indicators_of_compromise": [],
        "severity": "Low",
        "severity_justification": "",
        "affected_assets": [],
    }
    fenced = "```json\n" + json.dumps(inner) + "\n```"
    agent = InformationAgent()
    result = agent._parse_assessment(fenced)
    assert result["type"] == "assessment"
    assert result["assessment"]["severity"] == "Low"
    assert result["assessment"]["incident_summary"] == "Fenced"


@patch(
    "ccs_response_planner_backend.agents.information_agent"
    ".agent.genai",
)
def test_agent_step_stream_yields_thinking_events(
    mock_genai: MagicMock,
) -> None:
    """
    InformationAgent.step_stream should yield thinking events
    for thought parts, separate from regular text events.
    """
    from ccs_response_planner_backend.agents.information_agent.agent import (
        InformationAgent,
    )

    thought_part = _make_part(
        text="Let me analyze the alerts", thought=True,
    )
    text_part = _make_part(text="I will search")
    fc_part = _make_part(
        fc_name="tavily_search", fc_args={"query": "test"},
    )

    _mock_client_stream(
        mock_genai,
        [[thought_part], [text_part], [fc_part]],
    )

    agent = InformationAgent()
    events = list(agent.step_stream(
        system_description="test",
        security_alerts="alerts",
        operator_feedback="",
        conversation_history=[],
    ))
    assert len(events) == 3
    assert events[0] == {
        "type": "thinking",
        "delta": "Let me analyze the alerts",
    }
    assert events[1] == {
        "type": "text", "delta": "I will search",
    }
    assert events[2]["type"] == "tool_proposal"
    assert events[2]["rationale"] == "I will search"
    assert events[2]["thinking_trace"] == (
        "Let me analyze the alerts"
    )


def test_serialize_part_with_thought_signature() -> None:
    """
    _serialize_part should store thought_signature as base64
    when present on the part.
    """
    from ccs_response_planner_backend.agents.information_agent.agent import (
        InformationAgent,
    )

    sig_bytes = b"\x01\x02\x03\x04"
    part = _make_part(
        text="thinking", thought=True,
        thought_signature=sig_bytes,
    )

    serialized = InformationAgent._serialize_part(part)
    assert serialized["text"] == "thinking"
    assert serialized["thought"] is True
    assert serialized["thought_signature"] == base64.b64encode(
        sig_bytes,
    ).decode("ascii")


def test_serialize_part_without_thought_signature() -> None:
    """
    _serialize_part should handle parts with thought=True
    but no thought_signature.
    """
    from ccs_response_planner_backend.agents.information_agent.agent import (
        InformationAgent,
    )

    part = _make_part(text="hello", thought=True)

    serialized = InformationAgent._serialize_part(part)
    assert serialized["text"] == "hello"
    assert serialized["thought"] is True
    assert "thought_signature" not in serialized


def test_decode_raw_parts_with_thought_signature() -> None:
    """
    _decode_raw_parts should decode base64 thought_signature back
    to bytes and preserve thought flag.
    """
    from ccs_response_planner_backend.agents.information_agent.agent import (
        InformationAgent,
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
    decoded = InformationAgent._decode_raw_parts(raw)
    assert decoded[0]["text"] == "hello"
    assert decoded[0]["thought"] is True
    assert decoded[0]["thought_signature"] == sig_bytes
    assert decoded[1] == {
        "function_call": {"name": "test", "args": {}},
    }


@patch(
    "ccs_response_planner_backend.agents.information_agent"
    ".agent.genai",
)
def test_agent_step_includes_thinking_trace(
    mock_genai: MagicMock,
) -> None:
    """
    InformationAgent.step should include thinking_trace in the
    returned event when thought parts are present.
    """
    from ccs_response_planner_backend.agents.information_agent.agent import (
        InformationAgent,
    )

    thought_part = _make_part(
        text="Analyzing...", thought=True,
    )
    fc_part = _make_part(
        fc_name="tavily_search", fc_args={"query": "test"},
    )

    _mock_client_generate(
        mock_genai, [thought_part, fc_part],
    )

    agent = InformationAgent()
    result = agent.step(
        system_description="test",
        security_alerts="alerts",
        operator_feedback="",
        conversation_history=[],
    )
    assert result["type"] == "tool_proposal"
    assert result["thinking_trace"] == "Analyzing..."
