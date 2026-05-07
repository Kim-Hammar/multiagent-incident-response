"""
Gemini function-calling declarations for IRBench tools.

Replaces Docker-specific tools (dt_exec, dt_restart, etc.)
with ``ssh_exec`` for remote host execution, and adds
``produce_irbench_report`` for structured subtask answers.

Info-tool declarations (tavily, NVD, MITRE, etc.) are
imported from the existing ReportAgent declarations.
"""
from google.genai import types as genai_types  # type: ignore[attr-defined]

# ── SSH execution (replaces dt_exec) ─────────────────────

SSH_EXEC_DECLARATION = genai_types.FunctionDeclaration(
    name="ssh_exec",
    description=(
        "Execute a shell command on the target machine "
        "via SSH. Use this to inspect processes, network "
        "connections, logs, services, file systems, and "
        "to perform remediation actions. Commands are "
        "killed after the configured timeout."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": (
                    "The shell command to execute on "
                    "the target machine."
                ),
            },
        },
        "required": ["command"],
    },
)

# ── Info tools (reused from existing ReportAgent) ────────

TAVILY_DECLARATION = genai_types.FunctionDeclaration(
    name="tavily_search",
    description=(
        "Search the web for current information about "
        "cyber threats, vulnerabilities, or security "
        "topics."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query string.",
            },
            "max_results": {
                "type": "integer",
                "description": (
                    "Maximum number of results to "
                    "return (default 5)."
                ),
            },
        },
        "required": ["query"],
    },
)

NVD_DECLARATION = genai_types.FunctionDeclaration(
    name="nvd_search",
    description=(
        "Search the NIST National Vulnerability Database "
        "for CVE entries by CVE ID or keyword."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "cve_id": {
                "type": "string",
                "description": (
                    "A specific CVE identifier "
                    "(e.g. CVE-2021-44228)."
                ),
            },
            "keyword": {
                "type": "string",
                "description": (
                    "A keyword to search for in CVE "
                    "descriptions."
                ),
            },
        },
    },
)

MITRE_DECLARATION = genai_types.FunctionDeclaration(
    name="mitre_search",
    description=(
        "Search the MITRE ATT&CK framework for "
        "techniques by technique ID or keyword."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "technique_id": {
                "type": "string",
                "description": (
                    "An ATT&CK technique ID "
                    "(e.g. T1059)."
                ),
            },
            "search": {
                "type": "string",
                "description": (
                    "A keyword to search in technique "
                    "names and descriptions."
                ),
            },
        },
    },
)

VIRUSTOTAL_DECLARATION = genai_types.FunctionDeclaration(
    name="virustotal_scan",
    description=(
        "Look up an indicator on VirusTotal (IP address, "
        "domain, URL, or file hash)."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "scan_type": {
                "type": "string",
                "description": (
                    "The type of indicator: ip, domain, "
                    "url, or hash."
                ),
            },
            "value": {
                "type": "string",
                "description": (
                    "The indicator value to look up."
                ),
            },
        },
        "required": ["scan_type", "value"],
    },
)

ABUSEIPDB_DECLARATION = genai_types.FunctionDeclaration(
    name="abuseipdb_check",
    description=(
        "Check an IP address against the AbuseIPDB "
        "database for abuse reports and reputation."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "ip": {
                "type": "string",
                "description": (
                    "The IP address to check."
                ),
            },
        },
        "required": ["ip"],
    },
)

OTX_DECLARATION = genai_types.FunctionDeclaration(
    name="otx_search",
    description=(
        "Search AlienVault OTX for threat intelligence "
        "on an indicator (IP, domain, hash, CVE, etc.)."
    ),
    parameters={  # type: ignore[arg-type]
        "type": "object",
        "properties": {
            "indicator_type": {
                "type": "string",
                "description": (
                    "The indicator type: IPv4, IPv6, "
                    "domain, hostname, url, hash, "
                    "or cve."
                ),
            },
            "value": {
                "type": "string",
                "description": (
                    "The indicator value to look up."
                ),
            },
        },
        "required": ["indicator_type", "value"],
    },
)

# ── Subtask answer tool ──────────────────────────────────

PRODUCE_SUBTASK_ANSWER_DECLARATION = (
    genai_types.FunctionDeclaration(
        name="produce_subtask_answer",
        description=(
            "Submit your answer for the current subtask. "
            "Call this when you have found the answer or "
            "completed the required action."
        ),
        parameters={  # type: ignore[arg-type]
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": (
                        "Your answer or finding for "
                        "this subtask."
                    ),
                },
                "evidence": {
                    "type": "string",
                    "description": (
                        "Evidence supporting the answer "
                        "(command output, log entries, "
                        "etc.)."
                    ),
                },
                "action_taken": {
                    "type": "string",
                    "description": (
                        "For response/recovery tasks: "
                        "what action was executed."
                    ),
                },
                "completed": {
                    "type": "boolean",
                    "description": (
                        "Whether this subtask was "
                        "completed successfully."
                    ),
                },
            },
            "required": ["answer", "completed"],
        },
    )
)

# ── Grouped declaration lists ────────────────────────────

INFO_TOOL_DECLARATIONS = [
    TAVILY_DECLARATION,
    NVD_DECLARATION,
    MITRE_DECLARATION,
    VIRUSTOTAL_DECLARATION,
    ABUSEIPDB_DECLARATION,
    OTX_DECLARATION,
]

INVESTIGATION_DECLARATIONS = (
    [SSH_EXEC_DECLARATION]
    + INFO_TOOL_DECLARATIONS
    + [PRODUCE_SUBTASK_ANSWER_DECLARATION]
)

INVESTIGATION_DECLARATIONS_NO_INFO = [
    SSH_EXEC_DECLARATION,
    PRODUCE_SUBTASK_ANSWER_DECLARATION,
]

# For InvestigatorVerifier: SSH access to verify findings
# on the target, plus the final verification report.
VERIFIER_DECLARATIONS = [
    SSH_EXEC_DECLARATION,
    genai_types.FunctionDeclaration(
        name="produce_verification_report",
        description=(
            "Submit your verification of the "
            "Investigator's report. Include a verdict "
            "and per-subtask feedback."
        ),
        parameters={  # type: ignore[arg-type]
            "type": "object",
            "properties": {
                "verdict": {
                    "type": "string",
                    "description": (
                        "Either 'approved' or "
                        "'needs_revision'."
                    ),
                },
                "summary": {
                    "type": "string",
                    "description": (
                        "Brief overall assessment of "
                        "the report quality."
                    ),
                },
                "subtask_feedback": {
                    "type": "array",
                    "description": (
                        "Per-subtask feedback. Only "
                        "include subtasks that need "
                        "correction."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "task_number": {
                                "type": "integer",
                                "description": (
                                    "The subtask number."
                                ),
                            },
                            "issue": {
                                "type": "string",
                                "description": (
                                    "What is wrong or "
                                    "missing."
                                ),
                            },
                            "suggestion": {
                                "type": "string",
                                "description": (
                                    "What the Investigator "
                                    "should do differently."
                                ),
                            },
                        },
                        "required": [
                            "task_number",
                            "issue",
                        ],
                    },
                },
            },
            "required": [
                "verdict",
                "summary",
            ],
        },
    ),
]
