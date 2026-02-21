"""
PlanManagerAgent — uses Gemini with function calling to
orchestrate the full incident response pipeline:
CodeManager -> RlAgent -> ValidationAgent.
"""
import base64
import json
import logging
import os
import re
from typing import Any, Generator

import httpx
from google import genai  # type: ignore[attr-defined]
from google.genai import types as genai_types  # type: ignore[attr-defined]

from ccs_response_planner_backend.agents.stream_timeout import (
    iter_with_idle_timeout,
)
from ccs_response_planner_backend.agents.anthropic_adapter import (
    ANTHROPIC_CONTEXT_LIMIT,
    is_anthropic_model,
    stream_step as anthropic_stream_step,
)
from ccs_response_planner_backend.agents.context_utils import (
    compact_tool_result,
    maybe_compact_context,
)
from ccs_response_planner_backend.agents.plan_manager_agent.prompt import (
    SYSTEM_PROMPT_TEMPLATE,
)
from ccs_response_planner_backend.agents.plan_manager_agent.tool_declarations import (
    ALL_DECLARATIONS,
    ITERATING_DECLARATIONS,
)
from ccs_response_planner_backend.agents.plan_manager_agent.tools import (
    STREAMING_TOOL_DISPATCH,
    TOOL_DISPATCH,
)

logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-3-pro-preview"
CONTEXT_LIMIT = 1_048_576

REPORT_TOOL_NAME = "produce_plan_manager_report"

THINKING_BUDGET = 16384


def _build_initial_message(
    images: list[str] | None = None,
) -> dict[str, Any]:
    """
    Build the initial user message, optionally including images.

    :param images: optional list of base64 data-URL image strings
    :return: a Gemini-compatible content dict
    """
    parts: list[dict[str, Any]] = [{"text": (
        "Please orchestrate the full incident response "
        "pipeline. Start by running the CodeManager to "
        "generate the MDP environment code."
    )}]
    for data_url in (images or []):
        if "," not in data_url:
            continue
        header, b64_data = data_url.split(",", 1)
        mime = (
            header.split(":")[1].split(";")[0]
            if ":" in header else "image/png"
        )
        parts.append({
            "inline_data": {
                "mime_type": mime,
                "data": b64_data,
            },
        })
    return {"role": "user", "parts": parts}


class PlanManagerAgent:
    """
    A top-level orchestrator agent that uses Gemini function
    calling to coordinate CodeManagerAgent, RlAgent, and
    ValidationAgent in an automated pipeline loop.
    """

    def _create_client(self) -> Any:
        """
        Create a Google GenAI client configured with the API key.

        :return: a genai.Client instance
        """
        api_key = os.environ.get("GEMINI_API_KEY", "")
        return genai.Client(api_key=api_key)

    def _make_config(
        self, system_prompt: str,
        declarations: list[Any],
    ) -> Any:
        """
        Build the GenerateContentConfig with tools and thinking.

        :param system_prompt: the rendered system prompt
        :param declarations: the function declarations to expose
        :return: a GenerateContentConfig instance
        """
        return genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[genai_types.Tool(
                function_declarations=declarations,
            )],
            tool_config=genai_types.ToolConfig(
                function_calling_config=(
                    genai_types.FunctionCallingConfig(
                        mode="ANY",  # type: ignore[arg-type]
                    )
                ),
            ),
            thinking_config=genai_types.ThinkingConfig(
                include_thoughts=True,
                thinking_budget=THINKING_BUDGET,
            ),
            automatic_function_calling=(
                genai_types.AutomaticFunctionCallingConfig(
                    disable=True,
                )
            ),
        )

    def step_stream(
        self,
        system_description: str,
        incident_report: str,
        specification: str,
        operator_feedback: str,
        conversation_history: list[dict[str, Any]],
        images: list[str] | None = None,
        model_name: str | None = None,
        max_iterations: int = 2,
        compaction_model: str | None = None,
        compaction_threshold: float = 0.8,
    ) -> Generator[dict[str, Any], None, None]:
        """
        Advance the plan manager agent loop by one step.

        Yields NDJSON-compatible dicts:
        - ``{"type": "thinking", "delta": "..."}``
        - ``{"type": "text", "delta": "..."}``
        - ``{"type": "tool_proposal", ...}``
        - ``{"type": "plan_manager_report", ...}``
        - ``{"type": "error", "message": "..."}``

        :param system_description: description of the target system
        :param incident_report: the incident report/assessment
        :param specification: specification commands as text
        :param operator_feedback: operator feedback or guidance
        :param conversation_history: the full conversation so far
        :param images: optional list of base64 data-URL images
        :param model_name: optional LLM name override
        :param max_iterations: maximum pipeline iterations
        :param compaction_model: optional LLM for compaction
        :param compaction_threshold: context usage fraction that
            triggers compaction (default 0.8)
        :return: a generator of event dicts
        """
        effective_model = model_name or MODEL_NAME

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            system_description=(
                system_description or "N/A"
            ),
            incident_report=(
                incident_report or "N/A"
            ),
            specification=specification or "N/A",
            operator_feedback=(
                operator_feedback or "N/A"
            ),
            max_iterations=max_iterations,
        )

        yield {
            "type": "system_prompt",
            "text": system_prompt,
            "images": list(images or []),
        }

        ctx_limit = (
            ANTHROPIC_CONTEXT_LIMIT
            if is_anthropic_model(effective_model)
            else CONTEXT_LIMIT
        )
        if conversation_history and compaction_threshold > 0:
            for ev in maybe_compact_context(
                conversation_history, ctx_limit,
                threshold=compaction_threshold,
                compaction_model=compaction_model,
                agent_model=effective_model,
                last_prompt_tokens=getattr(
                    self, '_last_prompt_tokens', 0,
                ),
            ):
                yield ev

        declarations = (
            ALL_DECLARATIONS
            if self._has_validated(conversation_history)
            else ITERATING_DECLARATIONS
        )

        if is_anthropic_model(effective_model):
            for ev in anthropic_stream_step(
                system_prompt=system_prompt,
                tool_declarations=declarations,
                history=conversation_history,
                initial_user_parts=[{
                    "type": "text", "text": (
                        "Please orchestrate the full "
                        "incident response pipeline. "
                        "Start by running the "
                        "CodeManager to generate the "
                        "MDP environment code."
                    ),
                }],
                final_tool_name=REPORT_TOOL_NAME,
                final_event_type=(
                    "plan_manager_report"
                ),
                thinking_budget=THINKING_BUDGET,
                images=(
                    images if not conversation_history
                    else None
                ),
                model_name=effective_model,
            ):
                if ev.get("type") == "context_usage":
                    self._last_prompt_tokens = (
                        ev.get("prompt_tokens", 0)
                    )
                yield ev
            return

        client = self._create_client()
        config = self._make_config(
            system_prompt, declarations,
        )

        initial_images = (
            images if not conversation_history else None
        )
        contents = (
            [_build_initial_message(initial_images)]
            + self._build_contents(conversation_history)
        )

        full_text = ""
        thinking_trace = ""
        function_call = None
        all_parts: list[Any] = []
        usage_metadata = None

        _raw_stream = client.models.generate_content_stream(
            model=effective_model,
            contents=contents,
            config=config,
        )
        for chunk in iter_with_idle_timeout(_raw_stream):
            if chunk.usage_metadata:
                usage_metadata = chunk.usage_metadata
            if not chunk.candidates:
                continue
            candidate = chunk.candidates[0]
            if (
                not candidate.content
                or not candidate.content.parts
            ):
                continue
            for part in candidate.content.parts:
                all_parts.append(part)
                if part.text:
                    if part.thought:
                        thinking_trace += part.text
                        yield {
                            "type": "thinking",
                            "delta": part.text,
                        }
                    else:
                        full_text += part.text
                        yield {
                            "type": "text",
                            "delta": part.text,
                        }
                if (
                    part.function_call
                    and part.function_call.name
                ):
                    function_call = part.function_call

        if usage_metadata:
            self._last_prompt_tokens = (
                usage_metadata.prompt_token_count or 0
            )
            yield {
                "type": "context_usage",
                "prompt_tokens": (
                    self._last_prompt_tokens
                ),
                "candidates_tokens": (
                    usage_metadata.candidates_token_count
                    or 0
                ),
                "total_tokens": (
                    usage_metadata.total_token_count
                    or 0
                ),
                "context_limit": ctx_limit,
            }

        raw_parts = [
            d for d in (
                self._serialize_part(p)
                for p in all_parts
            ) if d
        ]

        if function_call:
            if function_call.name == REPORT_TOOL_NAME:
                event: dict[str, Any] = {
                    "type": "plan_manager_report",
                    "plan_manager_report": (
                        self._normalize_args(
                            dict(function_call.args)
                            if function_call.args
                            else {},
                        )
                    ),
                }
                if thinking_trace:
                    event["thinking_trace"] = (
                        thinking_trace
                    )
                yield event
            else:
                tool_args = (
                    dict(function_call.args)
                    if function_call.args else {}
                )
                event = {
                    "type": "tool_proposal",
                    "tool_name": function_call.name,
                    "tool_args": tool_args,
                    "rationale": full_text,
                    "_model_parts": raw_parts,
                }
                if thinking_trace:
                    event["thinking_trace"] = (
                        thinking_trace
                    )
                yield event
        else:
            yield self._parse_plan_manager_report(
                full_text,
            )

    @staticmethod
    def _has_validated(
        history: list[dict[str, Any]],
    ) -> bool:
        """
        Check whether the conversation history contains a
        run_validation_agent tool_result (gates the
        produce_plan_manager_report declaration).

        :param history: the conversation history list
        :return: True if a validation result exists
        """
        for entry in history:
            if (
                entry.get("type") == "tool_result"
                and entry.get("tool_name")
                == "run_validation_agent"
            ):
                return True
        return False

    @staticmethod
    def _normalize_args(obj: Any) -> Any:
        """
        Recursively convert proto MapComposite / RepeatedComposite
        to native Python dicts and lists.

        :param obj: a proto value (scalar, map, or repeated)
        :return: a native Python value
        """
        if isinstance(
            obj, (bool, int, float, str, type(None)),
        ):
            return obj
        if hasattr(obj, "items"):
            return {
                str(k): (
                    PlanManagerAgent._normalize_args(v)
                )
                for k, v in obj.items()
            }
        if hasattr(obj, "__iter__"):
            return [
                PlanManagerAgent._normalize_args(v)
                for v in obj
            ]
        return obj

    def execute_tool(
        self, tool_name: str,
        tool_args: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute an approved (non-streaming) tool call.

        :param tool_name: the name of the tool to execute
        :param tool_args: the arguments to pass to the tool
        :return: a dict with tool_name and result or error
        """
        fn = TOOL_DISPATCH.get(tool_name)
        if fn is None:
            return {
                "tool_name": tool_name,
                "error": f"Unknown tool: {tool_name}",
            }
        try:
            result = fn(**tool_args)
            return {
                "tool_name": tool_name,
                "result": result,
            }
        except Exception as e:
            return {
                "tool_name": tool_name,
                "error": str(e),
            }

    def execute_tool_stream(
        self, tool_name: str,
        tool_args: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """
        Execute a streaming tool call.

        :param tool_name: the name of the streaming tool
        :param tool_args: the arguments to pass to the tool
        :param context: extra context for sub-agent tools
        :return: a generator yielding event dicts
        """
        fn = STREAMING_TOOL_DISPATCH.get(tool_name)
        if fn is None:
            yield {
                "type": "error",
                "message": (
                    "Unknown streaming tool: "
                    f"{tool_name}"
                ),
            }
            return
        try:
            if context is not None:
                yield from fn(
                    context=context, **tool_args,
                )
            else:
                yield from fn(**tool_args)
        except (
            TimeoutError, OSError,
            httpx.TimeoutException,
        ):
            raise
        except Exception as e:
            logger.error(
                "execute_tool_stream(%s) error: "
                "%s: %s",
                tool_name, type(e).__name__, e,
                exc_info=True,
            )
            event: dict[str, Any] = {
                "type": "error",
                "message": str(e),
            }
            if hasattr(e, "to_error_detail"):
                event["errorDetail"] = (
                    e.to_error_detail()
                )
            else:
                event["errorDetail"] = {
                    "message": str(e),
                    "error_type": type(e).__name__,
                }
            yield event

    @staticmethod
    def _serialize_part(part: Any) -> dict[str, Any]:
        """
        Serialize a single Gemini Part to a JSON-safe dict.

        :param part: a Gemini Part object
        :return: a JSON-serializable dict
        """
        d: dict[str, Any] = {}
        if part.text:
            d["text"] = part.text
        fc = part.function_call
        if fc and fc.name:
            d["function_call"] = {
                "name": fc.name,
                "args": (
                    dict(fc.args)
                    if fc.args else {}
                ),
            }
        if getattr(part, "thought", False):
            d["thought"] = True
        sig = getattr(part, "thought_signature", None)
        if sig:
            d["thought_signature"] = (
                base64.b64encode(
                    sig if isinstance(sig, bytes)
                    else sig.encode("utf-8"),
                ).decode("ascii")
            )
        return d

    @staticmethod
    def _decode_raw_parts(
        raw: list[dict[str, Any]],
    ) -> list[Any]:
        """
        Decode serialized parts back to Gemini-compatible dicts.

        :param raw: list of serialized part dicts
        :return: list of dicts for the Gemini API
        """
        parts: list[Any] = []
        for rp in raw:
            if not rp:
                continue
            d: dict[str, Any] = {}
            if "text" in rp:
                d["text"] = rp["text"]
            if rp.get("thought"):
                d["thought"] = True
            sig = rp.get("thought_signature")
            if sig:
                d["thought_signature"] = (
                    base64.b64decode(sig)
                )
            if "function_call" in rp:
                d["function_call"] = rp["function_call"]
            parts.append(d)
        return parts

    def _parse_plan_manager_report(
        self, text: str,
    ) -> dict[str, Any]:
        """
        Parse LLM text into a structured plan manager report.

        :param text: raw text from the LLM
        :return: a dict with type plan_manager_report
        """
        cleaned = re.sub(
            r"^```(?:json)?\s*\n?", "", text.strip(),
        )
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        try:
            parsed = json.loads(cleaned)
            return {
                "type": "plan_manager_report",
                "plan_manager_report": parsed,
            }
        except (json.JSONDecodeError, ValueError):
            return {
                "type": "plan_manager_report",
                "plan_manager_report": {
                    "executive_summary": text,
                    "iterations": 0,
                    "final_verdict": "unknown",
                    "code_manager_summary": "",
                    "rl_agent_summary": "",
                    "validation_summary": "",
                },
            }

    def _build_contents(
        self, history: list[dict[str, Any]],
    ) -> list[Any]:
        """
        Convert conversation history to Gemini Content dicts.

        :param history: the conversation history list
        :return: a list of Gemini-compatible content dicts
        """
        contents: list[Any] = []
        _last_tr_idx = max(
            (i for i, e in enumerate(history)
             if e.get("type") == "tool_result"),
            default=-1,
        )
        for _idx, entry in enumerate(history):
            entry_type = entry.get("type", "")

            if entry_type == "tool_proposal":
                raw = entry.get("_model_parts")
                if raw:
                    parts = self._decode_raw_parts(raw)
                else:
                    parts = []
                    rationale = entry.get(
                        "rationale", "",
                    )
                    if rationale:
                        parts.append({
                            "text": rationale,
                        })
                    tool_name = entry.get(
                        "tool_name", "",
                    )
                    tool_args = entry.get(
                        "tool_args", {},
                    )
                    parts.append({
                        "function_call": {
                            "name": tool_name,
                            "args": tool_args,
                        },
                    })
                contents.append({
                    "role": "model",
                    "parts": parts,
                })

            elif entry_type == "tool_approval":
                approved = entry.get(
                    "approved", False,
                )
                if not approved:
                    tool_name = entry.get(
                        "tool_name", "",
                    )
                    contents.append({
                        "role": "user",
                        "parts": [{
                            "function_response": {
                                "name": tool_name,
                                "response": {
                                    "error": (
                                        "Tool call denied "
                                        "by operator."
                                    ),
                                },
                            },
                        }],
                    })

            elif entry_type == "tool_result":
                tool_name = entry.get(
                    "tool_name", "",
                )
                result = entry.get("result", {})
                compact = compact_tool_result(
                    tool_name, result,
                    preserve_full=(_idx == _last_tr_idx),
                )
                result_data: Any = compact
                if isinstance(compact, dict):
                    result_data = json.dumps(
                        compact, default=str,
                    )
                contents.append({
                    "role": "user",
                    "parts": [
                        {
                            "function_response": {
                                "name": tool_name,
                                "response": {
                                    "result": (
                                        result_data
                                    ),
                                },
                            },
                        },
                        {
                            "text": (
                                "Tool result received. "
                                "Analyze this result, "
                                "then decide the next "
                                "step: run RL agent, "
                                "run validation, revise "
                                "the code, or produce "
                                "the final report."
                            ),
                        },
                    ],
                })

            elif entry_type == "context_summary":
                summary_text = (
                    "Previous conversation summary:\n"
                    + entry.get("summary", "")
                )
                contents.append({
                    "role": "user",
                    "parts": [{"text": summary_text}],
                })

            elif entry_type == "plan_manager_report":
                report = entry.get(
                    "plan_manager_report", {},
                )
                content = json.dumps(
                    report, indent=2,
                )
                contents.append({
                    "role": "model",
                    "parts": [{"text": content}],
                })

        return contents
