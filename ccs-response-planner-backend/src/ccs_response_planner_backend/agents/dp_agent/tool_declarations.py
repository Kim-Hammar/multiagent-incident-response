"""
Gemini function-calling declarations for the DpAgent tools.
"""
from google.genai import types as genai_types  # type: ignore[attr-defined]

PYTHON_EXEC_DECL = genai_types.FunctionDeclaration(
    name="python_exec",
    description=(
        "Execute arbitrary Python code in a "
        "sandbox container. Use this for quick "
        "analysis, debugging, or inspecting the "
        "MDP code before solving."
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

DP_SOLVE_DECL = genai_types.FunctionDeclaration(
    name="dp_solve",
    description=(
        "Run DP value iteration code in the "
        "Python sandbox with streaming progress. "
        "The code MUST print JSON progress lines "
        "to stdout. Use this for all DP "
        "solving runs."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": (
                    "Python solving script that prints "
                    "JSON progress lines to stdout."
                ),
            },
            "time_limit_minutes": {
                "type": "integer",
                "description": (
                    "Max solving time in minutes. "
                    "Defaults to the UI-configured limit."
                ),
            },
            "method": {
                "type": "string",
                "description": (
                    "Name of the DP method being "
                    "used (e.g. value_iteration). "
                    "Displayed in the convergence chart."
                ),
            },
            "parameters": {
                "type": "string",
                "description": (
                    "Key parameters as a short "
                    "summary (e.g. 'bins=10, "
                    "gamma=0.99, theta=1e-6'). "
                    "Displayed in the convergence chart."
                ),
            },
        },
        "required": ["code"],
    },
)

PRODUCE_PLANNER_REPORT_DECL = genai_types.FunctionDeclaration(
    name="produce_planner_report",
    description=(
        "Produce the final incident response "
        "plan based on the DP value iteration "
        "results. Call this ONLY after dp_solve "
        "has completed at least once."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "executive_summary": {
                "type": "string",
                "description": (
                    "Overall assessment of the incident "
                    "and the DP-derived response plan."
                ),
            },
            "method": {
                "type": "string",
                "description": (
                    "DP method used and rationale "
                    "for choosing it."
                ),
            },
            "parameters": {
                "type": "string",
                "description": (
                    "Key parameters used for "
                    "solving."
                ),
            },
            "solving_summary": {
                "type": "string",
                "description": (
                    "Summary of solving: iterations, "
                    "convergence, Bellman error."
                ),
            },
            "action_sequence": {
                "type": "array",
                "description": (
                    "Ordered incident response plan "
                    "derived from the optimal policy."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "step": {
                            "type": "integer",
                            "description": (
                                "Step number in the "
                                "sequence."
                            ),
                        },
                        "action": {
                            "type": "string",
                            "description": (
                                "Name of the action."
                            ),
                        },
                        "description": {
                            "type": "string",
                            "description": (
                                "What this action does."
                            ),
                        },
                        "commands": {
                            "type": "array",
                            "description": (
                                "Shell commands that "
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
                        "expected_effect": {
                            "type": "string",
                            "description": (
                                "Expected effect on "
                                "the system state."
                            ),
                        },
                    },
                    "required": [
                        "step",
                        "action",
                        "description",
                        "commands",
                        "expected_effect",
                    ],
                },
            },
            "contingencies": {
                "type": "array",
                "description": (
                    "Fallback actions if primary "
                    "actions fail."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "condition": {
                            "type": "string",
                            "description": (
                                "When this contingency "
                                "applies."
                            ),
                        },
                        "alternative_action": {
                            "type": "string",
                            "description": (
                                "The alternative action "
                                "to take."
                            ),
                        },
                        "rationale": {
                            "type": "string",
                            "description": (
                                "Why this alternative "
                                "is appropriate."
                            ),
                        },
                    },
                    "required": [
                        "condition",
                        "alternative_action",
                        "rationale",
                    ],
                },
            },
            "expected_total_cost": {
                "type": "number",
                "description": (
                    "Expected total cost when "
                    "following this plan (cost = "
                    "-reward, i.e. the negated "
                    "cumulative reward)."
                ),
            },
            "risks": {
                "type": "array",
                "description": (
                    "Key risks and limitations of "
                    "the plan."
                ),
                "items": {
                    "type": "string",
                    "description": (
                        "A specific risk or limitation."
                    ),
                },
            },
        },
        "required": [
            "executive_summary",
            "method",
            "parameters",
            "solving_summary",
            "action_sequence",
            "contingencies",
            "expected_total_cost",
            "risks",
        ],
    },
)

ITERATING_DECLARATIONS = [
    PYTHON_EXEC_DECL,
    DP_SOLVE_DECL,
]

ALL_DECLARATIONS = [
    PYTHON_EXEC_DECL,
    DP_SOLVE_DECL,
    PRODUCE_PLANNER_REPORT_DECL,
]
