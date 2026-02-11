"""
Routes and sub-resources for the /agents resource.
"""
import json
from typing import Generator

from flask import Blueprint, Response, g, jsonify, request

from ccs_response_planner_backend.agents.information_agent.agent import (
    InformationAgent,
)
from ccs_response_planner_backend.agents.information_agent.prompt import (
    SYSTEM_PROMPT_TEMPLATE,
)
from ccs_response_planner_backend.agents.information_agent.tools import (
    TOOL_DISPATCH,
)
from ccs_response_planner_backend.agents.penetration_test_agent.agent import (
    PenetrationTestAgent,
)
from ccs_response_planner_backend.agents.penetration_test_agent.prompt import (
    SYSTEM_PROMPT_TEMPLATE as PENTEST_PROMPT_TEMPLATE,
)
from ccs_response_planner_backend.agents.penetration_test_agent.tools import (
    TOOL_DISPATCH as PENTEST_TOOL_DISPATCH,
)
from ccs_response_planner_backend.agents.validation_agent.agent import (
    ValidationAgent,
)
from ccs_response_planner_backend.agents.validation_agent.prompt import (
    SYSTEM_PROMPT_TEMPLATE as VALIDATION_PROMPT_TEMPLATE,
)
from ccs_response_planner_backend.agents.validation_agent.tools import (
    TOOL_DISPATCH as VALIDATION_TOOL_DISPATCH,
)
from ccs_response_planner_backend.constants.constants import API, DIGITAL_TWIN
from ccs_response_planner_backend.db.database_facade import DatabaseFacade
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
    conversation_history = body.get("conversation_history", [])
    images = body.get("images", [])
    model_name = body.get("model_name") or None
    if not isinstance(images, list):
        images = []
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
                conversation_history=conversation_history,
                images=images,
                model_name=model_name,
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


@agents_bp.route("/pentest/step", methods=["POST"])
@token_required
def agents_pentest_step() -> Response | tuple[Response, int]:
    """
    Advance the PenetrationTestAgent loop by one step (NDJSON stream).

    :return: an NDJSON streaming Response, or a (JSON, status) tuple
    """
    body = request.get_json(silent=True) or {}
    system_description = body.get("system_description", "")
    conversation_history = body.get("conversation_history", [])
    images = body.get("images", [])
    model_name = body.get("model_name") or None
    if not isinstance(images, list):
        images = []
    if not system_description:
        return jsonify({
            "error": "system_description is required",
        }), 400

    def generate() -> Generator[str, None, None]:
        """
        Yield NDJSON lines from the agent stream.

        :return: a generator of newline-delimited JSON strings
        """
        try:
            agent = PenetrationTestAgent()
            for event in agent.step_stream(
                system_description=system_description,
                conversation_history=conversation_history,
                images=images,
                model_name=model_name,
            ):
                yield json.dumps(event) + "\n"
        except Exception as e:
            yield json.dumps({
                "type": "error", "message": str(e),
            }) + "\n"

    return Response(generate(), mimetype="application/x-ndjson")


@agents_bp.route("/pentest/prompt", methods=["POST"])
@token_required
def agents_pentest_prompt() -> tuple[Response, int]:
    """
    Render the PenetrationTestAgent system prompt from the given context.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    prompt = PENTEST_PROMPT_TEMPLATE.format(
        system_description=body.get(
            "system_description", "",
        ) or "N/A",
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route("/pentest/tool", methods=["POST"])
@token_required
def agents_pentest_tool() -> tuple[Response, int]:
    """
    Execute an approved tool call for the PenetrationTestAgent.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    tool_name = body.get("tool_name", "")
    tool_args = body.get("tool_args", {})
    if not tool_name:
        return jsonify({"error": "tool_name is required"}), 400
    if tool_name not in PENTEST_TOOL_DISPATCH:
        return jsonify({
            "error": f"Unknown tool: {tool_name}",
        }), 400
    try:
        agent = PenetrationTestAgent()
        result = agent.execute_tool(tool_name, tool_args)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@agents_bp.route("/validation/step", methods=["POST"])
@token_required
def agents_validation_step() -> Response | tuple[Response, int]:
    """
    Advance the ValidationAgent loop by one step (NDJSON stream).

    :return: an NDJSON streaming Response, or a (JSON, status) tuple
    """
    body = request.get_json(silent=True) or {}
    system_description = body.get("system_description", "")
    incident_report = body.get("incident_report", "")
    response_plan = body.get("response_plan", "")
    specification = body.get("specification", "")
    conversation_history = body.get("conversation_history", [])
    images = body.get("images", [])
    model_name = body.get("model_name") or None
    if not isinstance(images, list):
        images = []
    if not system_description and not incident_report:
        return jsonify({
            "error": (
                "system_description or incident_report "
                "is required"
            ),
        }), 400
    if not specification:
        specification = json.dumps(
            DIGITAL_TWIN.DEFAULT_CONFIG[
                "specification_commands"
            ],
            indent=2,
        )

    def generate() -> Generator[str, None, None]:
        """
        Yield NDJSON lines from the agent stream.

        :return: a generator of newline-delimited JSON strings
        """
        try:
            agent = ValidationAgent()
            for event in agent.step_stream(
                system_description=system_description,
                incident_report=incident_report,
                response_plan=response_plan,
                specification=specification,
                conversation_history=conversation_history,
                images=images,
                model_name=model_name,
            ):
                yield json.dumps(event) + "\n"
        except Exception as e:
            yield json.dumps({
                "type": "error", "message": str(e),
            }) + "\n"

    return Response(generate(), mimetype="application/x-ndjson")


@agents_bp.route("/validation/prompt", methods=["POST"])
@token_required
def agents_validation_prompt() -> tuple[Response, int]:
    """
    Render the ValidationAgent system prompt from the given context.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    specification = body.get("specification", "")
    if not specification:
        specification = json.dumps(
            DIGITAL_TWIN.DEFAULT_CONFIG[
                "specification_commands"
            ],
            indent=2,
        )
    prompt = VALIDATION_PROMPT_TEMPLATE.format(
        system_description=body.get(
            "system_description", "",
        ) or "N/A",
        incident_report=body.get(
            "incident_report", "",
        ) or "N/A",
        response_plan=body.get(
            "response_plan", "",
        ) or "N/A",
        specification=specification or "N/A",
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route("/validation/tool", methods=["POST"])
@token_required
def agents_validation_tool() -> tuple[Response, int]:
    """
    Execute an approved tool call for the ValidationAgent.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    tool_name = body.get("tool_name", "")
    tool_args = body.get("tool_args", {})
    if not tool_name:
        return jsonify({"error": "tool_name is required"}), 400
    if tool_name not in VALIDATION_TOOL_DISPATCH:
        return jsonify({
            "error": f"Unknown tool: {tool_name}",
        }), 400
    try:
        agent = ValidationAgent()
        result = agent.execute_tool(tool_name, tool_args)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@agents_bp.route("/reports", methods=["POST"])
@token_required
def save_agent_report() -> tuple[Response, int]:
    """
    Save an agent report to the database.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    agent_type = body.get("agent_type", "")
    report = body.get("report")
    if not agent_type or report is None:
        return jsonify({
            "error": "agent_type and report are required",
        }), 400
    saved = DatabaseFacade.save_agent_report(
        agent_type=agent_type,
        username=g.username,
        report=report,
    )
    return jsonify(saved), 201


@agents_bp.route("/reports", methods=["GET"])
@token_required
def list_agent_reports() -> tuple[Response, int]:
    """
    List agent reports, optionally filtered by agent_type query param.

    :return: a tuple of (JSON response, HTTP status code)
    """
    agent_type = request.args.get("agent_type")
    reports = DatabaseFacade.list_agent_reports(
        agent_type=agent_type,
    )
    return jsonify(reports), 200


@agents_bp.route("/reports/<int:report_id>", methods=["GET"])
@token_required
def get_agent_report(report_id: int) -> tuple[Response, int]:
    """
    Get a single agent report by id.

    :param report_id: the report id
    :return: a tuple of (JSON response, HTTP status code)
    """
    report = DatabaseFacade.get_agent_report(report_id)
    if report is None:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(report), 200


@agents_bp.route("/reports/<int:report_id>", methods=["DELETE"])
@token_required
def delete_agent_report(
    report_id: int,
) -> tuple[Response, int]:
    """
    Delete an agent report by id.

    :param report_id: the report id
    :return: a tuple of (JSON response, HTTP status code)
    """
    deleted = DatabaseFacade.delete_agent_report(report_id)
    if not deleted:
        return jsonify({"error": "Report not found"}), 404
    return jsonify({"deleted": True}), 200
