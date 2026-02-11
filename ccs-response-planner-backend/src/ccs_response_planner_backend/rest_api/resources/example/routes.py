"""
Routes and sub-resources for the /example and /examples resources.
"""
from flask import Blueprint, Response, jsonify

from ccs_response_planner_backend.constants.constants import API, EXAMPLES
from ccs_response_planner_backend.db.database_facade import DatabaseFacade
from ccs_response_planner_backend.rest_api.util.auth import token_required

example_bp = Blueprint(
    API.EXAMPLE_RESOURCE, __name__,
    url_prefix=f"{API.PREFIX}/{API.EXAMPLE_RESOURCE}",
)

examples_bp = Blueprint(
    API.EXAMPLES_RESOURCE, __name__,
    url_prefix=API.EXAMPLES_ROUTE,
)


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
            "incident_report": incident["incident_report"],
            "response_plan": incident["response_plan"],
            "system_description_images": images,
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
        "incident_report": EXAMPLES.INCIDENT_REPORT,
        "response_plan": EXAMPLES.RESPONSE_PLAN,
        "system_description_images": images,
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
        "incident_report": incident["incident_report"],
        "response_plan": incident["response_plan"],
        "system_description_images": images,
    }), 200
