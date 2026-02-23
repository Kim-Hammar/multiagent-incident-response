"""
Routes and sub-resources for the /example and /examples resources.
"""
from flask import Blueprint, Response, jsonify

from ccs_response_planner_backend.constants.constants import (
    API, EXAMPLES, EXAMPLES_2, DIGITAL_TWIN,
)
from ccs_response_planner_backend.db.database_facade import DatabaseFacade
from ccs_response_planner_backend.rest_api.util.auth import token_required

_HOST_TO_ANALYZE_BY_INCIDENT: dict[int, str] = {
    1: EXAMPLES.HOST_TO_ANALYZE,
    2: EXAMPLES_2.HOST_TO_ANALYZE,
}

_ATTACK_PATH_BY_INCIDENT: dict[int, str] = {
    1: EXAMPLES.ATTACK_PATH,
    2: EXAMPLES_2.ATTACK_PATH,
}

example_bp = Blueprint(
    API.EXAMPLE_RESOURCE, __name__,
    url_prefix=f"{API.PREFIX}/{API.EXAMPLE_RESOURCE}",
)

examples_bp = Blueprint(
    API.EXAMPLES_RESOURCE, __name__,
    url_prefix=API.EXAMPLES_ROUTE,
)


def _spec_commands_for_incident(
    incident_id: int,
) -> list[dict[str, str]]:
    """
    Look up the specification_commands linked to an example incident.

    Falls back to the DEFAULT_CONFIG commands if no DB config exists.

    :param incident_id: the example incident id
    :return: a list of specification command dicts
    """
    config_id = DatabaseFacade.get_config_id_by_incident(
        incident_id,
    )
    if config_id is not None:
        cfg = DatabaseFacade.get_digital_twin_config_by_id(
            config_id,
        )
        if cfg and cfg.get("config"):
            cmds = cfg["config"].get(
                "specification_commands",
            )
            if cmds:
                return list(cmds)
    return list(DIGITAL_TWIN.DEFAULT_CONFIG.get(
        "specification_commands", [],
    ))


@example_bp.route("", methods=["GET"])
@token_required
def example() -> tuple[Response, int]:
    """
    Return example incident data for the response planner form.

    Reads Incident 1 from DB if available, falls back to constants.

    :return: a tuple of (JSON response, HTTP status code)
    """
    incident = DatabaseFacade.get_example_incident(1)
    if incident is not None:
        img = incident.get("system_description_image", "")
        images = [img] if img else []
        return jsonify({
            "system_description": incident["system_description"],
            "security_alerts": incident["security_alerts"],
            "operator_feedback": incident["operator_feedback"],
            "specification": incident["specification"],
            "specification_commands": (
                _spec_commands_for_incident(incident["id"])
            ),
            "incident_report": incident["incident_report"],
            "response_plan": incident["response_plan"],
            "system_description_images": images,
            "host_to_analyze": _HOST_TO_ANALYZE_BY_INCIDENT.get(
                incident["id"], "",
            ),
            "attack_path": _ATTACK_PATH_BY_INCIDENT.get(
                incident["id"], "",
            ),
        }), 200
    images = (
        [EXAMPLES.SYSTEM_DESCRIPTION_IMAGE]
        if EXAMPLES.SYSTEM_DESCRIPTION_IMAGE
        else []
    )
    return jsonify({
        "system_description": EXAMPLES.SYSTEM_DESCRIPTION,
        "security_alerts": EXAMPLES.SECURITY_ALERTS,
        "operator_feedback": EXAMPLES.OPERATOR_FEEDBACK,
        "specification": EXAMPLES.SPECIFICATION,
        "specification_commands": DIGITAL_TWIN.DEFAULT_CONFIG.get(
            "specification_commands", [],
        ),
        "incident_report": EXAMPLES.INCIDENT_REPORT,
        "response_plan": EXAMPLES.RESPONSE_PLAN,
        "system_description_images": images,
        "host_to_analyze": EXAMPLES.HOST_TO_ANALYZE,
        "attack_path": EXAMPLES.ATTACK_PATH,
    }), 200


@examples_bp.route("", methods=["GET"])
@token_required
def list_examples() -> tuple[Response, int]:
    """
    List all example incidents (id and name only).

    :return: a tuple of (JSON response, HTTP status code)
    """
    incidents = DatabaseFacade.list_example_incidents()
    return jsonify(incidents), 200


@examples_bp.route("/<int:incident_id>", methods=["GET"])
@token_required
def get_example(incident_id: int) -> tuple[Response, int]:
    """
    Get a full example incident by id.

    :param incident_id: the example incident id
    :return: a tuple of (JSON response, HTTP status code)
    """
    incident = DatabaseFacade.get_example_incident(incident_id)
    if incident is None:
        return jsonify({"error": "Example not found"}), 404
    img = incident.get("system_description_image", "")
    images = [img] if img else []
    return jsonify({
        "id": incident["id"],
        "name": incident["name"],
        "system_description": incident["system_description"],
        "security_alerts": incident["security_alerts"],
        "operator_feedback": incident["operator_feedback"],
        "specification": incident["specification"],
        "specification_commands": (
            _spec_commands_for_incident(incident["id"])
        ),
        "incident_report": incident["incident_report"],
        "response_plan": incident["response_plan"],
        "system_description_images": images,
        "host_to_analyze": _HOST_TO_ANALYZE_BY_INCIDENT.get(
            incident["id"], "",
        ),
        "attack_path": _ATTACK_PATH_BY_INCIDENT.get(
            incident["id"], "",
        ),
    }), 200
