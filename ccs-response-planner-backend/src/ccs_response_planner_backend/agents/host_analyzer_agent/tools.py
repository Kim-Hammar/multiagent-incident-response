"""
Tool dispatch for the HostAnalyzerAgent.

Reuses all ReportAgent investigation tools except
generate_attack_image. Includes dt_exec and dt_restart
from shared_tools.
"""
from typing import Any, Callable, Generator

from ccs_response_planner_backend.agents.report_agent.tools import (
    tavily_search,
    nvd_search,
    mitre_search,
    virustotal_scan,
    abuseipdb_check,
    otx_search,
    dt_python_exec,
)
from ccs_response_planner_backend.agents.shared_tools import (
    dt_exec,
    dt_exec_stream,
    dt_restart,
    dt_restart_stream,
)

TOOL_DISPATCH: dict[str, Callable[..., dict[str, Any]]] = {
    "tavily_search": tavily_search,
    "nvd_search": nvd_search,
    "mitre_search": mitre_search,
    "virustotal_scan": virustotal_scan,
    "abuseipdb_check": abuseipdb_check,
    "otx_search": otx_search,
    "dt_exec": dt_exec,
    "dt_restart": dt_restart,
    "dt_python_exec": dt_python_exec,
}

STREAMING_TOOL_DISPATCH: dict[
    str, Callable[..., Generator[dict[str, Any], None, None]]
] = {
    "dt_exec": dt_exec_stream,
    "dt_restart": dt_restart_stream,
}
