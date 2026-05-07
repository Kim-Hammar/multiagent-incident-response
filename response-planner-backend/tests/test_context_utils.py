"""Tests for the context_utils compact_tool_result helper."""
from unittest.mock import patch

from response_planner_backend.agents.context_utils import (
    compact_tool_result,
    estimate_tokens,
    maybe_compact_context,
)


def test_compact_strips_image() -> None:
    """
    generate_attack_image results should have the image field
    replaced with a short placeholder.
    """
    result = {
        "image": "data:image/png;base64," + "A" * 100_000,
        "description": "Attack path",
    }
    compact = compact_tool_result(
        "generate_attack_image", result,
    )
    assert compact["image"] == "(image generated successfully)"
    assert compact["description"] == "Attack path"


def test_compact_strips_image_preserves_original() -> None:
    """
    compact_tool_result must not mutate the original dict.
    """
    original_image = "data:image/png;base64," + "A" * 100
    result = {"image": original_image}
    compact_tool_result("generate_attack_image", result)
    assert result["image"] == original_image


def test_compact_truncates_dt_exec_output() -> None:
    """
    dt_exec output longer than 3000 chars should be truncated.
    """
    long_output = "x" * 10_000
    result = {
        "container": "i1_gateway",
        "command": "cat /var/log/syslog",
        "output": long_output,
        "exit_code": 0,
    }
    compact = compact_tool_result("dt_exec", result)
    assert len(compact["output"]) < 3200
    assert compact["output"].endswith("... (truncated)")
    assert compact["container"] == "i1_gateway"
    assert compact["exit_code"] == 0


def test_compact_truncates_dt_python_exec_output() -> None:
    """
    dt_python_exec output should also be truncated.
    """
    result = {
        "code": "print('x' * 50000)",
        "output": "x" * 10_000,
        "exit_code": 0,
    }
    compact = compact_tool_result("dt_python_exec", result)
    assert len(compact["output"]) < 3200
    assert compact["output"].endswith("... (truncated)")


def test_compact_dt_exec_short_output_unchanged() -> None:
    """
    dt_exec output shorter than 3000 chars passes through.
    """
    result = {
        "container": "i1_server1",
        "command": "whoami",
        "output": "root\n",
        "exit_code": 0,
    }
    compact = compact_tool_result("dt_exec", result)
    assert compact["output"] == "root\n"


def test_compact_truncates_tavily_content() -> None:
    """
    tavily_search results should have content truncated to
    500 chars each.
    """
    result = {
        "query": "CVE-2021-44228",
        "results": [
            {
                "title": "Log4Shell",
                "url": "https://example.com",
                "content": "A" * 2000,
                "score": 0.95,
            },
            {
                "title": "Another",
                "url": "https://example.com/2",
                "content": "Short content",
                "score": 0.8,
            },
        ],
        "response_time": 0.5,
    }
    compact = compact_tool_result("tavily_search", result)
    assert len(compact["results"][0]["content"]) == 503
    assert compact["results"][0]["content"].endswith("...")
    assert compact["results"][0]["title"] == "Log4Shell"
    assert compact["results"][1]["content"] == "Short content"
    assert compact["query"] == "CVE-2021-44228"


def test_compact_truncates_nvd_description() -> None:
    """
    nvd_search results should have description truncated.
    """
    result = {
        "query": "CVE-2021-44228",
        "results": [
            {
                "id": "CVE-2021-44228",
                "description": "D" * 2000,
                "cvss_score": 10.0,
            },
        ],
    }
    compact = compact_tool_result("nvd_search", result)
    assert len(compact["results"][0]["description"]) == 503
    assert compact["results"][0]["description"].endswith("...")
    assert compact["results"][0]["id"] == "CVE-2021-44228"


def test_compact_passthrough_small_results() -> None:
    """
    Small results from any tool should pass through unchanged.
    """
    result = {
        "query": "test",
        "results": [{"title": "ok"}],
    }
    compact = compact_tool_result("mitre_search", result)
    assert compact == result


def test_compact_general_truncates_long_strings() -> None:
    """
    Unknown tools with string values > 5000 chars should be
    truncated by the general fallback.
    """
    result = {
        "data": "Z" * 10_000,
        "short": "ok",
    }
    compact = compact_tool_result("some_future_tool", result)
    assert len(compact["data"]) < 5200
    assert compact["data"].endswith("... (truncated)")
    assert compact["short"] == "ok"


def test_compact_non_dict_passthrough() -> None:
    """
    Non-dict results should pass through unchanged.
    """
    assert compact_tool_result("dt_exec", "plain") == "plain"
    assert compact_tool_result("dt_exec", 42) == 42
    assert compact_tool_result("dt_exec", None) is None


def test_compact_always_strips_image() -> None:
    """
    Image data should always be replaced with a placeholder
    regardless of the compact_images flag.
    """
    big_image = "data:image/png;base64," + "A" * 100_000
    result = {"image": big_image, "description": "Attack path"}
    for flag in (True, False):
        compact = compact_tool_result(
            "generate_attack_image", result,
            compact_images=flag,
        )
        assert compact["image"] == "(image generated successfully)"
        assert compact["description"] == "Attack path"


def test_compact_strips_attack_path_image_nested() -> None:
    """
    attack_path_image keys should be recursively stripped
    from any tool result.
    """
    big_image = "data:image/png;base64," + "B" * 50_000
    result = {
        "assessment": {
            "title": "Report",
            "attack_path_image": big_image,
        },
        "status": "ok",
    }
    compact = compact_tool_result(
        "run_report_agent", result,
    )
    assert "attack_path_image" not in compact["assessment"]
    assert compact["assessment"]["title"] == "Report"
    assert compact["status"] == "ok"


def test_compact_python_exec_strips_code_echo() -> None:
    """
    python_exec results should replace the code echo with a
    placeholder and keep the output intact when short.
    """
    result = {
        "code": "print('hello')\n" * 1000,
        "exit_code": 0,
        "output": "hello\n",
    }
    compact = compact_tool_result("python_exec", result)
    assert compact["code"] == "(see tool call above)"
    assert compact["output"] == "hello\n"
    assert compact["exit_code"] == 0


def test_compact_python_exec_truncates_long_output() -> None:
    """
    python_exec output exceeding 15 000 chars should be
    truncated.
    """
    result = {
        "code": "x = 1",
        "exit_code": 0,
        "output": "Z" * 20_000,
    }
    compact = compact_tool_result("python_exec", result)
    assert len(compact["output"]) < 15_200
    assert compact["output"].endswith("... (truncated)")
    assert compact["code"] == "(see tool call above)"


def test_compact_python_exec_preserves_original() -> None:
    """
    python_exec compaction must not mutate the original dict.
    """
    original_code = "print('hello')\n" * 1000
    result = {
        "code": original_code,
        "exit_code": 0,
        "output": "hello\n",
    }
    compact_tool_result("python_exec", result)
    assert result["code"] == original_code


def test_compact_gym_verify_keeps_checks() -> None:
    """
    gym_verify results should keep the checks list intact.
    """
    result = {
        "valid": True,
        "checks": [
            {"check": "find_env_class", "passed": True},
            {"check": "has_step", "passed": True},
        ],
        "error": None,
    }
    compact = compact_tool_result("gym_verify", result)
    assert compact["valid"] is True
    assert len(compact["checks"]) == 2
    assert compact["checks"][0]["check"] == "find_env_class"


def test_compact_gym_verify_truncates_long_error() -> None:
    """
    gym_verify error tracebacks exceeding 15 000 chars should
    be truncated.
    """
    result = {
        "valid": False,
        "checks": [],
        "error": "Traceback...\n" * 5_000,
    }
    compact = compact_tool_result("gym_verify", result)
    assert len(compact["error"]) < 15_200
    assert compact["error"].endswith("... (truncated)")
    assert compact["checks"] == []


def test_estimate_tokens_empty() -> None:
    """
    An empty conversation history should return near 0.
    """
    result = estimate_tokens([])
    assert result < 5


def test_estimate_tokens_proportional() -> None:
    """
    A larger history should return a proportionally larger
    estimate.
    """
    small = [{"type": "tool_result", "result": "ok"}]
    large = [
        {"type": "tool_result", "result": "x" * 1000}
        for _ in range(10)
    ]
    assert estimate_tokens(large) > estimate_tokens(small)


def test_maybe_compact_below_threshold() -> None:
    """
    When the estimated tokens are below the threshold,
    no event should be yielded and history is unchanged.
    """
    history = [
        {"type": "tool_result", "result": "ok"},
        {"type": "tool_proposal", "tool_name": "t"},
    ]
    original = list(history)
    events = list(maybe_compact_context(
        history,
        context_limit=1_000_000,
        threshold=0.8,
    ))
    assert events == []
    assert history == original


@patch(
    "response_planner_backend.agents"
    ".context_utils.compact_context",
)
def test_maybe_compact_above_threshold(
    mock_compact,
) -> None:
    """
    When the estimated tokens exceed the threshold,
    a context_compaction event should be yielded and
    history should be mutated.
    """
    mock_compact.return_value = "Summary of older entries."
    history = [
        {"type": "tool_proposal", "tool_name": "a"},
        {"type": "tool_result", "result": "res_a"},
        {"type": "tool_proposal", "tool_name": "b"},
        {"type": "tool_result", "result": "res_b"},
    ]
    events = list(maybe_compact_context(
        history,
        context_limit=10,
        threshold=0.01,
    ))
    assert len(events) == 1
    ev = events[0]
    assert ev["type"] == "context_compaction"
    assert "original_tokens" in ev
    assert "compacted_tokens" in ev
    assert "compaction_model" in ev
    assert history[0]["type"] == "context_summary"
    assert history[0]["summary"] == (
        "Summary of older entries."
    )
    mock_compact.assert_called_once()


@patch(
    "response_planner_backend.agents"
    ".context_utils.compact_context",
)
def test_maybe_compact_preserves_recent(
    mock_compact,
) -> None:
    """
    The last N entries should be preserved verbatim
    after compaction.
    """
    mock_compact.return_value = "Summary."
    entry_a = {
        "type": "tool_proposal",
        "tool_name": "old",
    }
    entry_b = {
        "type": "tool_result",
        "result": "old_res",
    }
    entry_c = {
        "type": "tool_proposal",
        "tool_name": "recent1",
    }
    entry_d = {
        "type": "tool_result",
        "result": "recent2",
    }
    history = [entry_a, entry_b, entry_c, entry_d]
    list(maybe_compact_context(
        history,
        context_limit=10,
        threshold=0.01,
        preserve_last_n=2,
    ))
    assert len(history) == 3
    assert history[0]["type"] == "context_summary"
    assert history[1] is entry_c
    assert history[2] is entry_d


def test_maybe_compact_skips_when_real_tokens_below_threshold() -> None:
    """
    When last_prompt_tokens is well below the threshold,
    no compaction should fire even if estimate_tokens()
    would return a huge number.
    """
    history = [
        {"type": "tool_result", "result": "x" * 100_000},
        {"type": "tool_proposal", "tool_name": "t"},
        {"type": "tool_result", "result": "y" * 100_000},
        {"type": "tool_proposal", "tool_name": "u"},
    ]
    original = list(history)
    events = list(maybe_compact_context(
        history,
        context_limit=1_000_000,
        threshold=0.8,
        last_prompt_tokens=1_000,
    ))
    assert events == []
    assert history == original


@patch(
    "response_planner_backend.agents"
    ".context_utils.compact_context",
)
def test_maybe_compact_fires_when_real_tokens_above_threshold(
    mock_compact,
) -> None:
    """
    When last_prompt_tokens exceeds the threshold,
    compaction should fire.
    """
    mock_compact.return_value = "Summary."
    history = [
        {"type": "tool_proposal", "tool_name": "a"},
        {"type": "tool_result", "result": "res_a"},
        {"type": "tool_proposal", "tool_name": "b"},
        {"type": "tool_result", "result": "res_b"},
    ]
    events = list(maybe_compact_context(
        history,
        context_limit=1_000_000,
        threshold=0.8,
        last_prompt_tokens=900_000,
    ))
    assert len(events) == 1
    assert events[0]["type"] == "context_compaction"
    assert history[0]["type"] == "context_summary"
    mock_compact.assert_called_once()


@patch(
    "response_planner_backend.agents"
    ".context_utils.compact_context",
)
def test_maybe_compact_event_uses_real_tokens(
    mock_compact,
) -> None:
    """
    When last_prompt_tokens is provided, the event should
    report original_tokens equal to last_prompt_tokens and
    compacted_tokens proportionally scaled.
    """
    mock_compact.return_value = "Summary."
    history = [
        {"type": "tool_proposal", "tool_name": "a"},
        {"type": "tool_result", "result": "res_a"},
        {"type": "tool_proposal", "tool_name": "b"},
        {"type": "tool_result", "result": "res_b"},
    ]
    events = list(maybe_compact_context(
        history,
        context_limit=1_000_000,
        threshold=0.8,
        last_prompt_tokens=900_000,
    ))
    ev = events[0]
    assert ev["original_tokens"] == 900_000
    assert ev["compacted_tokens"] < 900_000
    assert isinstance(ev["compacted_tokens"], int)


@patch(
    "response_planner_backend.agents"
    ".context_utils.compact_context",
)
def test_maybe_compact_falls_back_without_real_tokens(
    mock_compact,
) -> None:
    """
    When last_prompt_tokens is 0 (default), the function
    falls back to estimate_tokens() for both the threshold
    check and the event values.
    """
    mock_compact.return_value = "Summary."
    history = [
        {"type": "tool_proposal", "tool_name": "a"},
        {"type": "tool_result", "result": "res_a"},
        {"type": "tool_proposal", "tool_name": "b"},
        {"type": "tool_result", "result": "res_b"},
    ]
    events = list(maybe_compact_context(
        history,
        context_limit=10,
        threshold=0.01,
        last_prompt_tokens=0,
    ))
    assert len(events) == 1
    ev = events[0]
    assert ev["original_tokens"] == estimate_tokens([
        {"type": "tool_proposal", "tool_name": "a"},
        {"type": "tool_result", "result": "res_a"},
        {"type": "tool_proposal", "tool_name": "b"},
        {"type": "tool_result", "result": "res_b"},
    ])
