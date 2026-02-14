"""
Gemini function-calling declarations for the CodeManagerAgent tools.
"""
from google.genai import types as genai_types  # type: ignore[attr-defined]

RUN_CODE_AGENT_DECL = genai_types.FunctionDeclaration(
    name="run_code_agent",
    description=(
        "Run the CodeAgent to generate (or revise) "
        "a Gymnasium MDP environment for incident "
        "response recovery. On the first call, omit "
        "both parameters. On revision iterations, "
        "provide previous_code and review_feedback "
        "so the agent can improve the code."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "previous_code": {
                "type": "string",
                "description": (
                    "The generated_code from the previous "
                    "code report, for revision iterations."
                ),
            },
            "review_feedback": {
                "type": "string",
                "description": (
                    "The reviewer's findings and "
                    "recommendations to address in "
                    "the revision."
                ),
            },
        },
        "required": [],
    },
)

RUN_CODE_REVIEWER_AGENT_DECL = genai_types.FunctionDeclaration(
    name="run_code_reviewer_agent",
    description=(
        "Run the CodeReviewerAgent to review the "
        "most recently generated MDP environment "
        "code. The code report is automatically "
        "extracted from the previous run_code_agent "
        "result."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {},
        "required": [],
    },
)

PRODUCE_ORCHESTRATOR_REPORT_DECL = genai_types.FunctionDeclaration(
    name="produce_orchestrator_report",
    description=(
        "Produce the final orchestration report. "
        "Call this ONLY after at least one review "
        "cycle has completed (both run_code_agent "
        "and run_code_reviewer_agent)."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "executive_summary": {
                "type": "string",
                "description": (
                    "High-level summary of the "
                    "orchestration process and "
                    "outcome."
                ),
            },
            "iterations": {
                "type": "integer",
                "description": (
                    "Number of generate-review "
                    "iterations performed."
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
            "code_report_summary": {
                "type": "string",
                "description": (
                    "Summary of the final code "
                    "generation report."
                ),
            },
            "review_report_summary": {
                "type": "string",
                "description": (
                    "Summary of the final review "
                    "report findings."
                ),
            },
        },
        "required": [
            "executive_summary",
            "iterations",
            "final_verdict",
            "code_report_summary",
            "review_report_summary",
        ],
    },
)

ITERATING_DECLARATIONS = [
    RUN_CODE_AGENT_DECL,
    RUN_CODE_REVIEWER_AGENT_DECL,
]

ALL_DECLARATIONS = [
    RUN_CODE_AGENT_DECL,
    RUN_CODE_REVIEWER_AGENT_DECL,
    PRODUCE_ORCHESTRATOR_REPORT_DECL,
]
