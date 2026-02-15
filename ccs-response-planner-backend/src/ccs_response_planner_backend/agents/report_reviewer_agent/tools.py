"""
Tool dispatch for the ReportReviewerAgent.

Reuses the exact same tools as the ReportAgent — threat intel
APIs, digital-twin shell execution, and Python sandbox.
"""
from ccs_response_planner_backend.agents.report_agent.tools import (
    STREAMING_TOOL_DISPATCH,
    TOOL_DISPATCH,
)

__all__ = ["TOOL_DISPATCH", "STREAMING_TOOL_DISPATCH"]
