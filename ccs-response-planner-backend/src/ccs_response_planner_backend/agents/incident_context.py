"""
Shared helper for building the incident context section.

When the report manager is enabled, agents receive the structured
incident report. When it is disabled, agents receive the raw
security alerts instead.
"""


def build_incident_context_section(
    report_manager_enabled: bool,
    incident_report: str,
    security_alerts: str,
) -> str:
    """
    Build the incident context section for agent prompts.

    :param report_manager_enabled: whether the report manager
        produced a structured incident report
    :param incident_report: the structured incident report
        (used when report_manager_enabled is True)
    :param security_alerts: the raw security alerts
        (used when report_manager_enabled is False)
    :return: the formatted incident context section
    """
    if report_manager_enabled:
        return (
            "### Incident Report\n"
            + (incident_report or "N/A")
        )
    return (
        "### Security Alerts\n"
        "The following are raw security alerts — no "
        "structured incident assessment has been produced. "
        "Analyze these alerts directly to understand the "
        "nature and scope of the incident.\n"
        + (security_alerts or "N/A")
    )
