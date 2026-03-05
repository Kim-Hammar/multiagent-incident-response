"""
Tool dispatch for the CodeVerifierAgent.

Provides ``python_exec`` and ``dt_exec`` tools that run
code in the Python sandbox and digital-twin containers.
"""
import base64
from typing import Any, Callable, Generator

import docker

from ccs_response_planner_backend.agents.shared_tools import (
    dt_exec,
    dt_exec_stream,
    dt_restart,
    dt_restart_stream,
)
from ccs_response_planner_backend.constants.constants import DOCKER


def _ensure_python_sandbox(
    client: docker.DockerClient,
) -> docker.models.containers.Container:
    """
    Ensure the Python sandbox container is running.

    If the container does not exist it is created from the sandbox
    image.  If it exists but is stopped it is started.

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


def python_exec(code: str) -> dict[str, Any]:
    """
    Execute Python code in the sandbox container.

    :param code: the Python source code to run
    :return: a dict with code, exit_code, and output
    """
    client = docker.from_env()
    ct = _ensure_python_sandbox(client)
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
            ct.id, ["/bin/sh", "-c", write_cmd],
            stdout=True, stderr=True,
        )["Id"],
    )
    run_cmd = "python /workspace/_code.py"
    exec_id = client.api.exec_create(
        ct.id, ["/bin/sh", "-c", run_cmd],
        stdout=True, stderr=True,
    )["Id"]
    output = client.api.exec_start(exec_id).decode(
        "utf-8", errors="replace",
    )
    exit_code = client.api.exec_inspect(exec_id)["ExitCode"]
    return {
        "code": code,
        "exit_code": exit_code,
        "output": output,
    }


TOOL_DISPATCH: dict[str, Callable[..., dict[str, Any]]] = {
    "python_exec": python_exec,
    "dt_exec": dt_exec,
    "dt_restart": dt_restart,
}

STREAMING_TOOL_DISPATCH: dict[
    str, Callable[..., Generator[dict[str, Any], None, None]]
] = {
    "dt_exec": dt_exec_stream,
    "dt_restart": dt_restart_stream,
}
