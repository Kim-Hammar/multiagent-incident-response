"""
Gemini function-calling declarations for the ActionValidatorAgent.

Provides ``TOOL_DECLARATIONS`` containing dt_exec, dt_restart,
and produce_action_validation.
"""
from google.genai import types as genai_types  # type: ignore[attr-defined]

from ccs_response_planner_backend.agents.validation_agent.tool_declarations import (
    DT_EXEC_DECL,
    DT_RESTART_DECL,
)

PRODUCE_ACTION_VALIDATION_DECL = genai_types.FunctionDeclaration(
    name="produce_action_validation",
    description=(
        "Produce the final structured action validation "
        "report. Call this ONLY after executing the "
        "action's commands on the digital twin and "
        "verifying the intended effect."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "action_name": {
                "type": "string",
                "description": (
                    "Name of the action that was "
                    "validated."
                ),
            },
            "action_description": {
                "type": "string",
                "description": (
                    "Description of what the action "
                    "does and its intended effect."
                ),
            },
            "commands_executed": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Shell commands executed to apply "
                    "this action."
                ),
            },
            "command_results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": (
                                "The shell command that "
                                "was executed."
                            ),
                        },
                        "container": {
                            "type": "string",
                            "description": (
                                "The container on which "
                                "the command ran."
                            ),
                        },
                        "exit_code": {
                            "type": "number",
                            "description": (
                                "The exit code of the "
                                "command."
                            ),
                        },
                        "output": {
                            "type": "string",
                            "description": (
                                "The stdout/stderr "
                                "output of the command."
                            ),
                        },
                    },
                    "required": [
                        "command", "container",
                        "exit_code", "output",
                    ],
                },
            },
            "outcome": {
                "type": "string",
                "description": (
                    "One of: Action validated, "
                    "Action partially validated, "
                    "Action failed."
                ),
            },
            "executive_summary": {
                "type": "string",
                "description": (
                    "Brief summary of what happened: "
                    "was the intended effect achieved, "
                    "were there side-effects."
                ),
            },
            "recovery_state_before": {
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
                "description": (
                    "Recovery state BEFORE applying "
                    "the action."
                ),
            },
            "recovery_state_after": {
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
                "description": (
                    "Recovery state AFTER applying "
                    "the action."
                ),
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
                        "description", "passed",
                    ],
                },
                "description": (
                    "Service specification check "
                    "results after applying the "
                    "action."
                ),
            },
            "step_cost": {
                "type": "number",
                "description": (
                    "Phase-weighted cost for this "
                    "action step."
                ),
            },
            "recommendations": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Recommendations for improving "
                    "or adjusting this action."
                ),
            },
        },
        "required": [
            "action_name",
            "action_description",
            "commands_executed",
            "command_results",
            "outcome",
            "recovery_state_before",
            "recovery_state_after",
            "service_state",
            "step_cost",
            "executive_summary",
            "recommendations",
        ],
    },
)

TOOL_DECLARATIONS = [
    DT_EXEC_DECL,
    DT_RESTART_DECL,
    PRODUCE_ACTION_VALIDATION_DECL,
]
