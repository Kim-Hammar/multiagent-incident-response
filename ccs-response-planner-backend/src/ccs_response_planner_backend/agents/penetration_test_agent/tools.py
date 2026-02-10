"""
Tool dispatch for the PenetrationTestAgent.

Provides a single ``pentest_exec`` tool that runs commands on the
attacker container only, preventing the LLM from executing directly
on victim containers.
"""
import threading
from typing import Any, Callable

import docker

from ccs_response_planner_backend.constants.constants import DOCKER

EXEC_TIMEOUT_SECONDS = 120


def pentest_exec(command: str) -> dict[str, Any]:
    """
    Execute a shell command on the attacker container.

    Commands are killed after EXEC_TIMEOUT_SECONDS to prevent
    long-running scans from blocking the UI indefinitely.

    :param command: the shell command to run
    :return: a dict with command, exit_code, and output
    """
    container_name = DOCKER.ATTACKER_CONTAINER
    try:
        client = docker.from_env()
        ct = client.containers.get(container_name)
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
    except docker.errors.NotFound:
        return {
            "error": (
                f"Attacker container '{container_name}' "
                f"not found. Is the digital twin deployed?"
            ),
        }


TOOL_DISPATCH: dict[str, Callable[..., dict[str, Any]]] = {
    "pentest_exec": pentest_exec,
}
