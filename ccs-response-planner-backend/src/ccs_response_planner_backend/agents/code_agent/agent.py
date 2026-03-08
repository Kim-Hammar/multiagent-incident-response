"""
CodeAgent — uses Gemini with function calling to generate
a Gymnasium MDP environment for incident response recovery.
"""
import base64
import json
import os
import re
from typing import Any, Generator

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
from ccs_response_planner_backend.agents.dt_prompt_utils import (
    DT_DISABLED_NOTICE,
    filter_dt_declarations,
    format_container_list,
    format_dt_attacker_note,
)
from ccs_response_planner_backend.agents.incident_context import (
    build_incident_context_section,
)
from ccs_response_planner_backend.agents.code_agent.prompt import (
    build_system_prompt,
)
from ccs_response_planner_backend.agents.code_agent.tool_declarations import (
    ALL_DECLARATIONS,
    ITERATING_DECLARATIONS,
)
from ccs_response_planner_backend.agents.code_agent.tools import (
    STREAMING_TOOL_DISPATCH,
    TOOL_DISPATCH,
)

MODEL_NAME = "gemini-3.1-pro-preview"
CONTEXT_LIMIT = 1_048_576

REPORT_TOOL_NAME = "produce_code_report"


def _build_initial_message(
    images: list[str] | None = None,
) -> dict[str, Any]:
    """
    Build the initial user message, optionally including images.

    :param images: optional list of base64 data-URL image strings
    :return: a Gemini-compatible content dict
    """
    parts: list[dict[str, Any]] = [{"text": (
        "Please generate a Gymnasium MDP environment "
        "for incident response recovery planning based "
        "on the provided system description, incident "
        "report, and specification."
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


THINKING_BUDGET = 16384


class CodeAgent:
    """
    An agent that uses Gemini function calling to generate
    a Gymnasium MDP environment and produce a structured
    code generation report.
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
        dt_config: dict[str, Any] | None = None,
        is_revision: bool = False,
        compaction_model: str | None = None,
        compaction_threshold: float = 0.8,
        dt_enabled: bool = True,
        report_manager_enabled: bool = True,
        security_alerts: str = "",
    ) -> Generator[dict[str, Any], None, None]:
        """
        Advance the agent loop by one step, streaming the response.

        Yields NDJSON-compatible dicts:
        - ``{"type": "thinking", "delta": "..."}`` for thinking
        - ``{"type": "text", "delta": "..."}`` for incremental text
        - ``{"type": "tool_proposal", ...}`` for a final tool call
        - ``{"type": "code_report", ...}`` for a final report
        - ``{"type": "error", "message": "..."}`` on failure

        :param system_description: description of the target system
        :param incident_report: the incident report/assessment
        :param specification: specification commands as text
        :param operator_feedback: operator feedback or guidance
        :param conversation_history: the full conversation so far
        :param images: optional list of base64 data-URL images
        :param model_name: optional LLM name override
        :param dt_config: digital twin configuration dict
        :param is_revision: whether this is a revision iteration
        :param compaction_model: optional LLM for compaction
        :param compaction_threshold: context usage fraction that
            triggers compaction (default 0.8)
        :param dt_enabled: whether the digital twin is enabled
        :param report_manager_enabled: whether the report manager
            produced a structured incident report (default True)
        :param security_alerts: raw security alerts (used when
            report_manager_enabled is False)
        :return: a generator of event dicts
        """
        effective_model = model_name or MODEL_NAME

        if is_revision:
            revision_notice = (
                "**IMPORTANT — REVISION ITERATION.** "
                "This is a revision round. You have been "
                "invoked with the previous iteration's "
                "generated code and the reviewer's feedback. "
                "Your primary goal is to carefully address "
                "the reviewer's findings and improve the "
                "existing code — do NOT start from scratch. "
                "Focus on the specific issues raised in the "
                "feedback while preserving what already works "
                "well. The detailed revision context (previous "
                "code and reviewer feedback) is provided in "
                "the Feedback section below.\n\n"
            )
        else:
            revision_notice = ""

        if dt_enabled:
            cfg = dt_config or {}
            dt_container_list = format_container_list(cfg)
            dt_attacker_note = (
                format_dt_attacker_note(cfg)
            )
        else:
            dt_container_list = DT_DISABLED_NOTICE
            dt_attacker_note = ""

        incident_context_section = (
            build_incident_context_section(
                report_manager_enabled=report_manager_enabled,
                incident_report=incident_report,
                security_alerts=security_alerts,
            )
        )
        system_prompt = build_system_prompt(
            dt_enabled=dt_enabled,
            system_description=system_description or "N/A",
            incident_context_section=(
                incident_context_section
            ),
            specification=specification or "N/A",
            operator_feedback=operator_feedback or "N/A",
            revision_notice=revision_notice,
            dt_container_list=dt_container_list,
            dt_attacker_note=dt_attacker_note,
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

        gym_verify_count = sum(
            1 for e in conversation_history
            if e.get("type") == "tool_result"
            and e.get("tool_name") == "gym_verify"
        )
        declarations = filter_dt_declarations(
            ALL_DECLARATIONS
            if self._gym_verify_passed(conversation_history)
            or gym_verify_count >= 3
            else ITERATING_DECLARATIONS,
            dt_enabled,
        )

        if is_anthropic_model(effective_model):
            for ev in anthropic_stream_step(
                system_prompt=system_prompt,
                tool_declarations=declarations,
                history=conversation_history,
                initial_user_parts=[{
                    "type": "text", "text": (
                        "Please generate a Gymnasium "
                        "MDP environment for incident "
                        "response recovery planning "
                        "based on the provided system "
                        "description, incident report, "
                        "and specification."
                    ),
                }],
                final_tool_name=REPORT_TOOL_NAME,
                final_event_type="code_report",
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
        config = self._make_config(system_prompt, declarations)

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
            if not candidate.content or not candidate.content.parts:
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
                if part.function_call and part.function_call.name:
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
                    usage_metadata.total_token_count or 0
                ),
                "context_limit": ctx_limit,
            }

        raw_parts = [
            d for d in (
                self._serialize_part(p) for p in all_parts
            ) if d
        ]

        if function_call:
            if function_call.name == REPORT_TOOL_NAME:
                event: dict[str, Any] = {
                    "type": "code_report",
                    "code_report": self._normalize_args(
                        dict(function_call.args)
                        if function_call.args else {},
                    ),
                }
                if thinking_trace:
                    event["thinking_trace"] = thinking_trace
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
                    event["thinking_trace"] = thinking_trace
                yield event
        else:
            yield self._parse_code_report(full_text)

    @staticmethod
    def _gym_verify_passed(
        history: list[dict[str, Any]],
    ) -> bool:
        """
        Check whether the conversation history contains a
        passing gym_verify tool result.

        :param history: the conversation history list
        :return: True if gym_verify returned valid=true
        """
        for entry in history:
            if (
                entry.get("type") == "tool_result"
                and entry.get("tool_name") == "gym_verify"
            ):
                result = entry.get("result", {})
                if isinstance(result, dict) and result.get(
                    "valid",
                ):
                    return True
        return False

    @staticmethod
    def _is_thought(part: Any) -> bool:
        """
        Check whether a Gemini Part is internal thinking.

        :param part: a Gemini Part object
        :return: True if the part is a thought part
        """
        return bool(getattr(part, "thought", False))

    @staticmethod
    def _normalize_args(obj: Any) -> Any:
        """
        Recursively convert proto MapComposite / RepeatedComposite
        to native Python dicts and lists.

        :param obj: a proto value (scalar, map, or repeated)
        :return: a native Python value
        """
        if isinstance(obj, (bool, int, float, str, type(None))):
            return obj
        if hasattr(obj, "items"):
            return {
                str(k): CodeAgent._normalize_args(v)
                for k, v in obj.items()
            }
        if hasattr(obj, "__iter__"):
            return [
                CodeAgent._normalize_args(v)
                for v in obj
            ]
        return obj

    def execute_tool(
        self, tool_name: str, tool_args: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute an approved tool call.

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
            return {"tool_name": tool_name, "result": result}
        except Exception as e:
            return {"tool_name": tool_name, "error": str(e)}

    def execute_tool_stream(
        self, tool_name: str, tool_args: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """
        Execute a streaming tool call.

        :param tool_name: the name of the streaming tool
        :param tool_args: the arguments to pass to the tool
        :return: a generator yielding event dicts
        """
        fn = STREAMING_TOOL_DISPATCH.get(tool_name)
        if fn is None:
            yield {
                "type": "error",
                "message": f"Unknown streaming tool: "
                f"{tool_name}",
            }
            return
        try:
            yield from fn(**tool_args)
        except Exception as e:
            yield {
                "type": "error",
                "message": str(e),
            }

    @staticmethod
    def _serialize_part(part: Any) -> dict[str, Any]:
        """
        Serialize a single Gemini Part to a JSON-safe dict.

        Stores thought_signature (base64-encoded) so that all
        proto fields are preserved for multi-turn replay.

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
                "args": dict(fc.args) if fc.args else {},
            }
        if getattr(part, "thought", False):
            d["thought"] = True
        sig = getattr(part, "thought_signature", None)
        if sig:
            d["thought_signature"] = base64.b64encode(
                sig if isinstance(sig, bytes)
                else sig.encode("utf-8"),
            ).decode("ascii")
        return d

    def _serialize_parts(
        self, parts: Any,
    ) -> list[dict[str, Any]]:
        """
        Serialize a list of Gemini Part objects.

        :param parts: iterable of Part objects
        :return: a list of JSON-serializable dicts
        """
        return [
            d for d in (self._serialize_part(p) for p in parts)
            if d
        ]

    @staticmethod
    def _decode_raw_parts(
        raw: list[dict[str, Any]],
    ) -> list[Any]:
        """
        Decode serialized parts back to Gemini-compatible dicts.

        Reconstructs Part-like dicts that the Gemini API accepts,
        preserving thought and thought_signature fields.

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
                d["thought_signature"] = base64.b64decode(sig)
            if "function_call" in rp:
                d["function_call"] = rp["function_call"]
            parts.append(d)
        return parts

    def _parse_code_report(
        self, text: str,
    ) -> dict[str, Any]:
        """
        Parse LLM text output into a structured code report.

        Strips markdown code fences if present, then attempts
        JSON parsing. Falls back to a default shape on failure.

        :param text: raw text from the LLM
        :return: a dict with type code_report and fields
        """
        cleaned = re.sub(
            r"^```(?:json)?\s*\n?", "", text.strip(),
        )
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        try:
            parsed = json.loads(cleaned)
            return {
                "type": "code_report",
                "code_report": parsed,
            }
        except (json.JSONDecodeError, ValueError):
            return {
                "type": "code_report",
                "code_report": {
                    "executive_summary": text,
                    "generated_code": "",
                    "actions": [],
                    "state_description": "",
                    "verification_result": "",
                    "verification_checks": [],
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
                    rationale = entry.get("rationale", "")
                    if rationale:
                        parts.append({"text": rationale})
                    tool_name = entry.get("tool_name", "")
                    tool_args = entry.get("tool_args", {})
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
                approved = entry.get("approved", False)
                if not approved:
                    tool_name = entry.get("tool_name", "")
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
                tool_name = entry.get("tool_name", "")
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
                                    "result": result_data,
                                },
                            },
                        },
                        {
                            "text": (
                                "Tool result received. "
                                "Analyze this result, then "
                                "continue developing and "
                                "testing the Gymnasium "
                                "environment code. Only "
                                "produce the final code "
                                "report after gym_verify "
                                "passes."
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

            elif entry_type == "code_report":
                report = entry.get(
                    "code_report", {},
                )
                content = json.dumps(report, indent=2)
                contents.append({
                    "role": "model",
                    "parts": [{"text": content}],
                })

        return contents
