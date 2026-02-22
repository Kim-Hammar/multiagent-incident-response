"""
Gemini function-calling declarations for the PlanManagerAgent tools.
"""
from google.genai import types as genai_types  # type: ignore[attr-defined]

RUN_CODE_MANAGER_DECL = genai_types.FunctionDeclaration(
    name="run_code_manager",
    description=(
        "Run the CodeManager agent to orchestrate MDP "
        "environment code generation via the CodeAgent "
        "and CodeReviewerAgent. On revision iterations, "
        "provide validation_feedback describing the "
        "issues found during validation so the CodeManager "
        "can revise the MDP code."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "validation_feedback": {
                "type": "string",
                "description": (
                    "Feedback from the validation phase "
                    "describing issues to fix in the "
                    "MDP code. Only needed on revision "
                    "iterations."
                ),
            },
        },
        "required": [],
    },
)

RUN_PLANNER_AGENT_DECL = genai_types.FunctionDeclaration(
    name="run_planner_agent",
    description=(
        "Run the Planner Agent to train a reinforcement "
        "learning policy on the MDP environment. "
        "Requires that run_code_manager has completed "
        "successfully first."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {},
        "required": [],
    },
)

RUN_VALIDATION_AGENT_DECL = genai_types.FunctionDeclaration(
    name="run_validation_agent",
    description=(
        "Run the Validation Agent to test the response "
        "plan on the digital twin. Requires that "
        "run_planner_agent has completed successfully first."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {},
        "required": [],
    },
)

PRODUCE_PLAN_MANAGER_REPORT_DECL = genai_types.FunctionDeclaration(
    name="produce_plan_manager_report",
    description=(
        "Produce the final pipeline report. Call this "
        "ONLY after at least one full pipeline cycle "
        "(CodeManager + Planner Agent + Validation Agent)."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "executive_summary": {
                "type": "string",
                "description": (
                    "High-level summary of the full "
                    "pipeline process and outcome."
                ),
            },
            "iterations": {
                "type": "integer",
                "description": (
                    "Number of full pipeline iterations "
                    "performed."
                ),
            },
            "final_verdict": {
                "type": "string",
                "description": (
                    "Final verdict: pass, "
                    "needs_revision, or "
                    "major_issues."
                ),
            },
            "code_manager_summary": {
                "type": "string",
                "description": (
                    "Summary of the MDP code "
                    "generation phase."
                ),
            },
            "planner_agent_summary": {
                "type": "string",
                "description": (
                    "Summary of the RL training "
                    "phase and computed policy."
                ),
            },
            "validation_summary": {
                "type": "string",
                "description": (
                    "Summary of the validation "
                    "phase results."
                ),
            },
        },
        "required": [
            "executive_summary",
            "iterations",
            "final_verdict",
            "code_manager_summary",
            "planner_agent_summary",
            "validation_summary",
        ],
    },
)

ITERATING_DECLARATIONS = [
    RUN_CODE_MANAGER_DECL,
    RUN_PLANNER_AGENT_DECL,
    RUN_VALIDATION_AGENT_DECL,
]

ALL_DECLARATIONS = [
    RUN_CODE_MANAGER_DECL,
    RUN_PLANNER_AGENT_DECL,
    RUN_VALIDATION_AGENT_DECL,
    PRODUCE_PLAN_MANAGER_REPORT_DECL,
]
