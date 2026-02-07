"""
Routes and sub-resources for the /health resource.
"""
from flask import Blueprint, Response, jsonify

from ccs_response_planner_backend.constants.constants import API, GENERAL

health_bp = Blueprint(
    API.HEALTH_RESOURCE, __name__,
    url_prefix=f"{API.PREFIX}/{API.HEALTH_RESOURCE}",
)


@health_bp.route("", methods=["GET"])
def health() -> tuple[Response, int]:
    """
    Health check endpoint.

    :return: a tuple of (JSON response, HTTP status code)
    """
    return jsonify({"status": "ok", "app": GENERAL.APP_NAME}), 200
