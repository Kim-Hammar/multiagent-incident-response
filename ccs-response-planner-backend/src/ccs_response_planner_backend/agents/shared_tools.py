"""
Shared tool functions used by multiple agents.

Provides ``dt_exec`` with automatic digital-twin deployment so
that agents do not fail when the DT containers are not yet running.
"""
import logging
from typing import Any

import docker

from ccs_response_planner_backend.constants.constants import DOCKER
from ccs_response_planner_backend.docker_manager.docker_manager \
    import DockerManager

logger = logging.getLogger(__name__)

_VALID_DT_CONTAINERS = [
    "gateway", "firewall", "ids",
    "server_1", "server_2", "server_3",
    "server_4", "server_5", "server_6",
]


def _exec_on_container(
    container: str, command: str,
) -> dict[str, Any]:
    """
    Run a shell command on a digital-twin container.

    :param container: host id (e.g. gateway, server_1)
    :param command: the shell command to run
    :return: a dict with container, command, exit_code, and output
    """
    container_name = f"{DOCKER.CONTAINER_PREFIX}{container}"
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


def dt_exec(
    container: str, command: str,
) -> dict[str, Any]:
    """
    Execute a shell command on a digital-twin container.

    If the container is not found, the digital twin is
    auto-deployed and the command is retried once.

    :param container: host id (e.g. gateway, server_1)
    :param command: the shell command to run
    :return: a dict with container, command, exit_code, and output
    """
    container_name = f"{DOCKER.CONTAINER_PREFIX}{container}"
    try:
        return _exec_on_container(container, command)
    except docker.errors.NotFound:
        logger.info(
            "Container '%s' not found; triggering "
            "auto-deploy...", container_name,
        )
        try:
            DockerManager.ensure_deployed()
            return _exec_on_container(container, command)
        except Exception as exc:
            return {
                "error": (
                    f"Container '{container_name}' not "
                    f"found and auto-deploy failed: {exc}"
                ),
            }
