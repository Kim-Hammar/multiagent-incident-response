"""
Tool dispatch for the PlannerAgent.

Provides ``python_exec`` (standard) and ``rl_train`` (streaming)
tools that run code in the Python sandbox container.
"""
import base64
import io
import json
import logging
import os
import signal
import tarfile
import threading
import time
import zipfile
from typing import Any, Callable, Generator

import docker

from response_planner_backend.constants.constants import DOCKER

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

    algo = algorithm.strip() or "MaskablePPO"
    usage_script = (
        '"""'
        "\nUsage script for the learned RL policy.\n"
        "\nLoads the trained Stable-Baselines3 model and "
        "demonstrates\nhow to query it for the optimal "
        "action given an observation.\n"
        '"""\n'
        f"from sb3_contrib import {algo}\n\n"
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


MAX_TIME_LIMIT_MINUTES = 60


def rl_train(
    code: str, time_limit_minutes: int = 10,
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
    time_limit_minutes = min(
        max(int(time_limit_minutes), 1),
        MAX_TIME_LIMIT_MINUTES,
    )
    timeout_secs = time_limit_minutes * 60 + 30
    logger.info(
        "rl_train called: time_limit_minutes=%d, "
        "kill timer=%ds",
        time_limit_minutes, timeout_secs,
    )

    client = docker.from_env()
    ct = _ensure_python_sandbox(client)
    _write_code_to_sandbox(client, ct, code, "_train.py")

    exec_id = client.api.exec_create(
        ct.id,
        ["python", "-u", "/workspace/_train.py"],
        stdout=True, stderr=True,
    )["Id"]
    logger.info("rl_train exec created: %s", exec_id)

    stream = client.api.exec_start(exec_id, stream=True)
    start_time = time.monotonic()
    yield {"type": "started", "message": "Training started"}

    timed_out = threading.Event()

    def _kill_exec() -> None:
        """
        Kill the training process after the time limit.

        Uses ``os.kill`` with the host-side PID from
        ``exec_inspect`` — this is reliable regardless of
        which tools are installed in the container.
        """
        elapsed = time.monotonic() - start_time
        logger.warning(
            "rl_train kill timer fired after %.1fs "
            "(limit was %ds) – killing exec %s",
            elapsed, timeout_secs, exec_id,
        )
        timed_out.set()

        # ── Method 1: os.kill from host ──────────────
        try:
            info = client.api.exec_inspect(exec_id)
            pid = info.get("Pid", 0)
            running = info.get("Running", False)
            logger.info(
                "exec_inspect: Pid=%s, Running=%s",
                pid, running,
            )
            if pid and pid > 0:
                os.kill(pid, signal.SIGKILL)
                logger.info(
                    "os.kill(%d, SIGKILL) succeeded",
                    pid,
                )
                return
            else:
                logger.warning(
                    "exec_inspect returned Pid=%s, "
                    "trying container-side kill", pid,
                )
        except ProcessLookupError:
            logger.info(
                "Process %s already dead", exec_id,
            )
            return
        except Exception:
            logger.warning(
                "os.kill failed for exec %s",
                exec_id, exc_info=True,
            )

        # ── Method 2: Python-based kill inside container
        try:
            py_kill = (
                "python3 -c \""
                "import os,signal as S;"
                "[os.kill(int(p),S.SIGKILL) "
                "for p in os.listdir('/proc') "
                "if p.isdigit() and "
                "'_train.py' in "
                "open('/proc/'+p+'/cmdline').read()"
                "]\""
            )
            kill_id = client.api.exec_create(
                ct.id,
                ["/bin/sh", "-c", py_kill],
                stdout=True, stderr=True,
            )["Id"]
            output = client.api.exec_start(kill_id)
            logger.info(
                "Container-side python kill output: %s",
                output,
            )
        except Exception:
            logger.warning(
                "Container-side kill also failed "
                "for exec %s",
                exec_id, exc_info=True,
            )

    timer = threading.Timer(timeout_secs, _kill_exec)
    timer.daemon = True
    timer.start()
    logger.info(
        "Kill timer started: %ds from now", timeout_secs,
    )

    line_buffer = ""
    stderr_buffer = ""
    result_data: dict[str, Any] | None = None
    # Throttle progress events to ≤1/s so the frontend
    # poll (limit=5) can always keep up.  Non-progress
    # events (result, error, eval_progress) are always
    # forwarded immediately.
    _MIN_PROGRESS_INTERVAL = 1.0
    _last_progress_time = 0.0
    _skipped = 0
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
                    if parsed.get("type") == "result":
                        result_data = parsed
                        yield parsed
                    elif parsed.get("type") == "progress":
                        now = time.monotonic()
                        if (
                            now - _last_progress_time
                            >= _MIN_PROGRESS_INTERVAL
                        ):
                            if _skipped:
                                parsed["_skipped"] = (
                                    _skipped
                                )
                            yield parsed
                            _last_progress_time = now
                            _skipped = 0
                        else:
                            _skipped += 1
                    else:
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

    elapsed = time.monotonic() - start_time
    logger.info(
        "rl_train stream ended after %.1fs, "
        "timed_out=%s",
        elapsed, timed_out.is_set(),
    )

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

    if exit_code != 0:
        err_msg = stderr_buffer.strip() or (
            f"Training failed (exit {exit_code})"
        )
        yield {
            "type": "error",
            "message": (
                f"Training script error "
                f"(exit {exit_code}): "
                f"{err_msg[:2000]}"
            ),
        }

    policy_data = _extract_policy_zip(ct, algorithm)

    # Yield policy_data as a separate event to keep the
    # done event small — large base64 payloads can break
    # JSON serialisation / transfer for the poll endpoint.
    if policy_data:
        yield {
            "type": "policy_data",
            "policy_data": policy_data,
        }

    done_event: dict[str, Any] = {
        "type": "done",
        "exit_code": exit_code,
    }
    if result_data:
        done_event["result"] = result_data
    if stderr_buffer.strip():
        done_event["stderr"] = stderr_buffer.strip()[
            :2000
        ]
    if exit_code != 0:
        done_event["error"] = (
            stderr_buffer.strip()[:2000]
            or f"Training failed (exit {exit_code})"
        )
    yield done_event
    logger.info(
        "rl_train finished: exit_code=%s, "
        "total_elapsed=%.1fs",
        exit_code, time.monotonic() - start_time,
    )


TOOL_DISPATCH: dict[str, Callable[..., dict[str, Any]]] = {
    "python_exec": python_exec,
}

STREAMING_TOOL_DISPATCH: dict[
    str, Callable[..., Generator[dict[str, Any], None, None]]
] = {
    "rl_train": rl_train,
}
