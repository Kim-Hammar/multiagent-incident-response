"""
Gemini function-calling declarations for the PlannerAgent tools.
"""
from google.genai import types as genai_types  # type: ignore[attr-defined]

PYTHON_EXEC_DECL = genai_types.FunctionDeclaration(
    name="python_exec",
    description=(
        "Execute arbitrary Python code in a "
        "sandbox container. Use this for quick "
        "analysis, debugging, or inspecting the "
        "MDP code before training."
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

RL_TRAIN_DECL = genai_types.FunctionDeclaration(
    name="rl_train",
    description=(
        "Run RL training code in the Python "
        "sandbox with streaming progress. The "
        "code MUST print JSON progress lines "
        "to stdout. Use this for all RL "
        "training runs."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": (
                    "Python training script that prints "
                    "JSON progress lines to stdout."
                ),
            },
            "time_limit_minutes": {
                "type": "integer",
                "description": (
                    "Max training time in minutes. "
                    "Defaults to the UI-configured limit."
                ),
            },
            "algorithm": {
                "type": "string",
                "description": (
                    "Name of the RL algorithm being "
                    "used (e.g. PPO, A2C, DQN). "
                    "Displayed in the training chart."
                ),
            },
            "hyperparameters": {
                "type": "string",
                "description": (
                    "Key hyperparameters as a short "
                    "summary (e.g. 'n_steps=128, "
                    "batch_size=64, lr=3e-4'). "
                    "Displayed in the training chart."
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
        "plan based on the RL training results. "
        "Call this ONLY after rl_train has "
        "completed at least once."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "executive_summary": {
                "type": "string",
                "description": (
                    "Overall assessment of the incident "
                    "and the RL-derived response plan."
                ),
            },
            "algorithm": {
                "type": "string",
                "description": (
                    "RL algorithm used and rationale "
                    "for choosing it."
                ),
            },
            "hyperparameters": {
                "type": "string",
                "description": (
                    "Key hyperparameters used for "
                    "training."
                ),
            },
            "training_summary": {
                "type": "string",
                "description": (
                    "Summary of training: episodes, "
                    "final reward, convergence info."
                ),
            },
            "action_sequence": {
                "type": "array",
                "description": (
                    "Policy characterization as an "
                    "ordered response plan, grouped "
                    "by recovery phase."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "step": {
                            "type": "integer",
                            "description": (
                                "Step number."
                            ),
                        },
                        "phase": {
                            "type": "string",
                            "description": (
                                "Recovery phase this "
                                "step belongs to "
                                "(containment, assessment"
                                ", preservation, "
                                "eviction, hardening, "
                                "or restoration)."
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
                        "rationale": {
                            "type": "string",
                            "description": (
                                "Why the policy chose "
                                "this action at this "
                                "point, including what "
                                "happens if it fails "
                                "and what the fallback "
                                "would be."
                            ),
                        },
                        "spec_impact": {
                            "type": "string",
                            "description": (
                                "Impact on service "
                                "specifications, e.g. "
                                "'temporarily breaks "
                                "FTP connectivity but "
                                "necessary to contain "
                                "the attack'."
                            ),
                        },
                    },
                    "required": [
                        "step",
                        "phase",
                        "action",
                        "description",
                        "commands",
                        "rationale",
                        "spec_impact",
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
            "algorithm",
            "hyperparameters",
            "training_summary",
            "action_sequence",
            "expected_total_cost",
            "risks",
        ],
    },
)

ITERATING_DECLARATIONS = [
    PYTHON_EXEC_DECL,
    RL_TRAIN_DECL,
]

POST_TRAINING_DECLARATIONS = [
    PYTHON_EXEC_DECL,
    PRODUCE_PLANNER_REPORT_DECL,
]
