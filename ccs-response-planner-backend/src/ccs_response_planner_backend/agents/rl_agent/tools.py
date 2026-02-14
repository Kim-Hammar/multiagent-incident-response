"""
Tool dispatch for the RlAgent.

Provides ``python_exec`` (standard) and ``rl_train`` (streaming)
tools that run code in the Python sandbox container.
"""
import base64
import io
import json
import logging
import tarfile
import threading
import zipfile
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

    Raises ``RuntimeError`` if the write fails.

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
    exec_id = client.api.exec_create(
        ct.id, ["/bin/sh", "-c", write_cmd],
        stdout=True, stderr=True,
    )["Id"]
    output = client.api.exec_start(exec_id)
    exit_code = client.api.exec_inspect(exec_id)[
        "ExitCode"
    ]
    if exit_code != 0:
        err = output.decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Failed to write {filename} to sandbox "
            f"(exit {exit_code}): {err}"
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


def _extract_policy_zip(
    ct: "docker.models.containers.Container",
    algorithm: str,
) -> str | None:
    """
    Extract the trained policy from the sandbox and bundle
    it with a usage script into a combined zip, returned as
    a base64-encoded string.

    Returns ``None`` if the policy file does not exist or
    extraction fails.

    :param ct: the sandbox container
    :param algorithm: the RL algorithm name (e.g. PPO, DQN)
    :return: base64-encoded zip data, or None
    """
    try:
        bits, _stat = ct.get_archive("/workspace/_policy.zip")
        tar_bytes = b"".join(bits)
        with tarfile.open(
            fileobj=io.BytesIO(tar_bytes),
        ) as tar:
            member = tar.getmembers()[0]
            f = tar.extractfile(member)
            if f is None:
                return None
            policy_bytes = f.read()
    except Exception:
        logger.debug(
            "Could not read _policy.zip from sandbox",
            exc_info=True,
        )
        return None

    algo = algorithm.strip() or "PPO"
    usage_script = (
        '"""'
        "\nUsage script for the learned RL policy.\n"
        "\nLoads the trained Stable-Baselines3 model and "
        "demonstrates\nhow to query it for the optimal "
        "action given an observation.\n"
        '"""\n'
        f"from stable_baselines3 import {algo}\n\n"
        "# ── Load the trained model "
        "─────────────────────────────\n"
        f'model = {algo}.load("policy")\n\n'
        "# ── Query the policy "
        "──────────────────────────────────\n"
        "# Replace with an actual observation from your "
        "environment.\n"
        "# obs = env.reset()\n"
        "obs = None  # <-- set your observation here\n"
        "action, _states = model.predict("
        "obs, deterministic=True)\n"
        'print(f"Recommended action index: {action}")\n'
    )

    combined = io.BytesIO()
    with zipfile.ZipFile(
        combined, "w", zipfile.ZIP_DEFLATED,
    ) as zf:
        zf.writestr("policy.zip", policy_bytes)
        zf.writestr("use_policy.py", usage_script)
    return base64.b64encode(
        combined.getvalue(),
    ).decode("ascii")


def rl_train(
    code: str, time_limit_minutes: int = 5,
    algorithm: str = "", hyperparameters: str = "",
) -> Generator[dict[str, Any], None, None]:
    """
    Run RL training code in the sandbox with streaming progress.

    Yields JSON dicts parsed from stdout lines. The training
    script is expected to print JSON lines with ``type`` field
    (``progress``, ``result``, etc.).

    :param code: Python training script
    :param time_limit_minutes: max training time in minutes
    :return: a generator yielding parsed JSON dicts
    """
    client = docker.from_env()
    ct = _ensure_python_sandbox(client)
    _write_code_to_sandbox(client, ct, code, "_train.py")

    exec_id = client.api.exec_create(
        ct.id,
        ["python", "-u", "/workspace/_train.py"],
        stdout=True, stderr=True,
    )["Id"]

    stream = client.api.exec_start(exec_id, stream=True)
    yield {"type": "started", "message": "Training started"}

    timed_out = threading.Event()

    def _kill_exec() -> None:
        """
        Kill the training process after time limit.
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
                "Failed to kill training process",
                exc_info=True,
            )

    timer = threading.Timer(
        time_limit_minutes * 60, _kill_exec,
    )
    timer.start()

    line_buffer = ""
    stderr_buffer = ""
    had_progress = False
    result_data: dict[str, Any] | None = None
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
                    if parsed.get("type") == "progress":
                        had_progress = True
                    if parsed.get("type") == "result":
                        result_data = parsed
                    yield parsed
                except (json.JSONDecodeError, ValueError):
                    stderr_buffer += line + "\n"
    except Exception as e:
        logger.warning(
            "rl_train stream error: %s", e,
            exc_info=True,
        )
    finally:
        timer.cancel()

    if timed_out.is_set():
        yield {
            "type": "timeout",
            "message": (
                f"Training killed after "
                f"{time_limit_minutes} minute(s)."
            ),
        }

    try:
        info = client.api.exec_inspect(exec_id)
        exit_code = info.get("ExitCode", -1)
    except Exception:
        exit_code = -1

    if exit_code != 0 and not had_progress:
        err_msg = stderr_buffer.strip() or (
            f"Training failed (exit {exit_code})"
        )
        yield {
            "type": "error",
            "message": (
                f"Training script error: "
                f"{err_msg[:500]}"
            ),
        }

    policy_data = _extract_policy_zip(ct, algorithm)

    done_event: dict[str, Any] = {
        "type": "done",
        "exit_code": exit_code,
    }
    if result_data:
        done_event["result"] = result_data
    if stderr_buffer.strip():
        done_event["stderr"] = stderr_buffer.strip()
    if policy_data:
        done_event["policy_data"] = policy_data
    yield done_event


TOOL_DISPATCH: dict[str, Callable[..., dict[str, Any]]] = {
    "python_exec": python_exec,
}

STREAMING_TOOL_DISPATCH: dict[
    str, Callable[..., Generator[dict[str, Any], None, None]]
] = {
    "rl_train": rl_train,
}
