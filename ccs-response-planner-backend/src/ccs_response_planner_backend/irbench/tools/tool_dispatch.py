"""
Tool dispatch dicts for IRBench evaluation.

Each ``build_*_dispatch`` function returns a
``(TOOL_DISPATCH, STREAMING_TOOL_DISPATCH)`` tuple that
maps tool names to callable implementations.  SSH tools
are wired to the provided ``SSHClient`` instance; info
tools are imported from the existing ReportAgent.
"""
from typing import Any, Callable, Generator

from ccs_response_planner_backend.agents.report_agent.tools import (
    tavily_search,
    nvd_search,
    mitre_search,
    virustotal_scan,
    abuseipdb_check,
    otx_search,
)
from ccs_response_planner_backend.irbench.ssh_client import (
    SSHClient,
)

ToolDispatch = dict[str, Callable[..., dict[str, Any]]]
StreamDispatch = dict[
    str,
    Callable[..., Generator[dict[str, Any], None, None]],
]


def build_investigation_dispatch(
    ssh_client: SSHClient,
    info_tools_enabled: bool = True,
) -> tuple[ToolDispatch, StreamDispatch]:
    """
    Build tool dispatchers for the Investigator agent.

    :param ssh_client: SSH client for the target host
    :param info_tools_enabled: include external info tools
    :return: (TOOL_DISPATCH, STREAMING_TOOL_DISPATCH)
    """
    dispatch: ToolDispatch = {
        "ssh_exec": lambda command: (
            ssh_client.exec(command)
        ),
    }
    if info_tools_enabled:
        dispatch.update({
            "tavily_search": tavily_search,
            "nvd_search": nvd_search,
            "mitre_search": mitre_search,
            "virustotal_scan": virustotal_scan,
            "abuseipdb_check": abuseipdb_check,
            "otx_search": otx_search,
        })
    return dispatch, {}


def build_verifier_dispatch(
    ssh_client: SSHClient,
) -> tuple[ToolDispatch, StreamDispatch]:
    """
    Build tool dispatchers for the InvestigatorVerifier.

    The verifier has SSH access to verify the Investigator's
    findings on the actual target machine.

    :param ssh_client: SSH client for the target host
    :return: (TOOL_DISPATCH, STREAMING_TOOL_DISPATCH)
    """
    return {
        "ssh_exec": lambda command: (
            ssh_client.exec(command)
        ),
    }, {}
