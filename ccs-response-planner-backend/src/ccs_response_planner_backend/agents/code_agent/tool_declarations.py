"""
Gemini function-calling declarations for the CodeAgent tools.
"""
from google.genai import types as genai_types  # type: ignore[attr-defined]

PYTHON_EXEC_DECL = genai_types.FunctionDeclaration(
    name="python_exec",
    description=(
        "Execute arbitrary Python code in a "
        "sandbox container. Use this to write, "
        "test, and iterate on the Gymnasium "
        "environment code."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": (
                    "The Python source code to execute."
                ),
            },
        },
        "required": ["code"],
    },
)

GYM_VERIFY_DECL = genai_types.FunctionDeclaration(
    name="gym_verify",
    description=(
        "Verify the Gymnasium environment: checks "
        "required methods (reset, step, get_actions, "
        "set_state, get_action_mask), validates state "
        "shape and action mask format, and runs a "
        "greedy reachability test (using the action "
        "mask to skip invalid actions) to confirm the "
        "terminal state can be reached within 300 "
        "steps."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": (
                    "The Python source code of the "
                    "Gymnasium environment to verify."
                ),
            },
        },
        "required": ["code"],
    },
)

DT_EXEC_DECL = genai_types.FunctionDeclaration(
    name="dt_exec",
    description=(
        "Execute a shell command on a digital-twin "
        "container. Use this to test whether a "
        "specific incident response command works "
        "on a given host. Valid container names: "
        "i1_gateway, i1_firewall, i1_ids, "
        "i1_server_1–i1_server_6 (Incident 1) or "
        "i2_server_1–i2_server_6 (Incident 2)."
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

PRODUCE_CODE_REPORT_DECL = genai_types.FunctionDeclaration(
    name="produce_code_report",
    description=(
        "Produce the final code generation report. "
        "Call this ONLY after gym_verify returns a "
        "passing result."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "executive_summary": {
                "type": "string",
                "description": (
                    "High-level overview of the "
                    "generated environment."
                ),
            },
            "generated_code": {
                "type": "string",
                "description": (
                    "The complete Python source code "
                    "of the Gymnasium environment."
                ),
            },
            "actions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": (
                                "Name of the action."
                            ),
                        },
                        "description": {
                            "type": "string",
                            "description": (
                                "Description of what "
                                "the action does."
                            ),
                        },
                        "state_effect": {
                            "type": "string",
                            "description": (
                                "Effect on recovery "
                                "and specification "
                                "state dimensions."
                            ),
                        },
                        "success_probability": {
                            "type": "string",
                            "description": (
                                "Probability of the "
                                "action succeeding."
                            ),
                        },
                        "commands": {
                            "type": "array",
                            "description": (
                                "Shell commands from "
                                "ACTION_TABLE for this "
                                "action."
                            ),
                            "items": {
                                "type": "object",
                                "properties": {
                                    "container": {
                                        "type": "string",
                                    },
                                    "command": {
                                        "type": "string",
                                    },
                                },
                                "required": [
                                    "container",
                                    "command",
                                ],
                            },
                        },
                    },
                    "required": [
                        "name",
                        "description",
                        "state_effect",
                        "commands",
                    ],
                },
            },
            "state_description": {
                "type": "string",
                "description": (
                    "Description of the state space "
                    "and its dimensions."
                ),
            },
            "verification_result": {
                "type": "string",
                "description": (
                    "One-line overall summary, e.g. "
                    "'All 9 checks passed'."
                ),
            },
            "verification_checks": {
                "type": "array",
                "description": (
                    "Individual verification checks "
                    "from gym_verify. Copy every "
                    "entry from the gym_verify "
                    "result checks array."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "check": {
                            "type": "string",
                            "description": (
                                "Check identifier, "
                                "e.g. find_env_class."
                            ),
                        },
                        "passed": {
                            "type": "boolean",
                            "description": (
                                "Whether the check "
                                "passed."
                            ),
                        },
                        "detail": {
                            "type": "string",
                            "description": (
                                "Extra detail or "
                                "error message."
                            ),
                        },
                    },
                    "required": [
                        "check",
                        "passed",
                    ],
                },
            },
        },
        "required": [
            "executive_summary",
            "generated_code",
            "actions",
            "state_description",
            "verification_result",
            "verification_checks",
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

ITERATING_DECLARATIONS = [
    PYTHON_EXEC_DECL,
    GYM_VERIFY_DECL,
    DT_EXEC_DECL,
    DT_RESTART_DECL,
]

ALL_DECLARATIONS = [
    PYTHON_EXEC_DECL,
    GYM_VERIFY_DECL,
    DT_EXEC_DECL,
    DT_RESTART_DECL,
    PRODUCE_CODE_REPORT_DECL,
]
