"""
Tool dispatch for the ValidationAgent.

Provides a single ``dt_exec`` tool that runs commands on
digital-twin containers to apply response actions and check state.
"""
from typing import Any, Callable

import docker

from ccs_response_planner_backend.constants.constants import DOCKER

_VALID_DT_CONTAINERS = [
    "gateway", "firewall", "ids",
    "server_1", "server_2", "server_3",
    "server_4", "server_5", "server_6",
]


def dt_exec(
    container: str, command: str,
) -> dict[str, Any]:
    """
    Execute a shell command on a digital-twin container.

    :param container: host id (e.g. gateway, server_1)
    :param command: the shell command to run
    :return: a dict with container, command, exit_code, and output
    """
    container_name = f"{DOCKER.CONTAINER_PREFIX}{container}"
    try:
        client = docker.from_env()
        ct = client.containers.get(container_name)
        exec_id = client.api.exec_create(
            ct.id, ["/bin/sh", "-c", command],
            stdout=True, stderr=True,
        )["Id"]
        output = client.api.exec_start(exec_id).decode(
            "utf-8", errors="replace",
        )
        exit_code = client.api.exec_inspect(exec_id)[
            "ExitCode"
        ]
        return {
            "container": container,
            "command": command,
            "exit_code": exit_code,
            "output": output,
        }
    except docker.errors.NotFound:
        return {
            "error": (
                f"Container '{container_name}' not found. "
                f"Valid containers: "
                f"{', '.join(_VALID_DT_CONTAINERS)}"
            ),
        }


TOOL_DISPATCH: dict[str, Callable[..., dict[str, Any]]] = {
    "dt_exec": dt_exec,
}
