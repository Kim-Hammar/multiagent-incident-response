"""
Anthropic Claude adapter — provides streaming tool-calling that
mirrors the Gemini agent pattern so each agent can branch to
Claude with minimal changes.
"""
import json
import os
import uuid
from typing import Any, Generator

import anthropic
import httpx

from ccs_response_planner_backend.agents.context_utils import (
    compact_tool_result,
)

ANTHROPIC_CONTEXT_LIMIT = 200_000
ANTHROPIC_MAX_TOKENS = 32768


def is_anthropic_model(model_name: str) -> bool:
    """
    Check whether a model name refers to an Anthropic Claude model.

    :param model_name: the model identifier
    :return: True if the model is a Claude model
    """
    return model_name.lower().startswith("claude")


def list_models(api_key: str) -> list[dict[str, Any]]:
    """
    Fetch available Claude models from the Anthropic API.

    Filters to models that support extended thinking
    (claude-3.5-sonnet and newer).

    :param api_key: the Anthropic API key
    :return: a list of model info dicts
    """
    client = anthropic.Anthropic(api_key=api_key)
    result: list[dict[str, Any]] = []
    page = client.models.list(limit=100)
    for m in page.data:
        model_id = m.id if hasattr(m, "id") else ""
        display = m.display_name if hasattr(
            m, "display_name",
        ) else model_id
        result.append({
            "name": model_id,
            "display_name": display,
            "description": f"Anthropic {display}",
            "input_token_limit": 200_000,
            "output_token_limit": 8192,
        })
    return result


def _schema_to_json_schema(schema: Any) -> dict[str, Any]:
    """
    Recursively convert a Gemini Schema proto/pydantic object
    to a standard JSON Schema dict.

    The Gemini SDK stores type as an enum (e.g. ``Type.OBJECT``)
    and includes many fields that are None. This function
    produces a clean JSON Schema with lowercase type strings.

    :param schema: a genai Schema object or plain dict
    :return: a JSON Schema dict
    """
    if schema is None:
        return {"type": "object", "properties": {}}
    if isinstance(schema, dict):
        return schema

    result: dict[str, Any] = {}

    schema_type = getattr(schema, "type", None)
    if schema_type is not None:
        type_str = str(schema_type)
        if "." in type_str:
            type_str = type_str.split(".")[-1]
        result["type"] = type_str.lower()
    else:
        result["type"] = "object"

    desc = getattr(schema, "description", None)
    if desc:
        result["description"] = desc

    props = getattr(schema, "properties", None)
    if props:
        result["properties"] = {
            k: _schema_to_json_schema(v)
            for k, v in props.items()
        }

    req = getattr(schema, "required", None)
    if req:
        result["required"] = list(req)

    items = getattr(schema, "items", None)
    if items:
        result["items"] = _schema_to_json_schema(items)

    enum = getattr(schema, "enum", None)
    if enum:
        result["enum"] = list(enum)

    return result


def convert_tool_declarations(
    gemini_decls: list[Any],
) -> list[dict[str, Any]]:
    """
    Convert Gemini FunctionDeclaration objects to Anthropic tool
    format.

    Handles the fact that ``decl.parameters`` returns a Gemini
    Schema proto (with enum type values like ``Type.OBJECT``)
    rather than a plain dict.

    :param gemini_decls: list of genai_types.FunctionDeclaration
    :return: list of Anthropic-compatible tool dicts
    """
    tools: list[dict[str, Any]] = []
    for decl in gemini_decls:
        tool: dict[str, Any] = {
            "name": decl.name,
            "description": decl.description or "",
            "input_schema": _schema_to_json_schema(
                decl.parameters,
            ),
        }
        tools.append(tool)
    return tools


def _convert_image(data_url: str) -> dict[str, Any]:
    """
    Convert a data-URL image to Anthropic image source format.

    :param data_url: a base64 data-URL string
    :return: an Anthropic image content block
    """
    if "," not in data_url:
        return {"type": "text", "text": "(invalid image)"}
    header, b64_data = data_url.split(",", 1)
    mime = (
        header.split(":")[1].split(";")[0]
        if ":" in header else "image/png"
    )
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": mime,
            "data": b64_data,
        },
    }


def build_messages(
    history: list[dict[str, Any]],
    initial_user_parts: list[dict[str, Any]],
    final_tool_name: str,
) -> list[dict[str, Any]]:
    """
    Convert vendor-agnostic conversation history to Anthropic
    messages format.

    :param history: the conversation history list
    :param initial_user_parts: content blocks for the first user
        message
    :param final_tool_name: name of the tool that produces the
        final report/assessment (used to detect final outputs)
    :return: a list of Anthropic-compatible message dicts
    """
    messages: list[dict[str, Any]] = []
    messages.append({
        "role": "user",
        "content": initial_user_parts,
    })

    _last_tr_idx = max(
        (i for i, e in enumerate(history)
         if e.get("type") == "tool_result"),
        default=-1,
    )
    for _idx, entry in enumerate(history):
        entry_type = entry.get("type", "")

        if entry_type == "tool_proposal":
            anthropic_content = entry.get(
                "_anthropic_content",
            )
            if anthropic_content:
                messages.append({
                    "role": "assistant",
                    "content": anthropic_content,
                })
            else:
                tool_use_id = entry.get(
                    "_tool_use_id",
                    f"toolu_{uuid.uuid4().hex[:24]}",
                )
                content: list[dict[str, Any]] = []
                rationale = entry.get("rationale", "")
                if rationale:
                    content.append({
                        "type": "text",
                        "text": rationale,
                    })
                content.append({
                    "type": "tool_use",
                    "id": tool_use_id,
                    "name": entry.get("tool_name", ""),
                    "input": entry.get("tool_args", {}),
                })
                messages.append({
                    "role": "assistant",
                    "content": content,
                })

        elif entry_type == "tool_approval":
            approved = entry.get("approved", False)
            if not approved:
                tool_use_id = _find_tool_use_id(
                    messages, entry.get("tool_name", ""),
                )
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": "Tool call denied by "
                        "operator.",
                        "is_error": True,
                    }],
                })

        elif entry_type == "tool_result":
            tool_name = entry.get("tool_name", "")
            tool_use_id = _find_tool_use_id(
                messages, tool_name,
            )
            result = entry.get("result", {})
            compact = compact_tool_result(
                tool_name, result,
                preserve_full=(_idx == _last_tr_idx),
            )
            if isinstance(compact, dict):
                result_str = json.dumps(
                    compact, default=str,
                )
            else:
                result_str = str(compact)
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result_str,
                }],
            })

        elif entry_type == "context_summary":
            messages.append({
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": (
                        "Previous conversation "
                        "summary:\n"
                        + entry.get("summary", "")
                    ),
                }],
            })

        elif entry_type in (
            "assessment", "report",
            "validation_report", "code_report",
            "review_report", "planner_report",
        ):
            data = entry.get(entry_type, {})
            messages.append({
                "role": "assistant",
                "content": [{
                    "type": "text",
                    "text": json.dumps(data, indent=2),
                }],
            })

    return messages


def _find_tool_use_id(
    messages: list[dict[str, Any]],
    tool_name: str,
) -> str:
    """
    Find the tool_use_id for the most recent tool_use block
    matching the given tool name.

    :param messages: the messages built so far
    :param tool_name: the tool name to look for
    :return: the tool_use_id string
    """
    for msg in reversed(messages):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", [])
        if not isinstance(content, list):
            continue
        for block in reversed(content):
            if (
                isinstance(block, dict)
                and block.get("type") == "tool_use"
                and block.get("name") == tool_name
            ):
                result: str = block.get(
                    "id",
                    f"toolu_{uuid.uuid4().hex[:24]}",
                )
                return result
    return f"toolu_{uuid.uuid4().hex[:24]}"


def stream_step(
    system_prompt: str,
    tool_declarations: list[Any],
    history: list[dict[str, Any]],
    initial_user_parts: list[dict[str, Any]],
    final_tool_name: str,
    final_event_type: str,
    thinking_budget: int = 8192,
    images: list[str] | None = None,
    model_name: str = "claude-sonnet-4-5-20250929",
) -> Generator[dict[str, Any], None, None]:
    """
    Stream one agent step via the Anthropic API.

    Yields NDJSON-compatible dicts matching the same event types
    as the Gemini streaming path.

    :param system_prompt: the system instruction text
    :param tool_declarations: Gemini FunctionDeclaration objects
    :param history: the conversation history
    :param initial_user_parts: content blocks for the first user
        message
    :param final_tool_name: name of the final report/assessment
        tool
    :param final_event_type: event type for the final output
        (e.g. "assessment", "report")
    :param thinking_budget: token budget for extended thinking
    :param images: optional list of base64 data-URL images
    :param model_name: the Claude model to use
    :return: a generator of event dicts
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    client = anthropic.Anthropic(
        api_key=api_key,
        timeout=httpx.Timeout(
            connect=30.0, read=300.0,
            write=30.0, pool=30.0,
        ),
    )

    tools = convert_tool_declarations(tool_declarations)
    user_content = list(initial_user_parts)
    for img in (images or []):
        user_content.append(_convert_image(img))

    msgs = build_messages(
        history, user_content, final_tool_name,
    )

    full_text = ""
    thinking_trace = ""
    tool_use_blocks: list[dict[str, Any]] = []
    anthropic_content: list[dict[str, Any]] = []
    input_tokens = 0
    output_tokens = 0

    with client.messages.stream(
        model=model_name,
        max_tokens=ANTHROPIC_MAX_TOKENS,
        system=system_prompt,
        messages=msgs,  # type: ignore[arg-type]
        tools=tools,  # type: ignore[arg-type]
        tool_choice={"type": "auto"},
        thinking={
            "type": "enabled",
            "budget_tokens": thinking_budget,
        },
    ) as stream:
        for event in stream:
            if event.type == "content_block_start":
                block = event.content_block
                if block.type == "thinking":
                    anthropic_content.append({
                        "type": "thinking",
                        "thinking": "",
                    })
                elif block.type == "text":
                    anthropic_content.append({
                        "type": "text",
                        "text": "",
                    })
                elif block.type == "tool_use":
                    anthropic_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": {},
                    })
                    tool_use_blocks.append({
                        "id": block.id,
                        "name": block.name,
                        "input_json": "",
                    })
                    yield {
                        "type": "tool_input_started",
                        "tool_name": block.name,
                    }

            elif event.type == "content_block_delta":
                delta = event.delta
                if delta.type == "thinking_delta":
                    thinking_trace += delta.thinking
                    if anthropic_content:
                        anthropic_content[-1][
                            "thinking"
                        ] = (
                            anthropic_content[-1].get(
                                "thinking", "",
                            ) + delta.thinking
                        )
                    yield {
                        "type": "thinking",
                        "delta": delta.thinking,
                    }
                elif delta.type == "text_delta":
                    full_text += delta.text
                    if anthropic_content:
                        anthropic_content[-1][
                            "text"
                        ] = (
                            anthropic_content[-1].get(
                                "text", "",
                            ) + delta.text
                        )
                    yield {
                        "type": "text",
                        "delta": delta.text,
                    }
                elif delta.type == "input_json_delta":
                    if tool_use_blocks:
                        tool_use_blocks[-1][
                            "input_json"
                        ] += delta.partial_json
                    yield {
                        "type": "tool_input_delta",
                        "delta": delta.partial_json,
                    }

            elif event.type == "message_delta":
                usage = getattr(
                    event, "usage", None,
                )
                if usage:
                    output_tokens = getattr(
                        usage, "output_tokens", 0,
                    )

            elif event.type == "message_start":
                msg = getattr(event, "message", None)
                if msg:
                    usage = getattr(msg, "usage", None)
                    if usage:
                        input_tokens = getattr(
                            usage, "input_tokens", 0,
                        )

    for tub in tool_use_blocks:
        try:
            tub["input"] = json.loads(
                tub["input_json"],
            ) if tub["input_json"] else {}
        except json.JSONDecodeError:
            tub["input"] = {}

    for ac in anthropic_content:
        if ac.get("type") == "tool_use":
            for tub in tool_use_blocks:
                if tub["id"] == ac["id"]:
                    ac["input"] = tub["input"]
                    break

    serializable_content = [
        block for block in anthropic_content
        if block.get("type") != "thinking"
    ]

    yield {
        "type": "context_usage",
        "prompt_tokens": input_tokens,
        "candidates_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "context_limit": ANTHROPIC_CONTEXT_LIMIT,
    }

    if tool_use_blocks:
        last_tool = tool_use_blocks[-1]
        tool_name = last_tool["name"]
        tool_args = last_tool["input"]

        if tool_name == final_tool_name:
            event_out: dict[str, Any] = {
                "type": final_event_type,
                final_event_type: tool_args,
            }
            if thinking_trace:
                event_out[
                    "thinking_trace"
                ] = thinking_trace
            yield event_out
        else:
            event_out = {
                "type": "tool_proposal",
                "tool_name": tool_name,
                "tool_args": tool_args,
                "rationale": full_text,
                "_anthropic_content": (
                    serializable_content
                ),
                "_tool_use_id": last_tool["id"],
                "_vendor": "anthropic",
            }
            if thinking_trace:
                event_out[
                    "thinking_trace"
                ] = thinking_trace
            yield event_out
    elif full_text:
        yield {
            "type": "text",
            "delta": "",
            "full_text": full_text,
        }
    elif thinking_trace:
        yield {
            "type": "text",
            "delta": "",
            "full_text": thinking_trace,
        }
