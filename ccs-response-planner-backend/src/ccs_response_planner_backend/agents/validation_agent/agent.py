"""
ValidationAgent — uses Gemini with function calling to validate
a response plan against the deployed digital twin.
"""
import base64
import json
import os
import re
from typing import Any, Generator

from google import genai  # type: ignore[attr-defined]
from google.genai import types as genai_types  # type: ignore[attr-defined]

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
    format_container_list,
    format_container_table,
    format_network_connectivity,
)
from ccs_response_planner_backend.agents.validation_agent.prompt import (
    build_system_prompt,
)
from ccs_response_planner_backend.agents.validation_agent.tool_declarations import (
    TOOL_DECLARATIONS,
    TOOL_DECLARATIONS_WITH_POLICY,
)
from ccs_response_planner_backend.agents.validation_agent.tools import (
    STREAMING_TOOL_DISPATCH,
    TOOL_DISPATCH,
)

MODEL_NAME = "gemini-3-pro-preview"
CONTEXT_LIMIT = 1_048_576

REPORT_TOOL_NAME = "produce_validation_report"


def _build_initial_message(
    images: list[str] | None = None,
    has_policy: bool = False,
) -> dict[str, Any]:
    """
    Build the initial user message, optionally including images.

    :param images: optional list of base64 data-URL image strings
    :param has_policy: True when policy-driven mode is active
    :return: a Gemini-compatible content dict
    """
    if has_policy:
        text = (
            "Please validate the response plan using the "
            "trained RL policy. Start by assessing the "
            "initial digital twin state, then query the "
            "policy for each action."
        )
    else:
        text = (
            "Please validate the response plan by "
            "applying actions sequentially on the "
            "digital twin and checking recovery and "
            "service state after each action."
        )
    parts: list[dict[str, Any]] = [{"text": text}]
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


THINKING_BUDGET = 8192


class ValidationAgent:
    """
    An agent that uses Gemini function calling to validate
    a response plan against the digital twin and produce
    a structured validation report.
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
        declarations: list[Any] | None = None,
    ) -> Any:
        """
        Build the GenerateContentConfig with tools and thinking.

        :param system_prompt: the rendered system prompt
        :param declarations: tool declarations to use
        :return: a GenerateContentConfig instance
        """
        decls = declarations or TOOL_DECLARATIONS
        return genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[genai_types.Tool(
                function_declarations=decls,
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
        )

    @staticmethod
    def _format_code_report(
        report: dict[str, Any],
    ) -> str:
        """
        Format a code agent report into readable text for the
        system prompt.

        :param report: the code report dict
        :return: a formatted string
        """
        sections: list[str] = []
        summary = report.get("executive_summary", "")
        if summary:
            sections.append(
                f"### Executive Summary\n{summary}"
            )
        state_desc = report.get("state_description", "")
        if state_desc:
            sections.append(
                f"### State Description\n{state_desc}"
            )
        actions = report.get("actions", [])
        if actions:
            lines = ["### Actions"]
            for i, a in enumerate(actions):
                name = a.get("name", f"Action {i}")
                desc = a.get("description", "")
                effect = a.get("state_effect", "")
                prob = a.get("success_probability", "")
                cmds = a.get("commands", [])
                lines.append(f"\n**{i}. {name}**")
                if desc:
                    lines.append(f"  Description: {desc}")
                if effect:
                    lines.append(
                        f"  State effect: {effect}"
                    )
                if prob:
                    lines.append(
                        f"  P(success): {prob}"
                    )
                if cmds:
                    for c in cmds:
                        ct = c.get("container", "?")
                        cmd = c.get("command", "?")
                        lines.append(
                            f"  Command: {ct}: {cmd}"
                        )
            sections.append("\n".join(lines))
        verification = report.get(
            "verification_result", "",
        )
        checks = report.get("verification_checks", [])
        if verification or checks:
            lines = ["### Verification"]
            if verification:
                lines.append(verification)
            for c in checks:
                status = (
                    "PASS" if c.get("passed") else "FAIL"
                )
                detail = c.get("detail", "")
                check_name = c.get("check", "?")
                lines.append(
                    f"  [{status}] {check_name}"
                    + (f": {detail}" if detail else "")
                )
            sections.append("\n".join(lines))
        code = report.get("generated_code", "")
        if code:
            sections.append(
                f"### Generated Code\n\n```python\n"
                f"{code}\n```"
            )
        return "\n\n".join(sections) if sections else "N/A"

    @staticmethod
    def _format_planner_report(
        report: dict[str, Any],
    ) -> str:
        """
        Format an RL agent report into readable text for the
        system prompt.

        :param report: the planner report dict
        :return: a formatted string
        """
        sections: list[str] = []
        summary = report.get("executive_summary", "")
        if summary:
            sections.append(
                f"### Executive Summary\n{summary}"
            )
        algorithm = report.get("algorithm", "")
        if algorithm:
            sections.append(
                f"### Algorithm\n{algorithm}"
            )
        training = report.get("training_summary", "")
        if training:
            sections.append(
                f"### Training Summary\n{training}"
            )
        action_seq = report.get("action_sequence", [])
        if action_seq:
            lines = ["### Action Sequence"]
            for i, a in enumerate(action_seq):
                name = a.get("name", f"Action {i}")
                desc = a.get("description", "")
                cmds = a.get("commands", [])
                lines.append(f"\n**{i}. {name}**")
                if desc:
                    lines.append(f"  Description: {desc}")
                if cmds:
                    for c in cmds:
                        ct = c.get("container", "?")
                        cmd = c.get("command", "?")
                        lines.append(
                            f"  Command: {ct}: {cmd}"
                        )
            sections.append("\n".join(lines))
        cost = report.get("expected_total_cost")
        if cost is not None:
            sections.append(
                f"### Expected Total Cost\n{cost}"
            )
        contingencies = report.get("contingencies", [])
        if contingencies:
            lines = ["### Contingencies"]
            for c in contingencies:
                lines.append(f"- {c}")
            sections.append("\n".join(lines))
        risks = report.get("risks", [])
        if risks:
            lines = ["### Risks"]
            for r in risks:
                lines.append(f"- {r}")
            sections.append("\n".join(lines))
        return "\n\n".join(sections) if sections else "N/A"

    @staticmethod
    def _format_validation_feedback(
        report: dict[str, Any],
    ) -> str:
        """
        Format a previous validation report into a concise
        feedback section for the system prompt.

        :param report: the previous validation_report dict
        :return: a formatted string, or empty string if empty
        """
        if not report:
            return ""
        sections: list[str] = [
            "## Previous Validation Feedback\n",
            "A previous validation run was already performed "
            "on an earlier iteration of this response plan. "
            "Use this feedback to focus your validation — "
            "do NOT repeat checks that already passed. "
            "Concentrate on areas that failed or had issues.\n",
        ]
        verdict = report.get(
            "overall_verdict",
            report.get("overall_result", ""),
        )
        if verdict:
            sections.append(
                f"**Previous verdict:** {verdict}\n"
            )
        summary = report.get("executive_summary", "")
        if summary:
            sections.append(
                f"**Summary:** {summary}\n"
            )
        actions = report.get("action_results", [])
        if actions:
            failed = [
                a for a in actions
                if not a.get("success", True)
                or a.get("actual_step_cost", 0) > 10
            ]
            if failed:
                lines = ["**Actions that had issues:**"]
                for a in failed[:10]:
                    name = a.get(
                        "action_name",
                        a.get("name", "?"),
                    )
                    outcome = a.get("outcome", "")
                    lines.append(
                        f"- {name}: {outcome}"
                    )
                sections.append("\n".join(lines) + "\n")
        recs = report.get("recommendations", [])
        if recs:
            lines = ["**Recommendations from previous run:**"]
            for r in recs[:5]:
                lines.append(f"- {r}")
            sections.append("\n".join(lines) + "\n")
        return "\n".join(sections) + "\n"

    def step_stream(
        self,
        system_description: str,
        incident_report: str,
        response_plan: str,
        specification: str,
        planner_report: dict[str, Any],
        code_report: dict[str, Any],
        conversation_history: list[dict[str, Any]],
        images: list[str] | None = None,
        model_name: str | None = None,
        has_policy: bool = False,
        dt_config: dict[str, Any] | None = None,
        validation_feedback: dict[str, Any] | None = None,
        compaction_model: str | None = None,
        compaction_threshold: float = 0.8,
    ) -> Generator[dict[str, Any], None, None]:
        """
        Advance the agent loop by one step, streaming the response.

        Yields NDJSON-compatible dicts:
        - ``{"type": "thinking", "delta": "..."}`` for thinking
        - ``{"type": "text", "delta": "..."}`` for incremental text
        - ``{"type": "tool_proposal", ...}`` for a final tool call
        - ``{"type": "validation_report", ...}`` for a final report
        - ``{"type": "error", "message": "..."}`` on failure

        :param system_description: description of the target system
        :param incident_report: the incident report/assessment
        :param response_plan: the response plan to validate
        :param specification: specification commands as text
        :param planner_report: RL agent report dict
        :param code_report: code agent report dict
        :param conversation_history: the full conversation so far
        :param images: optional list of base64 data-URL images
        :param model_name: optional LLM name override
        :param has_policy: True if RL policy is loaded in sandbox
        :param dt_config: digital twin configuration dict
        :param validation_feedback: previous validation report dict
        :param compaction_model: optional LLM for compaction
        :param compaction_threshold: context usage fraction that
            triggers compaction (default 0.8)
        :return: a generator of event dicts
        """
        effective_model = model_name or MODEL_NAME

        cfg = dt_config or {}
        system_prompt = build_system_prompt(
            has_policy=has_policy,
            system_description=system_description or "N/A",
            incident_report=incident_report or "N/A",
            specification=specification or "N/A",
            planner_report_formatted=(
                self._format_planner_report(
                    planner_report or {},
                )
            ),
            code_report_formatted=(
                self._format_code_report(
                    code_report or {},
                )
            ),
            validation_feedback=(
                self._format_validation_feedback(
                    validation_feedback or {},
                )
            ),
            dt_container_list=format_container_list(cfg),
            dt_container_table=(
                format_container_table(cfg)
            ),
            dt_network_connectivity=(
                format_network_connectivity(cfg)
            ),
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
            ):
                yield ev

        declarations = (
            TOOL_DECLARATIONS_WITH_POLICY
            if has_policy else TOOL_DECLARATIONS
        )

        if is_anthropic_model(effective_model):
            if has_policy:
                initial_text = (
                    "Please validate the response plan "
                    "using the trained RL policy. Start by "
                    "assessing the initial digital twin "
                    "state, then query the policy for "
                    "each action."
                )
            else:
                initial_text = (
                    "Please validate the response plan by "
                    "applying actions sequentially on the "
                    "digital twin and checking recovery and "
                    "service state after each action."
                )
            yield from anthropic_stream_step(
                system_prompt=system_prompt,
                tool_declarations=declarations,
                history=conversation_history,
                initial_user_parts=[{
                    "type": "text", "text": initial_text,
                }],
                final_tool_name=REPORT_TOOL_NAME,
                final_event_type="validation_report",
                thinking_budget=THINKING_BUDGET,
                images=(
                    images if not conversation_history
                    else None
                ),
                model_name=effective_model,
            )
            return

        client = self._create_client()
        config = self._make_config(
            system_prompt,
            declarations=declarations,
        )

        initial_images = (
            images if not conversation_history else None
        )
        contents = (
            [_build_initial_message(
                initial_images, has_policy,
            )]
            + self._build_contents(
                conversation_history, has_policy,
            )
        )

        full_text = ""
        thinking_trace = ""
        function_call = None
        all_parts: list[Any] = []
        usage_metadata = None

        for chunk in client.models.generate_content_stream(
            model=effective_model,
            contents=contents,
            config=config,
        ):
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
            yield {
                "type": "context_usage",
                "prompt_tokens": (
                    usage_metadata.prompt_token_count or 0
                ),
                "candidates_tokens": (
                    usage_metadata.candidates_token_count or 0
                ),
                "total_tokens": (
                    usage_metadata.total_token_count or 0
                ),
                "context_limit": CONTEXT_LIMIT,
            }

        raw_parts = [
            d for d in (
                self._serialize_part(p) for p in all_parts
            ) if d
        ]

        if function_call:
            if function_call.name == REPORT_TOOL_NAME:
                event: dict[str, Any] = {
                    "type": "validation_report",
                    "validation_report": self._normalize_args(
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
            yield self._parse_validation_report(full_text)

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
                str(k): ValidationAgent._normalize_args(v)
                for k, v in obj.items()
            }
        if hasattr(obj, "__iter__"):
            return [
                ValidationAgent._normalize_args(v)
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

    def _parse_validation_report(
        self, text: str,
    ) -> dict[str, Any]:
        """
        Parse LLM text output into a structured validation report.

        Strips markdown code fences if present, then attempts
        JSON parsing. Falls back to a default shape on failure.

        :param text: raw text from the LLM
        :return: a dict with type validation_report and fields
        """
        cleaned = re.sub(
            r"^```(?:json)?\s*\n?", "", text.strip(),
        )
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        try:
            parsed = json.loads(cleaned)
            return {
                "type": "validation_report",
                "validation_report": parsed,
            }
        except (json.JSONDecodeError, ValueError):
            return {
                "type": "validation_report",
                "validation_report": {
                    "executive_summary": text,
                    "action_results": [],
                    "final_recovery_state": {
                        "is_attack_contained": False,
                        "is_attack_assessed": False,
                        "is_forensic_evidence_preserved": False,
                        "is_attack_evicted": False,
                        "is_system_hardened": False,
                        "are_services_restored": False,
                    },
                    "final_service_state": [],
                    "overall_result": "Plan validation failed",
                    "recommendations": [],
                    "actual_total_cost": 0,
                    "simulated_total_cost": 0,
                },
            }

    def _build_contents(
        self, history: list[dict[str, Any]],
        has_policy: bool = False,
    ) -> list[Any]:
        """
        Convert conversation history to Gemini Content dicts.

        :param history: the conversation history list
        :param has_policy: True if policy-driven mode is active
        :return: a list of Gemini-compatible content dicts
        """
        if has_policy:
            nudge = (
                "Tool result received. "
                "Analyze this result, then reassess "
                "the state and query the policy for "
                "the next action. Only produce the "
                "final validation report when all "
                "recovery phases >= 0.9 or 30 actions "
                "have been applied."
            )
        else:
            nudge = (
                "Tool result received. "
                "Analyze this result, then "
                "continue applying response "
                "actions and checking state."
                " Only produce the final "
                "validation report when you "
                "have applied all actions "
                "and checked all states."
            )

        contents: list[Any] = []
        for entry in history:
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
                        {"text": nudge},
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

            elif entry_type == "validation_report":
                report = entry.get(
                    "validation_report", {},
                )
                content = json.dumps(report, indent=2)
                contents.append({
                    "role": "model",
                    "parts": [{"text": content}],
                })

        return contents
