"""
Shared tool functions used by multiple agents.

Provides ``dt_exec`` with automatic digital-twin deployment so
that agents do not fail when the DT containers are not yet running.
Also provides streaming variants (``_exec_stream_on_container``,
``dt_exec_stream``) that yield output line-by-line.
"""
import logging
import threading
from typing import Any, Generator, Optional

import docker

from ccs_response_planner_backend.constants.constants import DOCKER
from ccs_response_planner_backend.db.database_facade import DatabaseFacade
from ccs_response_planner_backend.docker_manager.docker_manager \
    import DockerManager

logger = logging.getLogger(__name__)

# ── Active exec registry ─────────────────────────────────────────
# Tracks (container_id, exec_id, client) for every running Docker
# exec so that ``kill_all_active_execs`` can terminate them when
# the user clicks Stop.
_active_execs_lock = threading.Lock()
_active_execs: dict[str, tuple[str, "docker.DockerClient"]] = {}


def _register_exec(
    exec_id: str, container_id: str,
    client: "docker.DockerClient",
) -> None:
    """
    Register a running Docker exec for later cancellation.

    :param exec_id: the Docker exec id
    :param container_id: the container the exec runs in
    :param client: a Docker client instance
    """
    with _active_execs_lock:
        _active_execs[exec_id] = (container_id, client)


def _unregister_exec(exec_id: str) -> None:
    """
    Remove a Docker exec from the active registry.

    :param exec_id: the Docker exec id
    """
    with _active_execs_lock:
        _active_execs.pop(exec_id, None)


def kill_all_active_execs() -> int:
    """
    Kill every exec currently tracked in the active registry.

    :return: the number of execs that were killed
    """
    with _active_execs_lock:
        snapshot = list(_active_execs.items())
        _active_execs.clear()

    killed = 0
    for exec_id, (container_id, client) in snapshot:
        try:
            info = client.api.exec_inspect(exec_id)
            if info.get("Running"):
                pid = info.get("Pid", 0)
                if pid:
                    kill_id = client.api.exec_create(
                        container_id,
                        ["/bin/sh", "-c",
                         f"kill -9 {pid}"],
                        stdout=True, stderr=True,
                    )["Id"]
                    client.api.exec_start(kill_id)
                    killed += 1
        except Exception:
            logger.debug(
                "Failed to kill exec %s", exec_id,
                exc_info=True,
            )
    return killed


_VALID_DT_CONTAINERS = [
    "i1_attacker", "i1_gateway", "i1_firewall", "i1_ids",
    "i1_server_1", "i1_server_2", "i1_server_3",
    "i1_server_4", "i1_server_5", "i1_server_6",
    "i2_attacker",
    "i2_server_1", "i2_server_2", "i2_server_3",
    "i2_server_4", "i2_server_5", "i2_server_6",
]


_DT_EXEC_TIMEOUT = 600


def _exec_on_container(
    container: str, command: str,
) -> dict[str, Any]:
    """
    Run a shell command on a digital-twin container.

    The command is killed after ``_DT_EXEC_TIMEOUT`` seconds to
    prevent long-running commands from blocking the API.

    :param container: host id (e.g. i1_firewall, i1_server_1)
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
    _register_exec(exec_id, ct.id, client)

    result: dict[str, Any] = {}

    def _run() -> None:
        result["output"] = client.api.exec_start(
            exec_id,
        ).decode("utf-8", errors="replace")

    try:
        thread = threading.Thread(target=_run)
        thread.start()
        thread.join(timeout=_DT_EXEC_TIMEOUT)

        if thread.is_alive():
            try:
                info = client.api.exec_inspect(exec_id)
                pid = info.get("Pid", 0)
                if pid:
                    kill_id = client.api.exec_create(
                        ct.id,
                        ["/bin/sh", "-c",
                         f"kill -9 {pid}"],
                        stdout=True, stderr=True,
                    )["Id"]
                    client.api.exec_start(kill_id)
            except Exception:
                pass
            thread.join(timeout=5)
            output = result.get("output", "")
            return {
                "container": container,
                "command": command,
                "exit_code": -1,
                "output": (
                    f"{output}\n\n[TIMEOUT] Command killed "
                    f"after {_DT_EXEC_TIMEOUT}s. Use short, "
                    f"targeted commands."
                ),
            }

        exit_code = client.api.exec_inspect(exec_id)[
            "ExitCode"
        ]
        return {
            "container": container,
            "command": command,
            "exit_code": exit_code,
            "output": result.get("output", ""),
        }
    finally:
        _unregister_exec(exec_id)


def dt_exec(
    container: str, command: str,
    incident_id: Optional[int] = None,
) -> dict[str, Any]:
    """
    Execute a shell command on a digital-twin container.

    If the container is not found, the digital twin is
    auto-deployed and the command is retried once.

    :param container: host id (e.g. i1_firewall, i1_server_1)
    :param command: the shell command to run
    :param incident_id: optional incident id for config lookup
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
            return _exec_on_container(container, command)
        except Exception as exc:
            return {
                "error": (
                    f"Container '{container_name}' not "
                    f"found and auto-deploy failed: {exc}"
                ),
            }


_EXEC_STREAM_TIMEOUT = 600


def _exec_stream_on_container(
    container_id: str,
    container_label: str,
    command: str,
    client: docker.DockerClient,
    timeout_seconds: int = _EXEC_STREAM_TIMEOUT,
) -> Generator[dict[str, Any], None, None]:
    """
    Stream the output of a shell command on a container line-by-line.

    Yields ``output_chunk`` events for each line, then a final
    ``done`` event with the full output and exit code.

    :param container_id: the Docker container id
    :param container_label: human-readable container label
    :param command: the shell command to run
    :param client: a Docker client instance
    :param timeout_seconds: max execution time in seconds
    :return: a generator of event dicts
    """
    exec_id = client.api.exec_create(
        container_id, ["/bin/sh", "-c", command],
        stdout=True, stderr=True,
    )["Id"]
    _register_exec(exec_id, container_id, client)

    stream = client.api.exec_start(exec_id, stream=True)

    timed_out = threading.Event()

    def _kill() -> None:
        """
        Kill the running exec after timeout.
        """
        timed_out.set()
        try:
            info = client.api.exec_inspect(exec_id)
            pid = info.get("Pid", 0)
            if pid:
                kill_id = client.api.exec_create(
                    container_id,
                    ["/bin/sh", "-c",
                     f"kill -9 {pid}"],
                    stdout=True, stderr=True,
                )["Id"]
                client.api.exec_start(kill_id)
        except Exception:
            logger.warning(
                "Failed to kill exec process",
                exc_info=True,
            )

    timer = threading.Timer(timeout_seconds, _kill)
    timer.start()

    full_output = ""
    line_buffer = ""
    try:
        for chunk in stream:
            text = chunk.decode("utf-8", errors="replace")
            full_output += text
            line_buffer += text
            while "\n" in line_buffer:
                line, line_buffer = line_buffer.split(
                    "\n", 1,
                )
                yield {
                    "type": "output_chunk",
                    "text": line + "\n",
                }
        if line_buffer:
            yield {
                "type": "output_chunk",
                "text": line_buffer,
            }
    except Exception as e:
        logger.warning(
            "exec stream error: %s", e, exc_info=True,
        )
    finally:
        timer.cancel()
        _unregister_exec(exec_id)

    if timed_out.is_set():
        timeout_msg = (
            f"\n\n[TIMEOUT] Command killed after "
            f"{timeout_seconds}s."
        )
        full_output += timeout_msg
        yield {
            "type": "output_chunk",
            "text": timeout_msg,
        }

    try:
        info = client.api.exec_inspect(exec_id)
        exit_code = info.get("ExitCode", -1)
    except Exception:
        exit_code = -1

    if timed_out.is_set():
        exit_code = -1

    yield {
        "type": "done",
        "container": container_label,
        "command": command,
        "exit_code": exit_code,
        "output": full_output,
    }


def dt_exec_stream(
    container: str, command: str,
    incident_id: Optional[int] = None,
) -> Generator[dict[str, Any], None, None]:
    """
    Stream the output of a command on a digital-twin container.

    If the container is not found, the digital twin is
    auto-deployed and the command is retried once.

    :param container: host id (e.g. i1_firewall, i1_server_1)
    :param command: the shell command to run
    :param incident_id: optional incident id for config lookup
    :return: a generator of event dicts
    """
    container_name = f"{DOCKER.CONTAINER_PREFIX}{container}"
    client = docker.from_env()
    try:
        ct = client.containers.get(container_name)
    except docker.errors.NotFound:
        logger.info(
            "Container '%s' not found; triggering "
            "auto-deploy...", container_name,
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
            ct = client.containers.get(container_name)
        except Exception as exc:
            yield {
                "type": "done",
                "container": container,
                "command": command,
                "exit_code": -1,
                "output": (
                    f"Container '{container_name}' not "
                    f"found and auto-deploy failed: {exc}"
                ),
            }
            return

    yield from _exec_stream_on_container(
        container_id=ct.id,
        container_label=container,
        command=command,
        client=client,
    )
