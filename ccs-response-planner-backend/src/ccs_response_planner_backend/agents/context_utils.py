"""
Shared utilities for compacting tool results before
replaying them into Gemini context windows.
"""
import copy
from typing import Any

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

    if tool_name == "generate_attack_image":
        if not compact_images:
            return result
        return _compact_image(result)
    if tool_name in ("dt_exec", "dt_python_exec"):
        return _compact_dt_output(result)
    if tool_name == "tavily_search":
        return _compact_tavily(result)
    if tool_name == "nvd_search":
        return _compact_nvd(result)

    return _compact_general(result)


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
