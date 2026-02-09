"""Tests for the InformationAgent and its standalone tool functions."""
import json
from unittest.mock import MagicMock, patch

from ccs_response_planner_backend.agents.information_agent.tools import (
    TOOL_DISPATCH,
    abuseipdb_check,
    mitre_search,
    nvd_search,
    otx_search,
    tavily_search,
    virustotal_scan,
)


def test_tool_dispatch_has_all_tools() -> None:
    """
    TOOL_DISPATCH must contain all six tool functions.
    """
    expected = {
        "tavily_search",
        "nvd_search",
        "mitre_search",
        "virustotal_scan",
        "abuseipdb_check",
        "otx_search",
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

    mock_fc = MagicMock()
    mock_fc.name = "tavily_search"
    mock_fc.args = {"query": "test"}

    text_part = MagicMock()
    text_part.text = "I will search for test"
    text_part.function_call = MagicMock()
    text_part.function_call.name = ""
    text_part._pb = None
    text_part.thought = False

    fc_part = MagicMock()
    fc_part.text = ""
    fc_part.function_call = mock_fc
    fc_part._pb = None
    fc_part.thought = False

    candidate = MagicMock()
    candidate.content.parts = [text_part, fc_part]

    mock_response = MagicMock()
    mock_response.candidates = [candidate]

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response
    mock_genai.GenerativeModel.return_value = mock_model

    agent = InformationAgent()
    result = agent.step(
        system_description="test system",
        security_alerts="test alerts",
        operator_feedback="",
        recovery_context="",
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
        "recommended_actions": [
            {"priority": 1, "action": "Block IP",
             "type": "immediate"},
        ],
    }
    mock_fc = MagicMock()
    mock_fc.name = "produce_assessment"
    mock_fc.args = assessment_args

    fc_part = MagicMock()
    fc_part.text = ""
    fc_part.function_call = mock_fc
    fc_part._pb = None
    fc_part.thought = False

    candidate = MagicMock()
    candidate.content.parts = [fc_part]

    mock_response = MagicMock()
    mock_response.candidates = [candidate]

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response
    mock_genai.GenerativeModel.return_value = mock_model

    agent = InformationAgent()
    result = agent.step(
        system_description="test system",
        security_alerts="test alerts",
        operator_feedback="",
        recovery_context="",
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

    # Chunk 1: text part
    text_part = MagicMock()
    text_part.text = "I will search"
    text_part.function_call = MagicMock()
    text_part.function_call.name = ""
    text_part._pb = None
    text_part.thought = False

    chunk_1_candidate = MagicMock()
    chunk_1_candidate.content.parts = [text_part]
    chunk_1 = MagicMock()
    chunk_1.candidates = [chunk_1_candidate]

    # Chunk 2: function call part
    mock_fc = MagicMock()
    mock_fc.name = "tavily_search"
    mock_fc.args = {"query": "test"}

    fc_part = MagicMock()
    fc_part.text = ""
    fc_part.function_call = mock_fc
    fc_part._pb = None
    fc_part.thought = False

    chunk_2_candidate = MagicMock()
    chunk_2_candidate.content.parts = [fc_part]
    chunk_2 = MagicMock()
    chunk_2.candidates = [chunk_2_candidate]

    # Aggregated response after streaming
    agg_candidate = MagicMock()
    agg_candidate.content.parts = [text_part, fc_part]

    mock_response = MagicMock()
    mock_response.__iter__ = MagicMock(
        return_value=iter([chunk_1, chunk_2]),
    )
    mock_response.candidates = [agg_candidate]

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response
    mock_genai.GenerativeModel.return_value = mock_model

    agent = InformationAgent()
    events = list(agent.step_stream(
        system_description="test system",
        security_alerts="test alerts",
        operator_feedback="",
        recovery_context="",
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
        "recommended_actions": [],
    }

    # Chunk 1: text rationale
    text_part = MagicMock()
    text_part.text = "Here is the assessment"
    text_part.function_call = MagicMock()
    text_part.function_call.name = ""
    text_part._pb = None
    text_part.thought = False

    chunk_1_candidate = MagicMock()
    chunk_1_candidate.content.parts = [text_part]
    chunk_1 = MagicMock()
    chunk_1.candidates = [chunk_1_candidate]

    # Chunk 2: produce_assessment function call
    mock_fc = MagicMock()
    mock_fc.name = "produce_assessment"
    mock_fc.args = assessment_args

    fc_part = MagicMock()
    fc_part.text = ""
    fc_part.function_call = mock_fc
    fc_part._pb = None
    fc_part.thought = False

    chunk_2_candidate = MagicMock()
    chunk_2_candidate.content.parts = [fc_part]
    chunk_2 = MagicMock()
    chunk_2.candidates = [chunk_2_candidate]

    # Aggregated response
    agg_candidate = MagicMock()
    agg_candidate.content.parts = [text_part, fc_part]

    mock_response = MagicMock()
    mock_response.__iter__ = MagicMock(
        return_value=iter([chunk_1, chunk_2]),
    )
    mock_response.candidates = [agg_candidate]

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response
    mock_genai.GenerativeModel.return_value = mock_model

    agent = InformationAgent()
    events = list(agent.step_stream(
        system_description="test system",
        security_alerts="test alerts",
        operator_feedback="",
        recovery_context="",
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

    text_part = MagicMock()
    text_part.text = "Assessment"
    text_part.function_call = MagicMock()
    text_part.function_call.name = ""
    text_part._pb = None
    text_part.thought = False

    chunk_candidate = MagicMock()
    chunk_candidate.content.parts = [text_part]
    chunk = MagicMock()
    chunk.candidates = [chunk_candidate]

    mock_response = MagicMock()
    mock_response.__iter__ = MagicMock(
        return_value=iter([chunk]),
    )

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response
    mock_genai.GenerativeModel.return_value = mock_model

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
        recovery_context="",
        conversation_history=history,
    ))

    call_args = mock_model.generate_content.call_args
    contents = call_args[0][0]
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
    assert a["recommended_actions"] == []


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
        "recommended_actions": [],
    }
    fenced = "```json\n" + json.dumps(inner) + "\n```"
    agent = InformationAgent()
    result = agent._parse_assessment(fenced)
    assert result["type"] == "assessment"
    assert result["assessment"]["severity"] == "Low"
    assert result["assessment"]["incident_summary"] == "Fenced"


def test_serialize_part_with_pb_stores_proto_binary() -> None:
    """
    _serialize_part should store proto binary via _pb when
    available, and read thought from the raw proto.
    """
    import base64

    from ccs_response_planner_backend.agents.information_agent.agent import (
        InformationAgent,
    )

    proto_bytes = b"\x01\x02\x03\x04"
    mock_pb = MagicMock()
    mock_pb.thought = True
    mock_pb.SerializeToString.return_value = proto_bytes

    part = MagicMock()
    part.text = "thinking"
    part.function_call = MagicMock()
    part.function_call.name = ""
    part._pb = mock_pb

    serialized = InformationAgent._serialize_part(part)
    assert serialized["text"] == "thinking"
    assert serialized["thought"] is True
    assert serialized["_pb"] == base64.b64encode(
        proto_bytes,
    ).decode("ascii")


def test_serialize_part_without_pb_fallback() -> None:
    """
    _serialize_part should fall back to getattr for thought
    when _pb is not available.
    """
    from ccs_response_planner_backend.agents.information_agent.agent import (
        InformationAgent,
    )

    part = MagicMock()
    part.text = "hello"
    part.function_call = MagicMock()
    part.function_call.name = ""
    part._pb = None
    part.thought = True

    serialized = InformationAgent._serialize_part(part)
    assert serialized["text"] == "hello"
    assert serialized["thought"] is True
    assert "_pb" not in serialized


def test_decode_raw_parts_dict_fallback() -> None:
    """
    _decode_raw_parts should return plain dicts when no _pb
    field is present, stripping any stale _pb keys.
    """
    from ccs_response_planner_backend.agents.information_agent.agent import (
        InformationAgent,
    )

    raw = [
        {"text": "hello", "thought": True},
        {"function_call": {"name": "test", "args": {}}},
    ]
    decoded = InformationAgent._decode_raw_parts(raw)
    assert decoded[0] == {"text": "hello", "thought": True}
    assert decoded[1] == {
        "function_call": {"name": "test", "args": {}},
    }
