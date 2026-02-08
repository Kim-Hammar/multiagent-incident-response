"""
Routes and sub-resources for the /agents resource.
"""
import json
from typing import Generator

from flask import Blueprint, Response, jsonify, request

from ccs_response_planner_backend.agents.information_agent.agent import (
    InformationAgent,
)
from ccs_response_planner_backend.agents.information_agent.prompt import (
    SYSTEM_PROMPT_TEMPLATE,
)
from ccs_response_planner_backend.agents.information_agent.tools import (
    TOOL_DISPATCH,
)
from ccs_response_planner_backend.constants.constants import API
from ccs_response_planner_backend.rest_api.util.auth import token_required

agents_bp = Blueprint(
    API.AGENTS_RESOURCE, __name__,
    url_prefix=f"{API.PREFIX}/{API.AGENTS_RESOURCE}",
)


@agents_bp.route("/information/step", methods=["POST"])
@token_required
def agents_information_step() -> Response | tuple[Response, int]:
    """
    Advance the InformationAgent loop by one step (NDJSON stream).

    :return: an NDJSON streaming Response, or a (JSON, status) tuple
    """
    body = request.get_json(silent=True) or {}
    system_description = body.get("system_description", "")
    security_alerts = body.get("security_alerts", "")
    operator_feedback = body.get("operator_feedback", "")
    recovery_context = body.get("recovery_context", "")
    conversation_history = body.get("conversation_history", [])
    if not system_description and not security_alerts:
        return jsonify({
            "error": (
                "system_description or security_alerts "
                "is required"
            ),
        }), 400

    def generate() -> Generator[str, None, None]:
        """
        Yield NDJSON lines from the agent stream.

        :return: a generator of newline-delimited JSON strings
        """
        try:
            agent = InformationAgent()
            for event in agent.step_stream(
                system_description=system_description,
                security_alerts=security_alerts,
                operator_feedback=operator_feedback,
                recovery_context=recovery_context,
                conversation_history=conversation_history,
            ):
                yield json.dumps(event) + "\n"
        except Exception as e:
            yield json.dumps({
                "type": "error", "message": str(e),
            }) + "\n"

    return Response(generate(), mimetype="application/x-ndjson")


@agents_bp.route("/information/prompt", methods=["POST"])
@token_required
def agents_information_prompt() -> tuple[Response, int]:
    """
    Render the InformationAgent system prompt from the given context.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    prompt = SYSTEM_PROMPT_TEMPLATE.format(
        system_description=body.get(
            "system_description", "",
        ) or "N/A",
        security_alerts=body.get(
            "security_alerts", "",
        ) or "N/A",
        operator_feedback=body.get(
            "operator_feedback", "",
        ) or "N/A",
        recovery_context=body.get(
            "recovery_context", "",
        ) or "N/A",
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route("/information/tool", methods=["POST"])
@token_required
def agents_information_tool() -> tuple[Response, int]:
    """
    Execute an approved tool call for the InformationAgent.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    tool_name = body.get("tool_name", "")
    tool_args = body.get("tool_args", {})
    if not tool_name:
        return jsonify({"error": "tool_name is required"}), 400
    if tool_name not in TOOL_DISPATCH:
        return jsonify({
            "error": f"Unknown tool: {tool_name}",
        }), 400
    try:
        agent = InformationAgent()
        result = agent.execute_tool(tool_name, tool_args)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
