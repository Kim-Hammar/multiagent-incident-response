"""
Gemini function-calling declarations for the HostAnalyzerAgent tools.

Provides ``TOOL_DECLARATIONS`` containing investigation tools
(tavily, nvd, mitre, virustotal, abuseipdb, otx, dt_exec,
dt_python_exec, dt_restart) plus produce_host_analysis.
Does NOT include generate_attack_image (single-host agent).
"""
from google.genai import types as genai_types  # type: ignore[attr-defined]

from response_planner_backend.agents.report_agent.tool_declarations import (
    TOOL_DECLARATIONS as REPORT_TOOL_DECLARATIONS,
)

# Reuse all ReportAgent tool declarations except
# generate_attack_image, produce_assessment, and
# run_host_analyzers (orchestration tool that spawns
# HostAnalyzerAgent sub-agents — must not be recursive).
_EXCLUDED = {
    "generate_attack_image",
    "produce_assessment",
    "run_host_analyzers",
}
_INHERITED_DECLS = [
    d for d in REPORT_TOOL_DECLARATIONS
    if d.name not in _EXCLUDED
]

PRODUCE_HOST_ANALYSIS_DECL = genai_types.FunctionDeclaration(
    name="produce_host_analysis",
    description=(
        "Produce the final structured host analysis report. "
        "Call this ONLY after gathering enough information "
        "from multiple investigation tools."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "host_name": {
                "type": "string",
                "description": (
                    "Name or identifier of the "
                    "analyzed host."
                ),
            },
            "compromise_status": {
                "type": "string",
                "description": (
                    "One of: Confirmed Compromised, "
                    "Likely Compromised, Possibly "
                    "Compromised, No Evidence of "
                    "Compromise."
                ),
            },
            "compromise_details": {
                "type": "string",
                "description": (
                    "Detailed explanation of how the "
                    "host was or may have been "
                    "compromised."
                ),
            },
            "attack_vectors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "vector": {
                            "type": "string",
                            "description": (
                                "Name of the attack "
                                "vector."
                            ),
                        },
                        "description": {
                            "type": "string",
                            "description": (
                                "How this attack "
                                "vector was used."
                            ),
                        },
                        "evidence": {
                            "type": "string",
                            "description": (
                                "Evidence supporting "
                                "this attack vector."
                            ),
                        },
                    },
                    "required": [
                        "vector", "description",
                        "evidence",
                    ],
                },
            },
            "security_posture": {
                "type": "string",
                "description": (
                    "Overall security posture "
                    "assessment of the host."
                ),
            },
            "indicators_of_compromise": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": (
                                "IOC type: ip, domain, "
                                "hash, cve, or other."
                            ),
                        },
                        "value": {
                            "type": "string",
                            "description": (
                                "The IOC value."
                            ),
                        },
                        "context": {
                            "type": "string",
                            "description": (
                                "Context about this "
                                "IOC."
                            ),
                        },
                    },
                    "required": [
                        "type", "value", "context",
                    ],
                },
            },
            "affected_services": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": (
                                "Name of the affected "
                                "service."
                            ),
                        },
                        "status": {
                            "type": "string",
                            "description": (
                                "Current status of "
                                "the service."
                            ),
                        },
                        "impact": {
                            "type": "string",
                            "description": (
                                "Impact on this "
                                "service."
                            ),
                        },
                    },
                    "required": [
                        "service", "status", "impact",
                    ],
                },
            },
            "recommendations": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Actionable recommendations for "
                    "securing or remediating this host."
                ),
            },
            "executive_summary": {
                "type": "string",
                "description": (
                    "Brief executive summary of the "
                    "host analysis findings."
                ),
            },
        },
        "required": [
            "host_name",
            "compromise_status",
            "compromise_details",
            "attack_vectors",
            "security_posture",
            "indicators_of_compromise",
            "affected_services",
            "recommendations",
            "executive_summary",
        ],
    },
)

TOOL_DECLARATIONS = _INHERITED_DECLS + [
    PRODUCE_HOST_ANALYSIS_DECL,
]
