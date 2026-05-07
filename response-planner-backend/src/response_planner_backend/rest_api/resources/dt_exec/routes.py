"""
Routes and sub-resources for the /dt-exec resource.
"""
from datetime import datetime, timezone

import docker
from flask import Blueprint, Response, jsonify, request

from response_planner_backend.constants.constants import API, DOCKER
from response_planner_backend.rest_api.util.auth import token_required

dt_exec_bp = Blueprint(
    API.DT_EXEC_RESOURCE, __name__,
    url_prefix=f"{API.PREFIX}/{API.DT_EXEC_RESOURCE}",
)


@dt_exec_bp.route("", methods=["GET"])
@token_required
def dt_exec_status() -> tuple[Response, int]:
    """
    Check whether the digital twin is deployed by listing DT containers.

    :return: a tuple of (JSON response, HTTP status code)
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True)
        dt_containers = [
            c.name for c in containers
            if c.name.startswith(DOCKER.CONTAINER_PREFIX)
        ]
        return jsonify({
            "status": "connected",
            "timestamp": timestamp,
            "containers": dt_containers,
            "count": len(dt_containers),
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "timestamp": timestamp,
            "error": str(e),
        }), 200


@dt_exec_bp.route("/run", methods=["POST"])
@token_required
def dt_exec_run() -> tuple[Response, int]:
    """
    Execute a shell command on a digital twin container.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    container_id = body.get("container", "")
    command = body.get("command", "")
    if not container_id or not command:
        return jsonify({
            "error": "container and command are required",
        }), 400
    container_name = f"{DOCKER.CONTAINER_PREFIX}{container_id}"
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
        exec_id = client.api.exec_create(
            container.id, ["/bin/sh", "-c", command],
            stdout=True, stderr=True,
        )["Id"]
        output = client.api.exec_start(exec_id).decode(
            "utf-8", errors="replace",
        )
        exit_code = client.api.exec_inspect(exec_id)["ExitCode"]
        return jsonify({
            "container": container_id,
            "command": command,
            "exit_code": exit_code,
            "output": output,
        }), 200
    except docker.errors.NotFound:
        return jsonify({
            "error": f"Container '{container_name}' not found",
        }), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
