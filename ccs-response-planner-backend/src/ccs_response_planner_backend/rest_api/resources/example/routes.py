"""
Routes and sub-resources for the /example resource.
"""
from flask import Blueprint, Response, jsonify

from ccs_response_planner_backend.constants.constants import API, EXAMPLES
from ccs_response_planner_backend.rest_api.util.auth import token_required

example_bp = Blueprint(
    API.EXAMPLE_RESOURCE, __name__,
    url_prefix=f"{API.PREFIX}/{API.EXAMPLE_RESOURCE}",
)


@example_bp.route("", methods=["GET"])
@token_required
def example() -> tuple[Response, int]:
    """
    Return example incident data for the response planner form.

    :return: a tuple of (JSON response, HTTP status code)
    """
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
