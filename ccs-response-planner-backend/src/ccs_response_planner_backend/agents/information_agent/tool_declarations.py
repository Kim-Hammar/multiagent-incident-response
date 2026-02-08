"""
Gemini function-calling declarations for the InformationAgent tools.
"""
from google.generativeai.types import FunctionDeclaration

TOOL_DECLARATIONS = [
    FunctionDeclaration(
        name="tavily_search",
        description=(
            "Search the web for current information about cyber "
            "threats, vulnerabilities, or security topics."
        ),
        parameters={
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
    FunctionDeclaration(
        name="nvd_search",
        description=(
            "Search the NIST National Vulnerability Database for "
            "CVE entries by CVE ID or keyword."
        ),
        parameters={
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
    FunctionDeclaration(
        name="mitre_search",
        description=(
            "Search the MITRE ATT&CK framework for techniques "
            "by technique ID or keyword."
        ),
        parameters={
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
    FunctionDeclaration(
        name="virustotal_scan",
        description=(
            "Look up an indicator on VirusTotal (IP address, "
            "domain, URL, or file hash)."
        ),
        parameters={
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
    FunctionDeclaration(
        name="abuseipdb_check",
        description=(
            "Check an IP address against the AbuseIPDB database "
            "for abuse reports and reputation."
        ),
        parameters={
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
    FunctionDeclaration(
        name="otx_search",
        description=(
            "Search AlienVault OTX for threat intelligence on "
            "an indicator (IP, domain, hash, CVE, etc.)."
        ),
        parameters={
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
]
