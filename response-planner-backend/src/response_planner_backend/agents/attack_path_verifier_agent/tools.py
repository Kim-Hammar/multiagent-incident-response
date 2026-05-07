"""
Tool dispatch for the AttackPathVerifierAgent.

Provides ``dt_exec`` for running commands on digital-twin containers
and ``dt_restart`` for restarting crashed containers.
"""
from typing import Any, Callable, Generator

from response_planner_backend.agents.shared_tools import (
    dt_exec,
    dt_exec_stream,
    dt_restart,
    dt_restart_stream,
)

TOOL_DISPATCH: dict[str, Callable[..., dict[str, Any]]] = {
    "dt_exec": dt_exec,
    "dt_restart": dt_restart,
}

STREAMING_TOOL_DISPATCH: dict[
    str, Callable[..., Generator[dict[str, Any], None, None]]
] = {
    "dt_exec": dt_exec_stream,
    "dt_restart": dt_restart_stream,
}
