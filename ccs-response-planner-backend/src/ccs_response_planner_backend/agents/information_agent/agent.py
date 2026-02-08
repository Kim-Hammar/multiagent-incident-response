"""
InformationAgent — uses Gemini with function calling to gather
incident information and produce a structured assessment.
"""
import json
import os
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

        contents = self._build_contents(conversation_history)
        if not contents:
            contents = [
                {
                    "role": "user",
                    "parts": [{"text": (
                        "Please analyze this incident and "
                        "gather information using the "
                        "available tools."
                    )}],
                },
            ]

        response = model.generate_content(contents)  # type: ignore[arg-type]

        candidate = response.candidates[0]
        parts = candidate.content.parts

        for part in parts:
            fc = part.function_call
            if fc and fc.name:
                tool_args = dict(fc.args) if fc.args else {}
                rationale = ""
                for p in parts:
                    if p.text:
                        rationale = p.text
                        break
                return {
                    "type": "tool_proposal",
                    "tool_name": fc.name,
                    "tool_args": tool_args,
                    "rationale": rationale,
                }

        text_parts = [p.text for p in parts if p.text]
        return {
            "type": "assessment",
            "content": "\n".join(text_parts),
        }

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
        - ``{"type": "assessment", "content": "..."}`` for a final assessment
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

        contents = self._build_contents(conversation_history)
        if not contents:
            contents = [
                {
                    "role": "user",
                    "parts": [{"text": (
                        "Please analyze this incident and "
                        "gather information using the "
                        "available tools."
                    )}],
                },
            ]

        response = model.generate_content(
            contents, stream=True,  # type: ignore[arg-type]
        )

        full_text = ""
        for chunk in response:
            candidate = chunk.candidates[0]
            for part in candidate.content.parts:
                if part.text:
                    full_text += part.text
                    yield {"type": "text", "delta": part.text}

        # After streaming completes, check for function calls
        # in the final aggregated response.
        response.resolve()  # type: ignore[union-attr]
        candidate = response.candidates[0]
        parts = candidate.content.parts

        for part in parts:
            fc = part.function_call
            if fc and fc.name:
                tool_args = dict(fc.args) if fc.args else {}
                rationale = full_text
                yield {
                    "type": "tool_proposal",
                    "tool_name": fc.name,
                    "tool_args": tool_args,
                    "rationale": rationale,
                }
                return

        yield {
            "type": "assessment",
            "content": full_text,
        }

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

    def _build_contents(
        self, history: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Convert conversation history to Gemini Content dicts.

        :param history: the conversation history list
        :return: a list of Gemini-compatible content dicts
        """
        contents: list[dict[str, Any]] = []
        for entry in history:
            entry_type = entry.get("type", "")

            if entry_type == "tool_proposal":
                parts: list[dict[str, Any]] = []
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
                    "parts": [{
                        "function_response": {
                            "name": tool_name,
                            "response": {
                                "result": result_data,
                            },
                        },
                    }],
                })

            elif entry_type == "assessment":
                content = entry.get("content", "")
                contents.append({
                    "role": "model",
                    "parts": [{"text": content}],
                })

        return contents
