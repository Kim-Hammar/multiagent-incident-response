"""
Tool dispatch for the CodeAgent.

Provides ``python_exec`` and ``gym_verify`` tools that run
code in the Python sandbox container.
"""
import base64
import json
import textwrap
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


_GYM_VERIFY_SCRIPT = textwrap.dedent("""\
    import importlib.util, json, sys, traceback
    checks = []
    error = None
    valid = True
    try:
        spec = importlib.util.spec_from_file_location(
            "_env", "/workspace/_env.py"
        )
        mod = spec.loader.load_module()
        import gymnasium
        env_cls = None
        for name in dir(mod):
            obj = getattr(mod, name)
            if (isinstance(obj, type)
                    and issubclass(obj, gymnasium.Env)
                    and obj is not gymnasium.Env):
                env_cls = obj
                break
        if env_cls is None:
            valid = False
            checks.append({
                "check": "find_env_class",
                "passed": False,
                "detail": "No gymnasium.Env subclass found"
            })
        else:
            checks.append({
                "check": "find_env_class",
                "passed": True,
                "detail": env_cls.__name__
            })
            for method in ["get_actions", "step",
                           "reset", "set_state"]:
                has = hasattr(env_cls, method)
                checks.append({
                    "check": f"has_{method}",
                    "passed": has,
                    "detail": "" if has else f"Missing {method}"
                })
                if not has:
                    valid = False
            if valid:
                env = env_cls()
                state, info = env.reset()
                state_list = list(state)
                ok = (len(state_list) >= 6
                      and all(0 <= v <= 1 for v in state_list))
                checks.append({
                    "check": "reset_state_shape",
                    "passed": ok,
                    "detail": f"{len(state_list)} dims: "
                             + str(state_list)
                })
                if not ok:
                    valid = False
                actions = env.get_actions()
                ok = (isinstance(actions, list)
                      and len(actions) > 0)
                checks.append({
                    "check": "get_actions_nonempty",
                    "passed": ok,
                    "detail": f"{len(actions)} actions"
                             if ok else "empty"
                })
                if not ok:
                    valid = False
                result = env.step(0)
                ok = (isinstance(result, tuple)
                      and len(result) == 5)
                checks.append({
                    "check": "step_returns_tuple5",
                    "passed": ok,
                    "detail": str(len(result))
                             if isinstance(result, tuple)
                             else type(result).__name__
                })
                if not ok:
                    valid = False
                n_dims = len(state_list)
                env.set_state([0.5] * n_dims)
                cur = list(env.state)
                ok = (len(cur) == n_dims
                      and all(
                    abs(v - 0.5) < 1e-6 for v in cur
                ))
                checks.append({
                    "check": "set_state_works",
                    "passed": ok,
                    "detail": str(cur)
                })
                if not ok:
                    valid = False
                if valid:
                    import numpy as _np
                    from collections import Counter
                    _N_SEEDS = 10
                    _MAX_STEPS = 300
                    _n_acts = env.action_space.n
                    _reached = 0
                    _step_counts = []
                    _diag_trace = []
                    _diag_final_state = None
                    _diag_last_reward = None
                    _diag_action_counts = None
                    for _sd in range(_N_SEEDS):
                        obs, _ = env.reset(
                            seed=_sd + 42
                        )
                        _actions_chosen = []
                        for _t in range(_MAX_STEPS):
                            _bk = _np.array(
                                obs, dtype=_np.float64
                            )
                            _ba, _br = 0, -1e18
                            for _a in range(_n_acts):
                                env.set_state(_bk)
                                _, _r, *_ = env.step(
                                    _a
                                )
                                if _r > _br:
                                    _ba = _a
                                    _br = _r
                            env.set_state(_bk)
                            obs, _rew, _tm, _tr, _ = (
                                env.step(_ba)
                            )
                            _act_name = "?"
                            _acts = env.get_actions()
                            if _ba < len(_acts):
                                _act_name = (
                                    _acts[_ba].get(
                                        "name",
                                        str(_ba)
                                    )
                                )
                            _actions_chosen.append(
                                _act_name
                            )
                            if _tm or _tr:
                                _reached += 1
                                _step_counts.append(
                                    _t + 1
                                )
                                break
                        else:
                            _step_counts.append(
                                _MAX_STEPS
                            )
                        if _sd == 0:
                            _diag_trace = (
                                _actions_chosen[:30]
                            )
                            _diag_last_reward = _rew
                            _diag_final_state = {
                                i: round(float(v), 2)
                                for i, v
                                in enumerate(obs)
                                if abs(v) > 0.001
                            }
                            _cnt = Counter(
                                _actions_chosen
                            )
                            _diag_action_counts = (
                                dict(
                                    _cnt.most_common(
                                        10
                                    )
                                )
                            )
                    _rok = _reached > 0
                    _rdt = (
                        f"{_reached}/{_N_SEEDS}"
                        " seeds reached terminal"
                    )
                    if _reached > 0:
                        _avg = sum(
                            s for s in _step_counts
                            if s < _MAX_STEPS
                        ) / _reached
                        _rdt += (
                            f" (avg {_avg:.0f} steps)"
                        )
                    if not _rok:
                        _rdt += (
                            f". DIAGNOSTIC (seed 0,"
                            f" first 30 actions):"
                            f" {_diag_trace}."
                            f" Action frequencies"
                            f" (all {_MAX_STEPS}"
                            f" steps):"
                            f" {_diag_action_counts}."
                            f" Last reward:"
                            f" {_diag_last_reward}."
                            f" Non-zero state dims:"
                            f" {_diag_final_state}"
                        )
                    checks.append({
                        "check":
                            "greedy_reachability",
                        "passed": _rok,
                        "detail": _rdt
                    })
                    if not _rok:
                        valid = False
    except Exception:
        valid = False
        error = traceback.format_exc()
    print(json.dumps({
        "valid": valid,
        "checks": checks,
        "error": error
    }))
""")


def gym_verify(code: str) -> dict[str, Any]:
    """
    Verify code implements a valid Gymnasium environment.

    Writes the code to /workspace/_env.py in the sandbox,
    then runs a verification script that checks for required
    methods, state shape, and basic episode execution.

    :param code: the Python source code to verify
    :return: a dict with valid, checks, and error fields
    """
    client = docker.from_env()
    ct = _ensure_python_sandbox(client)

    encoded_env = base64.b64encode(
        code.encode("utf-8"),
    ).decode("ascii")
    write_env_cmd = (
        f"python3 -c \"import base64; "
        f"open('/workspace/_env.py','wb')"
        f".write(base64.b64decode('{encoded_env}'))\""
    )
    client.api.exec_start(
        client.api.exec_create(
            ct.id, ["/bin/sh", "-c", write_env_cmd],
            stdout=True, stderr=True,
        )["Id"],
    )

    encoded_verify = base64.b64encode(
        _GYM_VERIFY_SCRIPT.encode("utf-8"),
    ).decode("ascii")
    write_verify_cmd = (
        f"python3 -c \"import base64; "
        f"open('/workspace/_verify.py','wb')"
        f".write(base64.b64decode('{encoded_verify}'))\""
    )
    client.api.exec_start(
        client.api.exec_create(
            ct.id, ["/bin/sh", "-c", write_verify_cmd],
            stdout=True, stderr=True,
        )["Id"],
    )

    run_cmd = "python /workspace/_verify.py"
    exec_id = client.api.exec_create(
        ct.id, ["/bin/sh", "-c", run_cmd],
        stdout=True, stderr=True,
    )["Id"]
    output = client.api.exec_start(exec_id).decode(
        "utf-8", errors="replace",
    )
    exit_code = client.api.exec_inspect(exec_id)["ExitCode"]

    if exit_code != 0:
        return {
            "valid": False,
            "checks": [],
            "error": output,
        }

    try:
        result: dict[str, Any] = json.loads(output)
        return result
    except (json.JSONDecodeError, ValueError):
        return {
            "valid": False,
            "checks": [],
            "error": output,
        }


TOOL_DISPATCH: dict[str, Callable[..., dict[str, Any]]] = {
    "python_exec": python_exec,
    "gym_verify": gym_verify,
    "dt_exec": dt_exec,
    "dt_restart": dt_restart,
}

STREAMING_TOOL_DISPATCH: dict[
    str, Callable[..., Generator[dict[str, Any], None, None]]
] = {
    "dt_exec": dt_exec_stream,
    "dt_restart": dt_restart_stream,
}
