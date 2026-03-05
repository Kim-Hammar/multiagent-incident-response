"""
Gemini function-calling declarations for the OrchestratorAgent tools.
"""
from google.genai import types as genai_types  # type: ignore[attr-defined]

RUN_REPORT_MANAGER_DECL = genai_types.FunctionDeclaration(
    name="run_report_manager",
    description=(
        "Run the ReportManager agent to orchestrate "
        "incident assessment generation and review "
        "via the ReportAgent and ReportVerifierAgent. "
        "The ReportManager handles the internal "
        "generate-review-revise loop and returns "
        "the final reviewed assessment."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {},
        "required": [],
    },
)

RUN_PENTEST_AGENT_DECL = genai_types.FunctionDeclaration(
    name="run_pentest_agent",
    description=(
        "Run the PentestAgent to validate the attack "
        "path from the incident assessment against "
        "the digital twin. Call this after "
        "run_report_manager completes to check "
        "whether the identified attack path is "
        "actually feasible."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {},
        "required": [],
    },
)

RUN_PLAN_MANAGER_DECL = genai_types.FunctionDeclaration(
    name="run_plan_manager",
    description=(
        "Run the PlanManager agent to orchestrate "
        "the full response planning pipeline: MDP "
        "code generation, RL policy training, and "
        "validation on the digital twin. Requires "
        "that run_report_manager has completed "
        "successfully first."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {},
        "required": [],
    },
)

PRODUCE_ORCHESTRATOR_AGENT_REPORT_DECL = (
    genai_types.FunctionDeclaration(
        name="produce_orchestrator_agent_report",
        description=(
            "Produce the final consolidated incident "
            "response report. Call this ONLY after "
            "both the ReportManager and PlanManager "
            "have completed."
        ),
        parameters={  # type: ignore[arg-type]
            "type": "object",
            "properties": {
                "executive_summary": {
                    "type": "string",
                    "description": (
                        "High-level summary of the full "
                        "end-to-end incident response "
                        "process and outcome."
                    ),
                },
                "iterations": {
                    "type": "integer",
                    "description": (
                        "Number of full orchestrator "
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
                "assessment_summary": {
                    "type": "string",
                    "description": (
                        "Summary of the incident "
                        "assessment phase."
                    ),
                },
                "response_plan_summary": {
                    "type": "string",
                    "description": (
                        "Summary of the response "
                        "planning phase."
                    ),
                },
            },
            "required": [
                "executive_summary",
                "iterations",
                "final_verdict",
                "assessment_summary",
                "response_plan_summary",
            ],
        },
    )
)

ITERATING_DECLARATIONS = [
    RUN_REPORT_MANAGER_DECL,
    RUN_PENTEST_AGENT_DECL,
]

MID_DECLARATIONS = [
    RUN_REPORT_MANAGER_DECL,
    RUN_PENTEST_AGENT_DECL,
    RUN_PLAN_MANAGER_DECL,
]

ALL_DECLARATIONS = [
    RUN_REPORT_MANAGER_DECL,
    RUN_PENTEST_AGENT_DECL,
    RUN_PLAN_MANAGER_DECL,
    PRODUCE_ORCHESTRATOR_AGENT_REPORT_DECL,
]
