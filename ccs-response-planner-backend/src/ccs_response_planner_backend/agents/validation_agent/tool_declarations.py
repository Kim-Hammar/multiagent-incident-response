"""
Gemini function-calling declarations for the ValidationAgent tools.
"""
from google.genai import types as genai_types  # type: ignore[attr-defined]

TOOL_DECLARATIONS = [
    genai_types.FunctionDeclaration(
        name="dt_exec",
        description=(
            "Execute a shell command on a digital-twin "
            "container. Use this to apply response "
            "actions, inspect processes, check "
            "connectivity, and verify service state. "
            "Valid container names: gateway, firewall, "
            "ids, server_1, server_2, server_3, "
            "server_4, server_5, server_6."
        ),
        parameters={  # type: ignore[arg-type]
            "type": "object",
            "properties": {
                "container": {
                    "type": "string",
                    "description": (
                        "The host id of the container "
                        "(e.g. gateway, server_1)."
                    ),
                },
                "command": {
                    "type": "string",
                    "description": (
                        "The shell command to execute."
                    ),
                },
            },
            "required": ["container", "command"],
        },
    ),
    genai_types.FunctionDeclaration(
        name="produce_validation_report",
        description=(
            "Produce the final structured validation "
            "report. Call this ONLY after applying all "
            "response actions and checking recovery and "
            "service state after each action."
        ),
        parameters={  # type: ignore[arg-type]
            "type": "object",
            "properties": {
                "executive_summary": {
                    "type": "string",
                    "description": (
                        "High-level overview of the "
                        "validation results."
                    ),
                },
                "action_results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action_name": {
                                "type": "string",
                                "description": (
                                    "Name of the response "
                                    "action applied."
                                ),
                            },
                            "action_description": {
                                "type": "string",
                                "description": (
                                    "Description of what the "
                                    "action does."
                                ),
                            },
                            "commands_executed": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": (
                                    "Shell commands executed "
                                    "to apply this action."
                                ),
                            },
                            "outcome": {
                                "type": "string",
                                "description": (
                                    "Result of applying "
                                    "the action."
                                ),
                            },
                            "recovery_state": {
                                "type": "object",
                                "properties": {
                                    "is_attack_contained": {
                                        "type": "boolean",
                                    },
                                    "is_attack_assessed": {
                                        "type": "boolean",
                                    },
                                    "is_forensic_evidence_preserved": {
                                        "type": "boolean",
                                    },
                                    "is_attack_evicted": {
                                        "type": "boolean",
                                    },
                                    "is_system_hardened": {
                                        "type": "boolean",
                                    },
                                    "are_services_restored": {
                                        "type": "boolean",
                                    },
                                },
                                "required": [
                                    "is_attack_contained",
                                    "is_attack_assessed",
                                    "is_forensic_evidence_preserved",
                                    "is_attack_evicted",
                                    "is_system_hardened",
                                    "are_services_restored",
                                ],
                            },
                            "service_state": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "description": {
                                            "type": "string",
                                        },
                                        "passed": {
                                            "type": "boolean",
                                        },
                                    },
                                    "required": [
                                        "description",
                                        "passed",
                                    ],
                                },
                            },
                        },
                        "required": [
                            "action_name",
                            "action_description",
                            "commands_executed",
                            "outcome",
                            "recovery_state",
                            "service_state",
                        ],
                    },
                },
                "final_recovery_state": {
                    "type": "object",
                    "properties": {
                        "is_attack_contained": {
                            "type": "boolean",
                        },
                        "is_attack_assessed": {
                            "type": "boolean",
                        },
                        "is_forensic_evidence_preserved": {
                            "type": "boolean",
                        },
                        "is_attack_evicted": {
                            "type": "boolean",
                        },
                        "is_system_hardened": {
                            "type": "boolean",
                        },
                        "are_services_restored": {
                            "type": "boolean",
                        },
                    },
                    "required": [
                        "is_attack_contained",
                        "is_attack_assessed",
                        "is_forensic_evidence_preserved",
                        "is_attack_evicted",
                        "is_system_hardened",
                        "are_services_restored",
                    ],
                },
                "final_service_state": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                            },
                            "passed": {
                                "type": "boolean",
                            },
                        },
                        "required": [
                            "description", "passed",
                        ],
                    },
                },
                "overall_result": {
                    "type": "string",
                    "description": (
                        "One of: Plan fully validated, "
                        "Plan partially validated, "
                        "Plan validation failed."
                    ),
                },
                "recommendations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Recommendations for improving "
                        "the response plan."
                    ),
                },
            },
            "required": [
                "executive_summary",
                "action_results",
                "final_recovery_state",
                "final_service_state",
                "overall_result",
                "recommendations",
            ],
        },
    ),
]
