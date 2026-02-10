"""
Gemini function-calling declarations for the PenetrationTestAgent tools.
"""
from google.genai import types as genai_types  # type: ignore[attr-defined]

TOOL_DECLARATIONS = [
    genai_types.FunctionDeclaration(
        name="pentest_exec",
        description=(
            "Execute a shell command on the attacker "
            "machine (120s timeout). Use this to scan "
            "networks, probe services, attempt exploits, "
            "pivot through compromised hosts, and perform "
            "all penetration testing activities. Keep "
            "commands fast and targeted."
        ),
        parameters={  # type: ignore[arg-type]
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": (
                        "The shell command to execute "
                        "on the attacker machine."
                    ),
                },
            },
            "required": ["command"],
        },
    ),
    genai_types.FunctionDeclaration(
        name="produce_report",
        description=(
            "Produce the final structured penetration test "
            "report. Call this ONLY after thoroughly testing "
            "the system and identifying all attack paths."
        ),
        parameters={  # type: ignore[arg-type]
            "type": "object",
            "properties": {
                "executive_summary": {
                    "type": "string",
                    "description": (
                        "High-level overview of the "
                        "penetration test results."
                    ),
                },
                "attack_paths": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": (
                                    "Name of the attack path."
                                ),
                            },
                            "description": {
                                "type": "string",
                                "description": (
                                    "Description of the "
                                    "attack path."
                                ),
                            },
                            "steps": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": (
                                    "Ordered steps in the "
                                    "attack path."
                                ),
                            },
                            "severity": {
                                "type": "string",
                                "description": (
                                    "Severity: Critical, "
                                    "High, Medium, or Low."
                                ),
                            },
                            "compromised_assets": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": (
                                    "Assets compromised via "
                                    "this path."
                                ),
                            },
                        },
                        "required": [
                            "name", "description", "steps",
                            "severity", "compromised_assets",
                        ],
                    },
                },
                "vulnerabilities_found": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "vulnerability": {
                                "type": "string",
                                "description": (
                                    "Name or description of "
                                    "the vulnerability."
                                ),
                            },
                            "affected_asset": {
                                "type": "string",
                                "description": (
                                    "The asset affected by "
                                    "this vulnerability."
                                ),
                            },
                            "severity": {
                                "type": "string",
                                "description": (
                                    "Severity: Critical, "
                                    "High, Medium, or Low."
                                ),
                            },
                            "remediation": {
                                "type": "string",
                                "description": (
                                    "Recommended remediation "
                                    "steps."
                                ),
                            },
                        },
                        "required": [
                            "vulnerability",
                            "affected_asset",
                            "severity",
                            "remediation",
                        ],
                    },
                },
                "compromised_servers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "List of servers that were "
                        "successfully compromised."
                    ),
                },
                "recommendations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Remediation recommendations."
                    ),
                },
            },
            "required": [
                "executive_summary",
                "attack_paths",
                "vulnerabilities_found",
                "compromised_servers",
                "recommendations",
            ],
        },
    ),
]
