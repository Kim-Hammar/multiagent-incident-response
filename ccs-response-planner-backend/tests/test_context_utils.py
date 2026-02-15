"""Tests for the context_utils compact_tool_result helper."""
from ccs_response_planner_backend.agents.context_utils import (
    compact_tool_result,
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


def test_compact_images_false_preserves_image() -> None:
    """
    When compact_images=False the image data should be
    kept so the agent can inspect it on the next step.
    """
    big_image = "data:image/png;base64," + "A" * 100_000
    result = {"image": big_image, "description": "Attack path"}
    compact = compact_tool_result(
        "generate_attack_image", result,
        compact_images=False,
    )
    assert compact["image"] == big_image
    assert compact["description"] == "Attack path"


def test_compact_images_true_strips_image() -> None:
    """
    When compact_images=True (default) the image data
    should be replaced with a placeholder.
    """
    big_image = "data:image/png;base64," + "A" * 100_000
    result = {"image": big_image}
    compact = compact_tool_result(
        "generate_attack_image", result,
        compact_images=True,
    )
    assert compact["image"] == "(image generated successfully)"
