"""
Gemini function-calling declarations for the CodeReviewerAgent tools.
"""
from google.genai import types as genai_types  # type: ignore[attr-defined]

PYTHON_EXEC_DECL = genai_types.FunctionDeclaration(
    name="python_exec",
    description=(
        "Execute arbitrary Python code in a "
        "sandbox container. Use this to test "
        "the MDP — run episodes, check action "
        "effects, verify state transitions, "
        "and validate the reward function."
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

DT_EXEC_DECL = genai_types.FunctionDeclaration(
    name="dt_exec",
    description=(
        "Execute a shell command on a digital-twin "
        "container. Use this to verify that "
        "commands from the ACTION_TABLE actually "
        "work on the target hosts. Valid container "
        "names: i1_gateway, i1_firewall, i1_ids, "
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

PRODUCE_REVIEW_REPORT_DECL = genai_types.FunctionDeclaration(
    name="produce_review_report",
    description=(
        "Produce the final code review report. "
        "Call this ONLY after you have called at "
        "least one other tool (python_exec or "
        "dt_exec) to actually test the code."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "executive_summary": {
                "type": "string",
                "description": (
                    "Overall assessment of the MDP "
                    "code quality."
                ),
            },
            "findings": {
                "type": "array",
                "description": (
                    "Specific issues found during "
                    "the review."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": (
                                "Review dimension: "
                                "completeness, "
                                "transition_realism, "
                                "command_correctness, "
                                "specification_alignment, "
                                "action_prerequisites, "
                                "reward_function, or "
                                "code_quality."
                            ),
                        },
                        "severity": {
                            "type": "string",
                            "description": (
                                "Issue severity: "
                                "critical, major, "
                                "minor, or info."
                            ),
                        },
                        "description": {
                            "type": "string",
                            "description": (
                                "Description of the "
                                "issue found."
                            ),
                        },
                        "recommendation": {
                            "type": "string",
                            "description": (
                                "Recommended fix or "
                                "improvement."
                            ),
                        },
                    },
                    "required": [
                        "category",
                        "severity",
                        "description",
                        "recommendation",
                    ],
                },
            },
            "missing_actions": {
                "type": "array",
                "description": (
                    "Actions the MDP should include "
                    "but currently does not."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": (
                                "Short name for the "
                                "missing action."
                            ),
                        },
                        "description": {
                            "type": "string",
                            "description": (
                                "What the action does."
                            ),
                        },
                        "commands": {
                            "type": "array",
                            "description": (
                                "Shell commands to "
                                "implement this action."
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
                        "rationale": {
                            "type": "string",
                            "description": (
                                "Why this action "
                                "should be included."
                            ),
                        },
                    },
                    "required": [
                        "name",
                        "description",
                        "commands",
                        "rationale",
                    ],
                },
            },
            "command_issues": {
                "type": "array",
                "description": (
                    "Commands in ACTION_TABLE that "
                    "are broken or incorrect."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "action_name": {
                            "type": "string",
                            "description": (
                                "Name of the action "
                                "with the issue."
                            ),
                        },
                        "container": {
                            "type": "string",
                            "description": (
                                "Container the command "
                                "runs on."
                            ),
                        },
                        "command": {
                            "type": "string",
                            "description": (
                                "The problematic "
                                "command."
                            ),
                        },
                        "issue": {
                            "type": "string",
                            "description": (
                                "What is wrong with "
                                "the command."
                            ),
                        },
                        "fix": {
                            "type": "string",
                            "description": (
                                "The corrected command."
                            ),
                        },
                    },
                    "required": [
                        "action_name",
                        "container",
                        "command",
                        "issue",
                        "fix",
                    ],
                },
            },
            "strengths": {
                "type": "array",
                "description": (
                    "Things the code does well."
                ),
                "items": {
                    "type": "string",
                    "description": (
                        "A specific strength."
                    ),
                },
            },
            "overall_verdict": {
                "type": "string",
                "description": (
                    "Overall verdict: pass, "
                    "needs_revision, or "
                    "major_issues."
                ),
            },
        },
        "required": [
            "executive_summary",
            "findings",
            "missing_actions",
            "command_issues",
            "strengths",
            "overall_verdict",
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
    DT_EXEC_DECL,
    DT_RESTART_DECL,
]

ALL_DECLARATIONS = [
    PYTHON_EXEC_DECL,
    DT_EXEC_DECL,
    DT_RESTART_DECL,
    PRODUCE_REVIEW_REPORT_DECL,
]
