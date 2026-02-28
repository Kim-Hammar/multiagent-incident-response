"""
Gemini function-calling declarations for the ReportManagerAgent tools.
"""
from google.genai import types as genai_types  # type: ignore[attr-defined]

RUN_REPORT_AGENT_DECL = genai_types.FunctionDeclaration(
    name="run_report_agent",
    description=(
        "Run the ReportAgent to generate (or revise) "
        "an incident assessment report. On the first "
        "call, omit both parameters. On revision "
        "iterations, provide previous_assessment and "
        "review_feedback so the agent can improve "
        "the report."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "previous_assessment": {
                "type": "string",
                "description": (
                    "The assessment from the previous "
                    "report, for revision iterations."
                ),
            },
            "review_feedback": {
                "type": "string",
                "description": (
                    "A concise, high-level summary "
                    "of the reviewer's findings — "
                    "use short bullet points listing "
                    "only the issues that need fixing "
                    "and what the reviewer recommended. "
                    "Do NOT paste the raw reviewer "
                    "output verbatim."
                ),
            },
        },
        "required": [],
    },
)

RUN_REPORT_REVIEWER_AGENT_DECL = genai_types.FunctionDeclaration(
    name="run_report_reviewer_agent",
    description=(
        "Run the ReportReviewerAgent to review the "
        "most recently generated incident assessment. "
        "The assessment is automatically extracted "
        "from the previous run_report_agent result. "
        "On re-review iterations, provide "
        "previous_review_summary so the reviewer "
        "knows what was already checked and can "
        "focus on verifying fixes and new issues."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "previous_review_summary": {
                "type": "string",
                "description": (
                    "A concise summary of the "
                    "previous review's findings "
                    "and what was already "
                    "validated. Include: which "
                    "checks passed, which issues "
                    "were found, and the verdict. "
                    "Omit on the first review."
                ),
            },
        },
        "required": [],
    },
)

_PRODUCE_REPORT_PARAMS = {  # type: ignore[var-annotated]
    "type": "object",
    "properties": {
        "executive_summary": {
            "type": "string",
            "description": (
                "Brief summary of the "
                "orchestration process and "
                "outcome (include how many "
                "generate-review iterations "
                "were performed)."
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
                "Overall verdict: pass, "
                "fail, or partial."
            ),
        },
        "report_summary": {
            "type": "string",
            "description": (
                "Summary of the final "
                "incident assessment report."
            ),
        },
        "review_summary": {
            "type": "string",
            "description": (
                "Summary of the final "
                "review findings."
            ),
        },
    },
    "required": [
        "executive_summary",
        "iterations",
        "final_verdict",
        "report_summary",
        "review_summary",
    ],
}

PRODUCE_REPORT_MANAGER_REPORT_DECL = (
    genai_types.FunctionDeclaration(
        name="produce_report_manager_report",
        description=(
            "Produce the final orchestration report. "
            "Call this ONLY after at least one review "
            "cycle has completed (both run_report_agent "
            "and run_report_reviewer_agent)."
        ),
        parameters=_PRODUCE_REPORT_PARAMS,  # type: ignore[arg-type]
    )
)

PRODUCE_REPORT_NO_REVIEWER_DECL = (
    genai_types.FunctionDeclaration(
        name="produce_report_manager_report",
        description=(
            "Produce the final orchestration report. "
            "Call this after run_report_agent has "
            "completed at least once."
        ),
        parameters=_PRODUCE_REPORT_PARAMS,  # type: ignore[arg-type]
    )
)

ITERATING_DECLARATIONS = [
    RUN_REPORT_AGENT_DECL,
    RUN_REPORT_REVIEWER_AGENT_DECL,
]

ALL_DECLARATIONS = [
    RUN_REPORT_AGENT_DECL,
    RUN_REPORT_REVIEWER_AGENT_DECL,
    PRODUCE_REPORT_MANAGER_REPORT_DECL,
]

ALL_DECLARATIONS_NO_REVIEWER = [
    RUN_REPORT_AGENT_DECL,
    PRODUCE_REPORT_NO_REVIEWER_DECL,
]
