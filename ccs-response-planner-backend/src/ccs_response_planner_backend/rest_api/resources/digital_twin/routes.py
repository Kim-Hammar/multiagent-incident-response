"""
Routes and sub-resources for the /digital-twin resource.
"""
import json
from typing import Generator

from flask import Blueprint, Response, jsonify, request

from ccs_response_planner_backend.constants.constants import (
    API,
    DIGITAL_TWIN,
)
from ccs_response_planner_backend.db.database_facade import DatabaseFacade
from ccs_response_planner_backend.docker_manager.docker_manager import (
    DockerManager,
)
from ccs_response_planner_backend.rest_api.util.auth import token_required

digital_twin_bp = Blueprint(
    API.DIGITAL_TWIN_RESOURCE,
    __name__,
    url_prefix=API.DIGITAL_TWIN_ROUTE,
)


@digital_twin_bp.route("", methods=["GET"])
@token_required
def get_digital_twin() -> tuple[Response, int]:
    """
    Load the saved digital twin configuration, or return the default.

    :return: a tuple of (JSON response, HTTP status code)
    """
    config = DatabaseFacade.get_digital_twin_config()
    if config is None:
        config = DIGITAL_TWIN.DEFAULT_CONFIG
    return jsonify(config), 200


@digital_twin_bp.route("", methods=["PUT"])
@token_required
def save_digital_twin() -> tuple[Response, int]:
    """
    Save a digital twin configuration.

    :return: a tuple of (JSON response, HTTP status code)
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body is required"}), 400
    if "networks" not in data or not isinstance(data["networks"], list):
        return jsonify({"error": "networks must be a list"}), 400
    if "hosts" not in data or not isinstance(data["hosts"], list):
        return jsonify({"error": "hosts must be a list"}), 400
    if "links" not in data or not isinstance(data["links"], list):
        return jsonify({"error": "links must be a list"}), 400
    DatabaseFacade.save_digital_twin_config(data)
    return jsonify({"message": "Configuration saved"}), 200


@digital_twin_bp.route("/reset", methods=["POST"])
@token_required
def reset_digital_twin() -> tuple[Response, int]:
    """
    Delete the saved configuration and return the default.

    :return: a tuple of (JSON response, HTTP status code)
    """
    DatabaseFacade.delete_digital_twin_config()
    return jsonify(DIGITAL_TWIN.DEFAULT_CONFIG), 200


@digital_twin_bp.route("/deploy", methods=["POST"])
@token_required
def deploy_digital_twin() -> Response:
    """
    Deploy the digital twin as Docker containers.

    Streams NDJSON progress lines, then a final result line.

    :return: a streaming Response with NDJSON content
    """
    def generate() -> Generator[str, None, None]:
        """
        Yield NDJSON lines as deployment progresses.

        :return: a generator of JSON-encoded strings
        """
        try:
            config = DatabaseFacade.get_digital_twin_config()
            if config is None:
                config = DIGITAL_TWIN.DEFAULT_CONFIG
            for item in DockerManager.deploy(config):
                yield json.dumps(item) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "message": str(e)
                              }) + "\n"

    return Response(generate(), mimetype="application/x-ndjson")


@digital_twin_bp.route("/stop", methods=["POST"])
@token_required
def stop_digital_twin() -> Response:
    """
    Stop and remove all digital twin containers and network.

    Streams NDJSON progress lines, then a final result line.

    :return: a streaming Response with NDJSON content
    """
    def generate() -> Generator[str, None, None]:
        """
        Yield NDJSON lines as stop progresses.

        :return: a generator of JSON-encoded strings
        """
        try:
            for item in DockerManager.stop():
                yield json.dumps(item) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "message": str(e)
                              }) + "\n"

    return Response(generate(), mimetype="application/x-ndjson")


@digital_twin_bp.route("/status", methods=["GET"])
@token_required
def status_digital_twin() -> tuple[Response, int]:
    """
    Get the status of digital twin containers.

    :return: a tuple of (JSON response, HTTP status code)
    """
    try:
        result = DockerManager.status()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@digital_twin_bp.route("/validate", methods=["POST"])
@token_required
def validate_digital_twin() -> Response:
    """
    Run specification commands against the deployed digital twin.

    Streams NDJSON progress lines, result lines, then a done line.

    :return: a streaming Response with NDJSON content
    """
    def generate() -> Generator[str, None, None]:
        """
        Yield NDJSON lines as validation progresses.

        :return: a generator of JSON-encoded strings
        """
        try:
            status = DockerManager.status()
            if not status.get("deployed"):
                yield json.dumps({
                    "type": "error",
                    "message": "Digital twin is not deployed. "
                               "Deploy it first from the Deployment tab.",
                }) + "\n"
                return

            config = DatabaseFacade.get_digital_twin_config()
            if config is None:
                config = DIGITAL_TWIN.DEFAULT_CONFIG
            spec_commands = config.get("specification_commands", [])
            if not spec_commands:
                yield json.dumps({
                    "type": "error",
                    "message": "No specification commands configured.",
                }) + "\n"
                return

            for item in DockerManager.validate(spec_commands):
                yield json.dumps(item) + "\n"
            yield json.dumps({"type": "done"}) + "\n"
        except Exception as e:
            yield json.dumps({
                "type": "error", "message": str(e),
            }) + "\n"

    return Response(generate(), mimetype="application/x-ndjson")
