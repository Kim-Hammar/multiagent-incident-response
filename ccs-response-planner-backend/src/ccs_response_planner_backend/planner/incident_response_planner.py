"""
Incident response planning logic.
"""
from typing import Any


class IncidentResponsePlanner:
    """
    Generates incident response plans for cyber-security incidents.
    """

    def generate_plan(self, incident_description: str) -> dict[str, Any]:
        """
        Generate a response plan for the given incident.

        :param incident_description: a text description of the incident
        :return: a dict containing the response plan with steps, severity, and status
        """
        return {
            "incident_description": incident_description,
            "severity": "medium",
            "status": "planned",
            "steps": [
                "1. Identify and isolate affected systems",
                "2. Collect and preserve evidence",
                "3. Analyze the scope of the incident",
                "4. Contain the threat",
                "5. Eradicate the root cause",
                "6. Recover affected systems",
                "7. Document lessons learned",
            ],
        }
