"""
Tool dispatch for the PenetrationTestAgent.

Provides a single ``pentest_exec`` tool that runs commands on the
attacker container only, preventing the LLM from executing directly
on victim containers.
"""
import logging
import threading
from typing import Any, Callable, Generator, Optional

import docker

from ccs_response_planner_backend.agents.shared_tools import (
    _exec_stream_on_container,
)
from ccs_response_planner_backend.constants.constants import DOCKER
from ccs_response_planner_backend.db.database_facade import DatabaseFacade
from ccs_response_planner_backend.docker_manager.docker_manager \
    import DockerManager

logger = logging.getLogger(__name__)

EXEC_TIMEOUT_SECONDS = 120


def _find_attacker_container(
    client: docker.DockerClient,
) -> Any:
    """
    Find a running attacker container by name pattern.

    Searches for containers whose name matches
    ``ccs_dt_*_attacker`` or ``ccs_dt_attacker``.

    :param client: a Docker client instance
    :return: the first matching container object
    :raises docker.errors.NotFound: if no attacker container exists
    """
    for ct in client.containers.list():
        name = ct.name
        if (name.startswith(DOCKER.CONTAINER_PREFIX)
                and name.endswith("_attacker")):
            return ct
    raise docker.errors.NotFound(
        "No running attacker container found"
    )


def _run_pentest_command(
    client: docker.DockerClient,
    ct: Any,
    command: str,
) -> dict[str, Any]:
    """
    Execute a command on the attacker container with a timeout.

    :param client: a Docker client instance
    :param ct: the attacker container object
    :param command: the shell command to run
    :return: a dict with command, exit_code, and output
    """
    exec_id = client.api.exec_create(
        ct.id, ["/bin/sh", "-c", command],
        stdout=True, stderr=True,
    )["Id"]

    result: dict[str, Any] = {}

    def _run() -> None:
        result["output"] = client.api.exec_start(
            exec_id,
        ).decode("utf-8", errors="replace")

    thread = threading.Thread(target=_run)
    thread.start()
    thread.join(timeout=EXEC_TIMEOUT_SECONDS)

    if thread.is_alive():
        # Kill the running process inside the container
        try:
            kill_id = client.api.exec_create(
                ct.id,
                ["/bin/sh", "-c",
                 f"kill -9 $(pgrep -f {command[:20]!r})"
                 " 2>/dev/null || true"],
                stdout=True, stderr=True,
            )["Id"]
            client.api.exec_start(kill_id)
        except Exception:
            pass
        thread.join(timeout=5)
        output = result.get("output", "")
        return {
            "command": command,
            "exit_code": -1,
            "output": (
                f"{output}\n\n[TIMEOUT] Command killed "
                f"after {EXEC_TIMEOUT_SECONDS}s. "
                f"Use faster, targeted commands "
                f"(e.g. scan specific ports, not -p-)."
            ),
        }

    exit_code = client.api.exec_inspect(exec_id)[
        "ExitCode"
    ]
    return {
        "command": command,
        "exit_code": exit_code,
        "output": result.get("output", ""),
    }


def pentest_exec(
    command: str,
    incident_id: Optional[int] = None,
) -> dict[str, Any]:
    """
    Execute a shell command on the attacker container.

    Dynamically discovers the attacker container by searching for
    running containers matching ``ccs_dt_*_attacker``. Commands
    are killed after EXEC_TIMEOUT_SECONDS to prevent long-running
    scans from blocking the UI indefinitely. If no attacker
    container is found, the digital twin is auto-deployed and the
    command is retried once.

    :param command: the shell command to run
    :param incident_id: optional incident id for config lookup
    :return: a dict with command, exit_code, and output
    """
    try:
        client = docker.from_env()
        ct = _find_attacker_container(client)
        return _run_pentest_command(client, ct, command)
    except docker.errors.NotFound:
        logger.info(
            "No attacker container found; "
            "triggering auto-deploy...",
        )
        try:
            config_id = None
            if incident_id is not None:
                config_id = (
                    DatabaseFacade.get_config_id_by_incident(
                        incident_id,
                    )
                )
            DockerManager.ensure_deployed(
                config_id=config_id,
            )
            client = docker.from_env()
            ct = _find_attacker_container(client)
            return _run_pentest_command(client, ct, command)
        except Exception as exc:
            return {
                "error": (
                    f"Attacker container not found and "
                    f"auto-deploy failed: {exc}"
                ),
            }


TOOL_DISPATCH: dict[str, Callable[..., dict[str, Any]]] = {
    "pentest_exec": pentest_exec,
}


def pentest_exec_stream(
    command: str,
    incident_id: Optional[int] = None,
) -> Generator[dict[str, Any], None, None]:
    """
    Stream pentest command output from the attacker container.

    Discovers the attacker container, then delegates to
    ``_exec_stream_on_container`` with a timeout. If no attacker
    container is found, auto-deploys and retries.

    :param command: the shell command to run
    :param incident_id: optional incident id for config lookup
    :return: a generator of event dicts
    """
    client = docker.from_env()
    try:
        ct = _find_attacker_container(client)
    except docker.errors.NotFound:
        logger.info(
            "No attacker container found; "
            "triggering auto-deploy...",
        )
        try:
            config_id = None
            if incident_id is not None:
                config_id = (
                    DatabaseFacade.get_config_id_by_incident(
                        incident_id,
                    )
                )
            DockerManager.ensure_deployed(
                config_id=config_id,
            )
            client = docker.from_env()
            ct = _find_attacker_container(client)
        except Exception as exc:
            yield {
                "type": "done",
                "container": "attacker",
                "command": command,
                "exit_code": -1,
                "output": (
                    f"Attacker container not found and "
                    f"auto-deploy failed: {exc}"
                ),
            }
            return

    yield from _exec_stream_on_container(
        container_id=ct.id,
        container_label="attacker",
        command=command,
        client=client,
        timeout_seconds=EXEC_TIMEOUT_SECONDS,
    )


STREAMING_TOOL_DISPATCH: dict[
    str, Callable[..., Generator[dict[str, Any], None, None]]
] = {
    "pentest_exec": pentest_exec_stream,
}
