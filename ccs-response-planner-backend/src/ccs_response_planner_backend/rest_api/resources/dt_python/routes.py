"""
Routes and sub-resources for the /dt-python resource.
"""
import base64
from datetime import datetime, timezone

import docker
from flask import Blueprint, Response, jsonify, request

from ccs_response_planner_backend.constants.constants import API, DOCKER
from ccs_response_planner_backend.rest_api.util.auth import token_required

dt_python_bp = Blueprint(
    API.DT_PYTHON_RESOURCE, __name__,
    url_prefix=f"{API.PREFIX}/{API.DT_PYTHON_RESOURCE}",
)


def _ensure_sandbox(
    client: docker.DockerClient,
) -> docker.models.containers.Container:
    """
    Ensure the Python sandbox container is running.

    If the container does not exist it is created from the sandbox image.
    If it exists but is stopped it is started.

    :param client: a Docker client instance
    :return: the running sandbox container
    """
    try:
        container = client.containers.get(
            DOCKER.PYTHON_SANDBOX_CONTAINER,
        )
        if container.status != "running":
            container.start()
        return container
    except docker.errors.NotFound:
        container = client.containers.run(
            DOCKER.PYTHON_SANDBOX_IMAGE,
            name=DOCKER.PYTHON_SANDBOX_CONTAINER,
            detach=True,
        )
        return container


@dt_python_bp.route("", methods=["GET"])
@token_required
def dt_python_status() -> tuple[Response, int]:
    """
    Check whether the Python sandbox container is running.

    :return: a tuple of (JSON response, HTTP status code)
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        client = docker.from_env()
        container = client.containers.get(
            DOCKER.PYTHON_SANDBOX_CONTAINER,
        )
        return jsonify({
            "status": "connected",
            "timestamp": timestamp,
            "container_status": container.status,
        }), 200
    except docker.errors.NotFound:
        return jsonify({
            "status": "connected",
            "timestamp": timestamp,
            "container_status": "not_found",
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "timestamp": timestamp,
            "error": str(e),
        }), 200


@dt_python_bp.route("/start", methods=["POST"])
@token_required
def dt_python_start() -> tuple[Response, int]:
    """
    Start the Python sandbox container.

    :return: a tuple of (JSON response, HTTP status code)
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        client = docker.from_env()
        _ensure_sandbox(client)
        return jsonify({
            "container_status": "running",
            "timestamp": timestamp,
        }), 200
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": timestamp,
        }), 500


@dt_python_bp.route("/stop", methods=["POST"])
@token_required
def dt_python_stop() -> tuple[Response, int]:
    """
    Stop and remove the Python sandbox container.

    :return: a tuple of (JSON response, HTTP status code)
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        client = docker.from_env()
        container = client.containers.get(
            DOCKER.PYTHON_SANDBOX_CONTAINER,
        )
        if container.status == "running":
            container.stop()
        container.remove()
        return jsonify({
            "container_status": "stopped",
            "timestamp": timestamp,
        }), 200
    except docker.errors.NotFound:
        return jsonify({
            "container_status": "not_found",
            "timestamp": timestamp,
        }), 200
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": timestamp,
        }), 500


@dt_python_bp.route("/run", methods=["POST"])
@token_required
def dt_python_run() -> tuple[Response, int]:
    """
    Execute Python code inside the sandbox container.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    code = body.get("code", "")
    is_test = bool(body.get("test", False))
    if not code:
        return jsonify({
            "error": "code is required",
        }), 400
    try:
        client = docker.from_env()
        container = _ensure_sandbox(client)
        encoded = base64.b64encode(
            code.encode("utf-8"),
        ).decode("ascii")
        write_cmd = (
            f"python3 -c \"import base64; "
            f"open('/workspace/_code.py','wb')"
            f".write(base64.b64decode('{encoded}'))\""
        )
        client.api.exec_start(
            client.api.exec_create(
                container.id, ["/bin/sh", "-c", write_cmd],
                stdout=True, stderr=True,
            )["Id"],
        )
        if is_test:
            run_cmd = "python -m pytest /workspace/_code.py -v"
        else:
            run_cmd = "python /workspace/_code.py"
        exec_id = client.api.exec_create(
            container.id, ["/bin/sh", "-c", run_cmd],
            stdout=True, stderr=True,
        )["Id"]
        output = client.api.exec_start(exec_id).decode(
            "utf-8", errors="replace",
        )
        exit_code = client.api.exec_inspect(exec_id)["ExitCode"]
        return jsonify({
            "exit_code": exit_code,
            "output": output,
            "test": is_test,
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
