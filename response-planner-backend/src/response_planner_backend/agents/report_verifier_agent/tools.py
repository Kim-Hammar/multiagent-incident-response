"""
Tool dispatch for the ReportVerifierAgent.

Reuses the same tools as the ReportAgent — threat intel
APIs, digital-twin shell execution, and Python sandbox —
except ``generate_attack_image`` (the verifier does not
generate or verify attack path diagrams).
"""
from response_planner_backend.agents.report_agent.tools import (
    STREAMING_TOOL_DISPATCH as _REPORT_STREAMING_DISPATCH,
    TOOL_DISPATCH as _REPORT_TOOL_DISPATCH,
)

_EXCLUDED = {"generate_attack_image", "run_host_analyzers"}

TOOL_DISPATCH = {
    k: v for k, v in _REPORT_TOOL_DISPATCH.items()
    if k not in _EXCLUDED
}

STREAMING_TOOL_DISPATCH = {
    k: v for k, v in _REPORT_STREAMING_DISPATCH.items()
    if k not in _EXCLUDED
}

__all__ = ["TOOL_DISPATCH", "STREAMING_TOOL_DISPATCH"]
