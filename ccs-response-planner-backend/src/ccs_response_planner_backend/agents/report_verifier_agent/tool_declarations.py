"""
Gemini function-calling declarations for the ReportVerifierAgent.

Imports all investigation tool declarations from the ReportAgent
and adds the ``produce_report_review`` final tool.  Two lists are
exposed for two-phase tool gating:

- ``ITERATING_DECLARATIONS`` — all tools except produce_report_review
- ``ALL_DECLARATIONS`` — adds produce_report_review after the agent
  has used at least one investigation tool
"""
from google.genai import types as genai_types  # type: ignore[attr-defined]

from ccs_response_planner_backend.agents.report_agent.tool_declarations import (
    TOOL_DECLARATIONS as _REPORT_TOOL_DECLARATIONS,
)

# All investigation tools (everything except produce_assessment)
_INVESTIGATION_DECLARATIONS = [
    d for d in _REPORT_TOOL_DECLARATIONS
    if d.name not in ("produce_assessment", "generate_attack_image")
]

PRODUCE_REPORT_REVIEW_DECL = genai_types.FunctionDeclaration(
    name="produce_report_review",
    description=(
        "Produce the final incident report review. "
        "Call this ONLY after you have called at "
        "least one investigation tool to verify "
        "claims in the report."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "executive_summary": {
                "type": "string",
                "description": (
                    "Overall assessment of the "
                    "incident report quality."
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
                                "evidence_quality, "
                                "severity_accuracy, "
                                "attack_vector_analysis, "
                                "affected_assets, "
                                "factual_accuracy, or "
                                "actionability."
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
            "missing_elements": {
                "type": "array",
                "description": (
                    "Elements missing from the "
                    "incident report."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "element": {
                            "type": "string",
                            "description": (
                                "What is missing from "
                                "the report."
                            ),
                        },
                        "description": {
                            "type": "string",
                            "description": (
                                "Details about the "
                                "missing element."
                            ),
                        },
                        "importance": {
                            "type": "string",
                            "description": (
                                "Why this element "
                                "matters."
                            ),
                        },
                        "recommendation": {
                            "type": "string",
                            "description": (
                                "How to address the "
                                "missing element."
                            ),
                        },
                    },
                    "required": [
                        "element",
                        "description",
                        "importance",
                        "recommendation",
                    ],
                },
            },
            "evidence_gaps": {
                "type": "array",
                "description": (
                    "Claims in the report that "
                    "lack sufficient evidence."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "claim": {
                            "type": "string",
                            "description": (
                                "The claim made in "
                                "the report."
                            ),
                        },
                        "section": {
                            "type": "string",
                            "description": (
                                "Which section of the "
                                "report (e.g. "
                                "attack_vector_analysis)."
                            ),
                        },
                        "issue": {
                            "type": "string",
                            "description": (
                                "What is wrong with "
                                "the evidence."
                            ),
                        },
                        "suggestion": {
                            "type": "string",
                            "description": (
                                "How to improve the "
                                "evidence."
                            ),
                        },
                    },
                    "required": [
                        "claim",
                        "section",
                        "issue",
                        "suggestion",
                    ],
                },
            },
            "strengths": {
                "type": "array",
                "description": (
                    "Things the report does well."
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
            "missing_elements",
            "evidence_gaps",
            "strengths",
            "overall_verdict",
        ],
    },
)

ITERATING_DECLARATIONS = list(_INVESTIGATION_DECLARATIONS)

ALL_DECLARATIONS = list(_INVESTIGATION_DECLARATIONS) + [
    PRODUCE_REPORT_REVIEW_DECL,
]
