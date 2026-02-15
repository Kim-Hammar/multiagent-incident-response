"""
Gemini function-calling declarations for the ValidationAgent tools.

Provides two declaration lists: ``TOOL_DECLARATIONS`` for sequence
mode (dt_exec + report) and ``TOOL_DECLARATIONS_WITH_POLICY`` for
policy mode (dt_exec + query_policy + report).
"""
from google.genai import types as genai_types  # type: ignore[attr-defined]

DT_EXEC_DECL = genai_types.FunctionDeclaration(
    name="dt_exec",
    description=(
        "Execute a shell command on a digital-twin "
        "container. Use this to apply response "
        "actions, inspect processes, check "
        "connectivity, and verify service state. "
        "Valid container names: i1_gateway, "
        "i1_firewall, i1_ids, "
        "i1_server_1\u2013i1_server_6 (Incident 1) or "
        "i2_server_1\u2013i2_server_6 (Incident 2)."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "container": {
                "type": "string",
                "description": (
                    "The host id of the container "
                    "(e.g. i1_firewall, i1_server_1)."
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
)

QUERY_POLICY_DECL = genai_types.FunctionDeclaration(
    name="query_policy",
    description=(
        "Query the trained RL policy for the next "
        "action given the current state vector. "
        "First 6 values are recovery phases "
        "(containment, assessment, preservation, "
        "eviction, hardening, restoration) each "
        "0.0-1.0. Remaining values are specification "
        "states (1.0 = passing, 0.0 = failing)."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "state": {
                "type": "array",
                "items": {"type": "number"},
                "description": (
                    "Current state vector."
                ),
            },
        },
        "required": ["state"],
    },
)

PRODUCE_REPORT_DECL = genai_types.FunctionDeclaration(
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
                        "actual_step_cost": {
                            "type": "number",
                            "description": (
                                "Actual cost for this step: "
                                "1 + number of failed "
                                "specification commands."
                            ),
                        },
                    },
                    "required": [
                        "action_name",
                        "action_description",
                        "commands_executed",
                        "outcome",
                        "recovery_state",
                        "service_state",
                        "actual_step_cost",
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
            "actual_total_cost": {
                "type": "number",
                "description": (
                    "Total actual cost from digital "
                    "twin execution (sum of all "
                    "per-step costs)."
                ),
            },
            "simulated_total_cost": {
                "type": "number",
                "description": (
                    "Expected total cost from the "
                    "RL agent report."
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
            "actual_total_cost",
            "simulated_total_cost",
        ],
    },
)

DT_RESTART_DECL = genai_types.FunctionDeclaration(
    name="dt_restart",
    description=(
        "Restart a digital-twin container that has "
        "crashed or stopped. Use when dt_exec fails "
        "with a 'container is not running' error. "
        "Pass a specific container name to restart "
        "just that host, or pass 'all' to redeploy "
        "the entire digital twin."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "container": {
                "type": "string",
                "description": (
                    "The host id to restart "
                    "(e.g. i1_server_2), or 'all' "
                    "to redeploy the entire DT."
                ),
            },
        },
        "required": ["container"],
    },
)

TOOL_DECLARATIONS = [
    DT_EXEC_DECL, DT_RESTART_DECL, PRODUCE_REPORT_DECL,
]

TOOL_DECLARATIONS_WITH_POLICY = [
    DT_EXEC_DECL,
    DT_RESTART_DECL,
    QUERY_POLICY_DECL,
    PRODUCE_REPORT_DECL,
]
