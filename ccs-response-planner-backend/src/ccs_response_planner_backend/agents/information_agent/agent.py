"""
InformationAgent — uses Gemini with function calling to gather
incident information and produce a structured assessment.
"""
import base64
import json
import os
import re
from typing import Any, Generator

import google.generativeai as genai  # type: ignore[attr-defined]

from ccs_response_planner_backend.agents.information_agent.prompt import (
    SYSTEM_PROMPT_TEMPLATE,
)
from ccs_response_planner_backend.agents.information_agent.tool_declarations import (
    TOOL_DECLARATIONS,
)
from ccs_response_planner_backend.agents.information_agent.tools import (
    TOOL_DISPATCH,
)

MODEL_NAME = "gemini-3-pro-preview"

INITIAL_USER_MESSAGE: dict[str, Any] = {
    "role": "user",
    "parts": [{"text": (
        "Please analyze this incident. "
        "Use multiple tools to gather "
        "comprehensive information before "
        "producing your final assessment."
    )}],
}

ASSESSMENT_TOOL_NAME = "produce_assessment"

TOOL_CONFIG: dict[str, Any] = {
    "function_calling_config": {"mode": "any"},
}


class InformationAgent:
    """
    An agent that uses Gemini function calling to invoke
    security information tools and produce an incident assessment.
    """

    def step(
        self,
        system_description: str,
        security_alerts: str,
        operator_feedback: str,
        recovery_context: str,
        conversation_history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Advance the agent loop by one step.

        :param system_description: description of the target system
        :param security_alerts: security alert data
        :param operator_feedback: operator notes/feedback
        :param recovery_context: recovery constraints or context
        :param conversation_history: the full conversation so far
        :return: a dict with type tool_proposal or assessment
        """
        api_key = os.environ.get("GEMINI_API_KEY", "")
        genai.configure(api_key=api_key)  # type: ignore[attr-defined]

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            system_description=system_description or "N/A",
            security_alerts=security_alerts or "N/A",
            operator_feedback=operator_feedback or "N/A",
            recovery_context=recovery_context or "N/A",
        )

        model = genai.GenerativeModel(  # type: ignore[attr-defined]
            model_name=MODEL_NAME,
            system_instruction=system_prompt,
            tools=[genai.types.Tool(
                function_declarations=TOOL_DECLARATIONS,
            )],
        )

        contents = (
            [INITIAL_USER_MESSAGE]
            + self._build_contents(conversation_history)
        )

        response = model.generate_content(
            contents,  # type: ignore[arg-type]
            tool_config=TOOL_CONFIG,  # type: ignore[arg-type]
        )

        candidate = response.candidates[0]
        parts = candidate.content.parts

        for part in parts:
            fc = part.function_call
            if fc and fc.name:
                if fc.name == ASSESSMENT_TOOL_NAME:
                    return {
                        "type": "assessment",
                        "assessment": self._normalize_args(
                            dict(fc.args) if fc.args
                            else {},
                        ),
                    }
                tool_args = dict(fc.args) if fc.args else {}
                rationale = ""
                for p in parts:
                    if p.text and not self._is_thought(p):
                        rationale = p.text
                        break
                return {
                    "type": "tool_proposal",
                    "tool_name": fc.name,
                    "tool_args": tool_args,
                    "rationale": rationale,
                    "_model_parts": self._serialize_parts(
                        parts,
                    ),
                }

        text_parts = [
            p.text for p in parts
            if p.text and not self._is_thought(p)
        ]
        return self._parse_assessment("\n".join(text_parts))

    def step_stream(
        self,
        system_description: str,
        security_alerts: str,
        operator_feedback: str,
        recovery_context: str,
        conversation_history: list[dict[str, Any]],
    ) -> Generator[dict[str, Any], None, None]:
        """
        Advance the agent loop by one step, streaming the response.

        Yields NDJSON-compatible dicts:
        - ``{"type": "text", "delta": "..."}`` for incremental text
        - ``{"type": "tool_proposal", ...}`` for a final tool call
        - ``{"type": "assessment", "assessment": {...}}`` for a final assessment
        - ``{"type": "error", "message": "..."}`` on failure

        :param system_description: description of the target system
        :param security_alerts: security alert data
        :param operator_feedback: operator notes/feedback
        :param recovery_context: recovery constraints or context
        :param conversation_history: the full conversation so far
        :return: a generator of event dicts
        """
        api_key = os.environ.get("GEMINI_API_KEY", "")
        genai.configure(api_key=api_key)  # type: ignore[attr-defined]

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            system_description=system_description or "N/A",
            security_alerts=security_alerts or "N/A",
            operator_feedback=operator_feedback or "N/A",
            recovery_context=recovery_context or "N/A",
        )

        model = genai.GenerativeModel(  # type: ignore[attr-defined]
            model_name=MODEL_NAME,
            system_instruction=system_prompt,
            tools=[genai.types.Tool(
                function_declarations=TOOL_DECLARATIONS,
            )],
        )

        contents = (
            [INITIAL_USER_MESSAGE]
            + self._build_contents(conversation_history)
        )

        response = model.generate_content(
            contents,  # type: ignore[arg-type]
            stream=True,
            tool_config=TOOL_CONFIG,  # type: ignore[arg-type]
        )

        full_text = ""
        function_call = None
        for chunk in response:
            candidate = chunk.candidates[0]
            for part in candidate.content.parts:
                if part.text and not self._is_thought(part):
                    full_text += part.text
                    yield {"type": "text", "delta": part.text}
                fc = part.function_call
                if fc and fc.name:
                    function_call = fc

        # Serialize from the aggregated response which has
        # complete Parts including thought_signature fields.
        raw_parts: list[dict[str, Any]] = []
        try:
            agg_parts = response.candidates[0].content.parts
            raw_parts = [
                d for d in (
                    self._serialize_part(p) for p in agg_parts
                ) if d
            ]
        except (AttributeError, IndexError):
            pass

        if function_call:
            if function_call.name == ASSESSMENT_TOOL_NAME:
                yield {
                    "type": "assessment",
                    "assessment": self._normalize_args(
                        dict(function_call.args)
                        if function_call.args else {},
                    ),
                }
            else:
                tool_args = (
                    dict(function_call.args)
                    if function_call.args else {}
                )
                yield {
                    "type": "tool_proposal",
                    "tool_name": function_call.name,
                    "tool_args": tool_args,
                    "rationale": full_text,
                    "_model_parts": raw_parts,
                }
        else:
            yield self._parse_assessment(full_text)

    @staticmethod
    def _is_thought(part: Any) -> bool:
        """
        Check whether a Gemini Part is internal thinking.

        Thought parts contain chain-of-thought reasoning that
        should not be streamed to the user or included in the
        final assessment text.

        :param part: a Gemini Part proto object
        :return: True if the part is a thought part
        """
        thought = getattr(part, "thought", None)
        if thought is not None:
            return bool(thought)
        pb = getattr(part, "_pb", None)
        if pb is not None:
            return bool(getattr(pb, "thought", False))
        return False

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
                str(k): InformationAgent._normalize_args(v)
                for k, v in obj.items()
            }
        if hasattr(obj, "__iter__"):
            return [
                InformationAgent._normalize_args(v)
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

    @staticmethod
    def _serialize_part(part: Any) -> dict[str, Any]:
        """
        Serialize a single Gemini Part proto to a JSON-safe dict.

        Stores the raw protobuf binary (base64-encoded) so that
        thought_signature and all other proto fields are preserved
        exactly for multi-turn replay.

        :param part: a Gemini Part proto object
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
        pb = getattr(part, "_pb", None)
        if pb is not None:
            if getattr(pb, "thought", False):
                d["thought"] = True
            d["_pb"] = base64.b64encode(
                pb.SerializeToString(),
            ).decode("ascii")
        else:
            thought = getattr(part, "thought", False)
            if thought:
                d["thought"] = True
        return d

    def _serialize_parts(
        self, parts: Any,
    ) -> list[dict[str, Any]]:
        """
        Serialize a list of Gemini Part protos.

        :param parts: iterable of Part proto objects
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
        Decode serialized parts back to Gemini-compatible objects.

        When proto binary is available, deserializes to proto-plus
        Part objects that preserve all fields including
        thought_signature. Falls back to plain dicts otherwise.

        :param raw: list of serialized part dicts
        :return: list of Part protos or dicts for the Gemini API
        """
        parts: list[Any] = []
        for rp in raw:
            if not rp:
                continue
            pb_data = rp.get("_pb")
            if pb_data:
                try:
                    proto_part = genai.protos.Part()  # type: ignore
                    proto_part._pb.ParseFromString(
                        base64.b64decode(pb_data),
                    )
                    parts.append(proto_part)
                    continue
                except Exception:
                    pass
            fallback = dict(rp)
            fallback.pop("_pb", None)
            parts.append(fallback)
        return parts

    def _parse_assessment(
        self, text: str,
    ) -> dict[str, Any]:
        """
        Parse LLM text output into a structured assessment event.

        Strips markdown code fences if present, then attempts
        JSON parsing. Falls back to a default shape on failure.

        :param text: raw text from the LLM
        :return: a dict with type assessment and structured fields
        """
        cleaned = re.sub(
            r"^```(?:json)?\s*\n?", "", text.strip(),
        )
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        try:
            parsed = json.loads(cleaned)
            return {"type": "assessment", "assessment": parsed}
        except (json.JSONDecodeError, ValueError):
            return {
                "type": "assessment",
                "assessment": {
                    "incident_summary": text,
                    "attack_vector_analysis": "",
                    "indicators_of_compromise": [],
                    "severity": "Unknown",
                    "severity_justification": "",
                    "affected_assets": [],
                    "recommended_actions": [],
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
                result_data: Any = result
                if isinstance(result, dict):
                    result_data = json.dumps(
                        result, default=str,
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
                                "continue your investigation "
                                "by calling additional tools "
                                "if you need more information."
                                " Only produce the final JSON "
                                "assessment when you have "
                                "gathered enough evidence from "
                                "multiple sources."
                            ),
                        },
                    ],
                })

            elif entry_type == "assessment":
                assessment = entry.get("assessment", {})
                content = json.dumps(assessment, indent=2)
                contents.append({
                    "role": "model",
                    "parts": [{"text": content}],
                })

        return contents
