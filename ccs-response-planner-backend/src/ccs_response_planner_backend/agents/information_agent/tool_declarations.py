"""
Gemini function-calling declarations for the InformationAgent tools.
"""
from google.genai import types as genai_types  # type: ignore[attr-defined]

TOOL_DECLARATIONS = [
    genai_types.FunctionDeclaration(
        name="tavily_search",
        description=(
            "Search the web for current information about cyber "
            "threats, vulnerabilities, or security topics."
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
                        "Maximum number of results to return "
                        "(default 5)."
                    ),
                },
            },
            "required": ["query"],
        },
    ),
    genai_types.FunctionDeclaration(
        name="nvd_search",
        description=(
            "Search the NIST National Vulnerability Database for "
            "CVE entries by CVE ID or keyword."
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
    ),
    genai_types.FunctionDeclaration(
        name="mitre_search",
        description=(
            "Search the MITRE ATT&CK framework for techniques "
            "by technique ID or keyword."
        ),
        parameters={  # type: ignore[arg-type]
            "type": "object",
            "properties": {
                "technique_id": {
                    "type": "string",
                    "description": (
                        "An ATT&CK technique ID (e.g. T1059)."
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
    ),
    genai_types.FunctionDeclaration(
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
    ),
    genai_types.FunctionDeclaration(
        name="abuseipdb_check",
        description=(
            "Check an IP address against the AbuseIPDB database "
            "for abuse reports and reputation."
        ),
        parameters={  # type: ignore[arg-type]
            "type": "object",
            "properties": {
                "ip": {
                    "type": "string",
                    "description": "The IP address to check.",
                },
            },
            "required": ["ip"],
        },
    ),
    genai_types.FunctionDeclaration(
        name="otx_search",
        description=(
            "Search AlienVault OTX for threat intelligence on "
            "an indicator (IP, domain, hash, CVE, etc.)."
        ),
        parameters={  # type: ignore[arg-type]
            "type": "object",
            "properties": {
                "indicator_type": {
                    "type": "string",
                    "description": (
                        "The indicator type: IPv4, IPv6, "
                        "domain, hostname, url, hash, or cve."
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
    ),
    genai_types.FunctionDeclaration(
        name="produce_assessment",
        description=(
            "Produce the final structured incident assessment. "
            "Call this ONLY after gathering enough information "
            "from multiple investigation tools."
        ),
        parameters={  # type: ignore[arg-type]
            "type": "object",
            "properties": {
                "incident_summary": {
                    "type": "string",
                    "description": (
                        "Brief overview of the incident."
                    ),
                },
                "attack_vector_analysis": {
                    "type": "string",
                    "description": (
                        "How the attacker gained access and "
                        "what techniques were used."
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
                                    "Context about this IOC."
                                ),
                            },
                        },
                        "required": [
                            "type", "value", "context",
                        ],
                    },
                },
                "severity": {
                    "type": "string",
                    "description": (
                        "Severity: Critical, High, "
                        "Medium, or Low."
                    ),
                },
                "severity_justification": {
                    "type": "string",
                    "description": (
                        "Why this severity was chosen."
                    ),
                },
                "affected_assets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "asset": {
                                "type": "string",
                                "description": (
                                    "The asset name."
                                ),
                            },
                            "impact": {
                                "type": "string",
                                "description": (
                                    "Impact on this asset."
                                ),
                            },
                        },
                        "required": ["asset", "impact"],
                    },
                },
            },
            "required": [
                "incident_summary",
                "attack_vector_analysis",
                "indicators_of_compromise",
                "severity",
                "severity_justification",
                "affected_assets",
            ],
        },
    ),
]
