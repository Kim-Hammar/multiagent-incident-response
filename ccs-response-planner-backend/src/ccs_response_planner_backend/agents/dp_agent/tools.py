"""
Tool dispatch for the DpAgent.

Provides ``python_exec`` (standard) and ``dp_solve`` (streaming)
tools that run code in the Python sandbox container.
"""
import base64
import json
import logging
import threading
from typing import Any, Callable, Generator

import docker

from ccs_response_planner_backend.constants.constants import DOCKER

logger = logging.getLogger(__name__)


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


def _write_code_to_sandbox(
    client: docker.DockerClient,
    ct: docker.models.containers.Container,
    code: str,
    filename: str,
) -> None:
    """
    Write Python code to a file inside the sandbox container.

    :param client: a Docker client instance
    :param ct: the sandbox container
    :param code: the Python source code
    :param filename: the target filename inside /workspace/
    """
    encoded = base64.b64encode(
        code.encode("utf-8"),
    ).decode("ascii")
    write_cmd = (
        f"python3 -c \"import base64; "
        f"open('/workspace/{filename}','wb')"
        f".write(base64.b64decode('{encoded}'))\""
    )
    client.api.exec_start(
        client.api.exec_create(
            ct.id, ["/bin/sh", "-c", write_cmd],
            stdout=True, stderr=True,
        )["Id"],
    )


def python_exec(code: str) -> dict[str, Any]:
    """
    Execute Python code in the sandbox container.

    :param code: the Python source code to run
    :return: a dict with code, exit_code, and output
    """
    client = docker.from_env()
    ct = _ensure_python_sandbox(client)
    _write_code_to_sandbox(client, ct, code, "_code.py")
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


def dp_solve(
    code: str, time_limit_minutes: int = 10,
    method: str = "", parameters: str = "",
) -> Generator[dict[str, Any], None, None]:
    """
    Run DP value iteration code in the sandbox with streaming progress.

    Yields JSON dicts parsed from stdout lines. The solving
    script is expected to print JSON lines with ``type`` field
    (``progress``, ``result``, etc.).

    :param code: Python solving script
    :param time_limit_minutes: max solving time in minutes
    :param method: the DP method name (e.g. value_iteration)
    :param parameters: key parameters as a summary string
    :return: a generator yielding parsed JSON dicts
    """
    client = docker.from_env()
    ct = _ensure_python_sandbox(client)
    _write_code_to_sandbox(client, ct, code, "_dp_solve.py")

    exec_id = client.api.exec_create(
        ct.id,
        ["python", "-u", "/workspace/_dp_solve.py"],
        stdout=True, stderr=True,
    )["Id"]

    stream = client.api.exec_start(exec_id, stream=True)

    timed_out = threading.Event()

    def _kill_exec() -> None:
        """
        Kill the solving process after time limit.
        """
        timed_out.set()
        try:
            info = client.api.exec_inspect(exec_id)
            pid = info.get("Pid", 0)
            if pid:
                client.api.exec_create(
                    ct.id,
                    ["/bin/sh", "-c", f"kill -9 {pid}"],
                    stdout=True, stderr=True,
                )
        except Exception:
            logger.warning(
                "Failed to kill solving process",
                exc_info=True,
            )

    timer = threading.Timer(
        time_limit_minutes * 60, _kill_exec,
    )
    timer.start()

    line_buffer = ""
    stderr_buffer = ""
    try:
        for chunk in stream:
            text = chunk.decode("utf-8", errors="replace")
            line_buffer += text
            while "\n" in line_buffer:
                line, line_buffer = line_buffer.split(
                    "\n", 1,
                )
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                    yield parsed
                except (json.JSONDecodeError, ValueError):
                    stderr_buffer += line + "\n"
    except Exception as e:
        logger.warning(
            "dp_solve stream error: %s", e,
            exc_info=True,
        )
    finally:
        timer.cancel()

    if timed_out.is_set():
        yield {
            "type": "timeout",
            "message": (
                f"Solving killed after "
                f"{time_limit_minutes} minute(s)."
            ),
        }

    try:
        info = client.api.exec_inspect(exec_id)
        exit_code = info.get("ExitCode", -1)
    except Exception:
        exit_code = -1

    done_event: dict[str, Any] = {
        "type": "done",
        "exit_code": exit_code,
    }
    if stderr_buffer.strip():
        done_event["stderr"] = stderr_buffer.strip()
    yield done_event


TOOL_DISPATCH: dict[str, Callable[..., dict[str, Any]]] = {
    "python_exec": python_exec,
}

STREAMING_TOOL_DISPATCH: dict[
    str, Callable[..., Generator[dict[str, Any], None, None]]
] = {
    "dp_solve": dp_solve,
}
