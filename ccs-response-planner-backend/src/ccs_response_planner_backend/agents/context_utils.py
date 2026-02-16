"""
Shared utilities for compacting tool results before
replaying them into Gemini context windows.
"""
import copy
import json
import logging
import os
from typing import Any, Generator


logger = logging.getLogger(__name__)

_DT_OUTPUT_LIMIT = 3000
_SEARCH_CONTENT_LIMIT = 500
_GENERAL_STRING_LIMIT = 5000


def compact_tool_result(
    tool_name: str, result: Any,
    compact_images: bool = True,
) -> Any:
    """
    Return a compact copy of *result* suitable for the LLM
    context window.  The original dict is never mutated.

    Per-tool rules:

    * ``generate_attack_image`` -- replace the ``image`` field
      with a short placeholder (skipped when *compact_images*
      is ``False`` so the agent can inspect the image on the
      step immediately after generation).
    * ``dt_exec`` / ``dt_python_exec`` -- truncate ``output``
      to 3 000 characters.
    * ``tavily_search`` -- truncate each result's ``content``
      to 500 characters.
    * ``nvd_search`` -- truncate each CVE's ``description``
      to 500 characters.
    * Everything else -- truncate any string value longer than
      5 000 characters.

    :param tool_name: the name of the tool that produced *result*
    :param result: the raw tool result (dict, list, or scalar)
    :param compact_images: whether to strip image data
        (default ``True``; pass ``False`` for the most recent
        tool result so the LLM can still see the image)
    :return: a compacted copy of the result
    """
    if not isinstance(result, dict):
        return result

    result = copy.deepcopy(result)

    _strip_attack_path_images(result)

    if tool_name == "generate_attack_image":
        return _compact_image(result)
    if tool_name in ("dt_exec", "dt_python_exec"):
        return _compact_dt_output(result)
    if tool_name == "tavily_search":
        return _compact_tavily(result)
    if tool_name == "nvd_search":
        return _compact_nvd(result)

    return _compact_general(result)


def _strip_attack_path_images(
    result: dict[str, Any],
) -> None:
    """
    Recursively remove ``attack_path_image`` keys from *result*.

    Attack-path images are large base64 blobs that should never
    appear in the LLM context window.  They are preserved
    separately for UI display.

    :param result: a tool result dict (mutated in place)
    """
    result.pop("attack_path_image", None)
    for val in result.values():
        if isinstance(val, dict):
            _strip_attack_path_images(val)


def _compact_image(result: dict[str, Any]) -> dict[str, Any]:
    """
    Replace the ``image`` field with a placeholder.

    :param result: the generate_attack_image result dict
    :return: the compacted dict
    """
    if "image" in result:
        result["image"] = "(image generated successfully)"
    return result


def _compact_dt_output(
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    Truncate the ``output`` field to *_DT_OUTPUT_LIMIT* chars.

    :param result: the dt_exec / dt_python_exec result dict
    :return: the compacted dict
    """
    output = result.get("output", "")
    if isinstance(output, str) and len(output) > _DT_OUTPUT_LIMIT:
        result["output"] = (
            output[:_DT_OUTPUT_LIMIT] + "\n... (truncated)"
        )
    return result


def _compact_tavily(
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    Truncate each Tavily result's ``content`` field.

    :param result: the tavily_search result dict
    :return: the compacted dict
    """
    for item in result.get("results", []):
        if not isinstance(item, dict):
            continue
        content = item.get("content", "")
        if (
            isinstance(content, str)
            and len(content) > _SEARCH_CONTENT_LIMIT
        ):
            item["content"] = (
                content[:_SEARCH_CONTENT_LIMIT] + "..."
            )
    return result


def _compact_nvd(
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    Truncate each NVD result's ``description`` field.

    :param result: the nvd_search result dict
    :return: the compacted dict
    """
    for item in result.get("results", []):
        if not isinstance(item, dict):
            continue
        desc = item.get("description", "")
        if (
            isinstance(desc, str)
            and len(desc) > _SEARCH_CONTENT_LIMIT
        ):
            item["description"] = (
                desc[:_SEARCH_CONTENT_LIMIT] + "..."
            )
    return result


def _compact_general(
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    Truncate any string value exceeding *_GENERAL_STRING_LIMIT*.

    :param result: any tool result dict
    :return: the compacted dict
    """
    for key, value in result.items():
        if (
            isinstance(value, str)
            and len(value) > _GENERAL_STRING_LIMIT
        ):
            result[key] = (
                value[:_GENERAL_STRING_LIMIT]
                + "\n... (truncated)"
            )
    return result


def estimate_tokens(
    conversation_history: list[dict[str, Any]],
) -> int:
    """
    Estimate the token count of a conversation history using
    the ~4 characters per token heuristic.

    :param conversation_history: the conversation history list
    :return: estimated token count
    """
    return len(json.dumps(
        conversation_history, default=str,
    )) // 4


def compact_context(
    entries: list[dict[str, Any]],
    model_name: str,
) -> str:
    """
    Summarize a list of conversation history entries into a
    concise text summary using an LLM.

    :param entries: older history entries to summarize
    :param model_name: the LLM to use for compaction
    :return: a summary string
    """
    formatted_parts: list[str] = []
    for entry in entries:
        entry_type = entry.get("type", "unknown")
        if entry_type == "tool_proposal":
            tool = entry.get("tool_name", "?")
            rationale = entry.get("rationale", "")
            formatted_parts.append(
                f"[Tool Call: {tool}] {rationale}"
            )
        elif entry_type == "tool_result":
            tool = entry.get("tool_name", "?")
            result = entry.get("result", {})
            result_str = json.dumps(
                result, default=str,
            )[:500]
            formatted_parts.append(
                f"[Tool Result: {tool}] {result_str}"
            )
        elif entry_type == "tool_approval":
            tool = entry.get("tool_name", "?")
            approved = entry.get("approved", False)
            formatted_parts.append(
                f"[Tool Approval: {tool}] "
                f"{'approved' if approved else 'denied'}"
            )
        else:
            text = json.dumps(entry, default=str)[:300]
            formatted_parts.append(
                f"[{entry_type}] {text}"
            )

    history_text = "\n".join(formatted_parts)
    prompt = (
        "Summarize the following agent conversation "
        "history concisely. Preserve key findings, "
        "tool results, decisions, and any important "
        "data. Be brief but retain all critical "
        "information needed to continue the "
        "conversation.\n\n"
        f"{history_text}"
    )

    from ccs_response_planner_backend.agents.anthropic_adapter import (
        is_anthropic_model,
    )
    if is_anthropic_model(model_name):
        import anthropic as anthropic_lib
        from anthropic.types import TextBlock as AnthropicTextBlock
        api_key = os.environ.get(
            "ANTHROPIC_API_KEY", "",
        )
        anth_client = anthropic_lib.Anthropic(
            api_key=api_key,
        )
        anth_resp = anth_client.messages.create(
            model=model_name,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": prompt,
            }],
        )
        block = anth_resp.content[0]
        if isinstance(block, AnthropicTextBlock):
            return block.text
        return ""
    else:
        from google import genai  # type: ignore[attr-defined]
        api_key = os.environ.get(
            "GEMINI_API_KEY", "",
        )
        gem_client: Any = genai.Client(api_key=api_key)
        gem_resp = gem_client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        return gem_resp.text or ""


def maybe_compact_context(
    conversation_history: list[dict[str, Any]],
    context_limit: int,
    threshold: float = 0.8,
    compaction_model: str | None = None,
    agent_model: str | None = None,
    preserve_last_n: int = 2,
) -> Generator[dict[str, Any], None, None]:
    """
    Check whether the conversation history exceeds a token
    threshold and, if so, compact older entries into a summary.

    Mutates *conversation_history* in place when compaction
    fires: replaces all but the last *preserve_last_n* entries
    with a single ``context_summary`` entry.

    :param conversation_history: the conversation history
        (mutated in place on compaction)
    :param context_limit: the model's context window size
    :param threshold: fraction of context_limit that triggers
        compaction (default 0.8)
    :param compaction_model: explicit LLM override for
        compaction; when set, always used
    :param agent_model: the calling agent's own model,
        used as fallback when compaction_model is not set
    :param preserve_last_n: number of recent entries to keep
    :return: yields a context_compaction event if compaction
        fires, otherwise nothing
    """
    estimated = estimate_tokens(conversation_history)
    if estimated < threshold * context_limit:
        return

    model = (
        compaction_model or agent_model or "gemini-2.0-flash"
    )

    if len(conversation_history) <= preserve_last_n:
        return

    older = conversation_history[:-preserve_last_n]
    recent = conversation_history[-preserve_last_n:]

    try:
        summary = compact_context(older, model)
    except Exception as e:
        logger.warning(
            "Context compaction failed: %s", e,
        )
        return

    conversation_history.clear()
    conversation_history.extend(
        [{"type": "context_summary", "summary": summary}]
        + recent
    )

    compacted = estimate_tokens(conversation_history)
    yield {
        "type": "context_compaction",
        "original_tokens": estimated,
        "compacted_tokens": compacted,
        "compaction_model": model,
    }
