"""
Tool dispatch for the ValidationAgent.

Provides ``dt_exec`` for running commands on digital-twin containers
and ``query_policy`` for querying a trained RL policy.
"""
import base64
import json
import logging
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

logger = logging.getLogger(__name__)

_QUERY_POLICY_SCRIPT = textwrap.dedent("""\
    import json, sys, importlib.util, numpy as np
    from sb3_contrib import MaskablePPO
    spec = importlib.util.spec_from_file_location(
        "_env", "/workspace/_env.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    import gymnasium
    EnvClass = None
    for name in dir(mod):
        obj = getattr(mod, name)
        if (isinstance(obj, type)
                and issubclass(obj, gymnasium.Env)
                and obj is not gymnasium.Env):
            EnvClass = obj
            break
    env = EnvClass()
    expected_dims = env.observation_space.shape[0]
    state_arr = np.array(STATE_VEC, dtype=np.float32)
    if len(state_arr) != expected_dims:
        print(json.dumps({
            "error": (
                f"Dimension mismatch: expected "
                f"{expected_dims}, got {len(state_arr)}. "
                f"Check the Code Agent Report for the "
                f"correct state vector format."
            ),
            "expected_dimensions": expected_dims,
            "got_dimensions": len(state_arr)
        }))
        sys.exit(0)
    env.set_state(state_arr)
    mask = env.get_action_mask()
    model = MaskablePPO.load("/workspace/_policy", env=env)
    action, _ = model.predict(
        state_arr, action_masks=mask, deterministic=False
    )
    action_idx = int(action)
    actions = env.get_actions()
    a = actions[action_idx] if action_idx < len(actions) else {}
    mask_list = [bool(m) for m in mask]
    print(json.dumps({
        "action_index": action_idx,
        "name": a.get("name", f"action_{action_idx}"),
        "description": a.get("description", ""),
        "commands": a.get("commands", []),
        "action_mask": mask_list,
        "valid_action_count": sum(mask_list),
        "total_action_count": len(mask_list)
    }))
""")


def query_policy(state: list[float]) -> dict[str, Any]:
    """
    Query the trained RL policy for the best action given a state.

    Runs a Python script in the sandbox that loads the environment
    and policy, sets the environment state, computes the action mask,
    and calls model.predict with masking applied.

    :param state: the current state vector
    :return: dict with action_index, name, description, commands,
             action_mask, valid_action_count, total_action_count
    """
    script = _QUERY_POLICY_SCRIPT.replace(
        "STATE_VEC",
        repr(state),
    )

    client = docker.from_env()
    try:
        ct = client.containers.get(
            DOCKER.PYTHON_SANDBOX_CONTAINER,
        )
        if ct.status != "running":
            ct.start()
    except docker.errors.NotFound:
        return {
            "error": "Python sandbox not running. "
            "Policy may not be loaded.",
        }

    encoded = base64.b64encode(
        script.encode("utf-8"),
    ).decode("ascii")
    write_cmd = (
        f"python3 -c \"import base64; "
        f"open('/workspace/_query.py','wb')"
        f".write(base64.b64decode('{encoded}'))\""
    )
    client.api.exec_start(
        client.api.exec_create(
            ct.id, ["/bin/sh", "-c", write_cmd],
            stdout=True, stderr=True,
        )["Id"],
    )

    exec_id = client.api.exec_create(
        ct.id,
        ["/bin/sh", "-c",
         "python3 /workspace/_query.py 2>&1"],
        stdout=True, stderr=True,
    )["Id"]
    output = client.api.exec_start(exec_id).decode(
        "utf-8", errors="replace",
    )
    exit_code = client.api.exec_inspect(exec_id)[
        "ExitCode"
    ]

    if exit_code != 0:
        return {
            "error": f"Policy query failed "
            f"(exit {exit_code}): {output.strip()}",
        }

    for line in output.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            return dict(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            continue

    return {"error": f"No JSON output: {output.strip()}"}


TOOL_DISPATCH: dict[str, Callable[..., dict[str, Any]]] = {
    "dt_exec": dt_exec,
    "dt_restart": dt_restart,
    "query_policy": query_policy,
}

STREAMING_TOOL_DISPATCH: dict[
    str, Callable[..., Generator[dict[str, Any], None, None]]
] = {
    "dt_exec": dt_exec_stream,
    "dt_restart": dt_restart_stream,
}
