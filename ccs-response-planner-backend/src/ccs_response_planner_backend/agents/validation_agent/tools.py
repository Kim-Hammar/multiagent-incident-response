"""
Tool dispatch for the ValidationAgent.

Provides ``dt_exec`` for running commands on digital-twin containers
and ``query_policy`` for querying a trained RL policy.
"""
import base64
import json
import logging
from typing import Any, Callable

import docker

from ccs_response_planner_backend.agents.shared_tools import (
    dt_exec,
)
from ccs_response_planner_backend.constants.constants import DOCKER

logger = logging.getLogger(__name__)


def query_policy(state: list[float]) -> dict[str, Any]:
    """
    Query the trained RL policy for the best action given a state.

    Runs a Python script in the sandbox that loads the environment
    and policy, calls model.predict(state), and returns the action.

    :param state: the current state vector
    :return: dict with action_index, name, description, commands
    """
    script = (
        "import json, sys, importlib.util, numpy as np\n"
        "from stable_baselines3 import PPO\n"
        "spec = importlib.util.spec_from_file_location("
        "'_env', '/workspace/_env.py')\n"
        "mod = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(mod)\n"
        "import gymnasium\n"
        "EnvClass = None\n"
        "for name in dir(mod):\n"
        "    obj = getattr(mod, name)\n"
        "    if isinstance(obj, type) and issubclass("
        "obj, gymnasium.Env) and obj is not gymnasium.Env:\n"
        "        EnvClass = obj\n"
        "        break\n"
        "env = EnvClass()\n"
        "model = PPO.load('/workspace/_policy', env=env)\n"
        "state_arr = np.array(STATE_VEC, dtype=np.float32)\n"
        "action, _ = model.predict(state_arr, "
        "deterministic=False)\n"
        "action_idx = int(action)\n"
        "actions = env.get_actions()\n"
        "a = actions[action_idx] if action_idx < len("
        "actions) else {}\n"
        "print(json.dumps({"
        "'action_index': action_idx, "
        "'name': a.get('name', f'action_{action_idx}'), "
        "'description': a.get('description', ''), "
        "'commands': a.get('commands', [])"
        "}))\n"
    )
    script = script.replace(
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
    "query_policy": query_policy,
}
