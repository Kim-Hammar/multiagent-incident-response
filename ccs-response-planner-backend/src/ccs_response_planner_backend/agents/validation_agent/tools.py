"""
Tool dispatch for the ValidationAgent.

Provides a single ``dt_exec`` tool that runs commands on
digital-twin containers to apply response actions and check state.
"""
from typing import Any, Callable

from ccs_response_planner_backend.agents.shared_tools import (
    dt_exec,
)

TOOL_DISPATCH: dict[str, Callable[..., dict[str, Any]]] = {
    "dt_exec": dt_exec,
}
