"""
Tool dispatch for the ReportReviewerAgent.

Reuses the same tools as the ReportAgent — threat intel
APIs, digital-twin shell execution, and Python sandbox —
except ``generate_attack_image`` (the reviewer does not
generate or verify attack path diagrams).
"""
from ccs_response_planner_backend.agents.report_agent.tools import (
    STREAMING_TOOL_DISPATCH,
    TOOL_DISPATCH as _REPORT_TOOL_DISPATCH,
)

TOOL_DISPATCH = {
    k: v for k, v in _REPORT_TOOL_DISPATCH.items()
    if k != "generate_attack_image"
}

__all__ = ["TOOL_DISPATCH", "STREAMING_TOOL_DISPATCH"]
