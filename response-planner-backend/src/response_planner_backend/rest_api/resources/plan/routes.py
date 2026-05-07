"""
Routes and sub-resources for the /plan resource.
"""
from flask import Blueprint, Response, jsonify, request

from response_planner_backend.constants.constants import API
from response_planner_backend.planner.incident_response_planner import (
    IncidentResponsePlanner,
)
from response_planner_backend.rest_api.util.auth import token_required

plan_bp = Blueprint(
    API.PLAN_RESOURCE, __name__,
    url_prefix=f"{API.PREFIX}/{API.PLAN_RESOURCE}",
)

planner = IncidentResponsePlanner()


@plan_bp.route("", methods=["POST"])
@token_required
def plan() -> tuple[Response, int]:
    """
    Generate an incident response plan.

    :return: a tuple of (JSON response, HTTP status code)
    """
    data = request.get_json(silent=True) or {}
    incident_description = data.get("incident_description", "")
    if not incident_description:
        return jsonify({"error": "incident_description is required"}), 400
    images = data.get("images", [])
    if not isinstance(images, list):
        return jsonify({"error": "images must be a list"}), 400
    specification = data.get("specification", "")
    result = planner.generate_plan(
        incident_description, images=images, specification=specification,
    )
    return jsonify(result), 200
