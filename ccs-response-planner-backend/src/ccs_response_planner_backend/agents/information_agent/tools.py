"""
Standalone tool functions for the InformationAgent.

Each function encapsulates the SDK call logic extracted from
the corresponding route handler, reads its API key from the
environment, and returns a plain dict (no Flask dependency).
"""
import base64
import os
import tempfile
from typing import Any, Callable, Generator

import docker
import nvdlib
import requests as http_requests
import vt
from mitreattack.stix20 import MitreAttackData
from OTXv2 import IndicatorTypes, OTXv2
from tavily import TavilyClient

from google import genai  # type: ignore[attr-defined]
from google.genai import types as genai_types  # type: ignore[attr-defined]

from ccs_response_planner_backend.agents.shared_tools import (
    dt_exec,
    dt_exec_stream,
    dt_restart,
    dt_restart_stream,
)
from ccs_response_planner_backend.constants.constants import DOCKER, LLM
from ccs_response_planner_backend.db.database_facade import (
    DatabaseFacade,
)

_STIX_URL = (
    "https://raw.githubusercontent.com/mitre/cti"
    "/master/enterprise-attack/enterprise-attack.json"
)
_STIX_CACHE = os.path.join(
    tempfile.gettempdir(), "enterprise-attack.json",
)

_ABUSEIPDB_BASE_URL = "https://api.abuseipdb.com/api/v2"

_OTX_TYPE_MAP = {
    "IPv4": IndicatorTypes.IPv4,
    "IPv6": IndicatorTypes.IPv6,
    "domain": IndicatorTypes.DOMAIN,
    "hostname": IndicatorTypes.HOSTNAME,
    "url": IndicatorTypes.URL,
    "hash": IndicatorTypes.FILE_HASH_SHA256,
    "cve": IndicatorTypes.CVE,
}

_VT_VALID_TYPES = {"ip", "domain", "url", "hash"}


def tavily_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """
    Search the web via the Tavily API.

    :param query: the search query
    :param max_results: maximum number of results to return
    :return: a dict with query, results list, and response_time
    """
    api_key = os.environ.get("TAVILY_API_KEY", "")
    client = TavilyClient(api_key=api_key)
    result = client.search(query=query.strip(), max_results=max_results)
    results = [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", ""),
            "score": r.get("score", 0),
        }
        for r in result.get("results", [])
    ]
    return {
        "query": query.strip(),
        "results": results,
        "response_time": result.get("response_time"),
    }


def nvd_search(
    cve_id: str = "", keyword: str = "", results_per_page: int = 5,
) -> dict[str, Any]:
    """
    Search the NVD database by CVE ID or keyword.

    :param cve_id: a specific CVE identifier to look up
    :param keyword: a keyword to search for
    :param results_per_page: max results when searching by keyword
    :return: a dict with query and results list
    """
    api_key = os.environ.get("NVD_API_KEY")
    kwargs: dict[str, Any] = {}
    if api_key:
        kwargs["key"] = api_key
    if cve_id:
        kwargs["cveId"] = cve_id.strip()
        query = cve_id.strip()
    else:
        kwargs["keywordSearch"] = keyword.strip()
        kwargs["limit"] = results_per_page
        query = keyword.strip()
    cve_list = list(nvdlib.searchCVE(**kwargs))
    results = []
    for cve in cve_list:
        desc = ""
        for d in getattr(cve, "descriptions", []):
            if getattr(d, "lang", "") == "en":
                desc = getattr(d, "value", "")
                break
        score = getattr(cve, "v31score", None)
        results.append({
            "id": getattr(cve, "id", ""),
            "description": desc,
            "score": score,
            "published": getattr(cve, "published", ""),
            "url": (
                f"https://nvd.nist.gov/vuln/detail/"
                f"{getattr(cve, 'id', '')}"
            ),
        })
    return {"query": query, "results": results}


def _get_attack_data() -> MitreAttackData:
    """
    Load the MITRE ATT&CK STIX data bundle, downloading on first use.

    :return: a MitreAttackData instance
    """
    if not os.path.exists(_STIX_CACHE):
        resp = http_requests.get(_STIX_URL, timeout=60)
        resp.raise_for_status()
        with open(_STIX_CACHE, "wb") as f:
            f.write(resp.content)
    return MitreAttackData(_STIX_CACHE)


def _technique_to_dict(technique: Any) -> dict[str, Any]:
    """
    Convert a MITRE ATT&CK technique STIX object to a dict.

    :param technique: a STIX technique object
    :return: a dict with id, name, description, tactics, and url
    """
    ext_refs = getattr(technique, "external_references", [])
    attack_id = ""
    url = ""
    for ref in ext_refs:
        if getattr(ref, "source_name", "") == "mitre-attack":
            attack_id = getattr(ref, "external_id", "")
            url = getattr(ref, "url", "")
            break
    phases = getattr(technique, "kill_chain_phases", [])
    tactics = [getattr(p, "phase_name", "") for p in phases]
    desc = getattr(technique, "description", "") or ""
    if len(desc) > 500:
        desc = desc[:500] + "..."
    return {
        "id": attack_id,
        "name": getattr(technique, "name", ""),
        "description": desc,
        "tactics": tactics,
        "url": url,
    }


def mitre_search(
    technique_id: str = "", search: str = "",
) -> dict[str, Any]:
    """
    Search MITRE ATT&CK techniques by ID or keyword.

    :param technique_id: an ATT&CK technique ID (e.g. T1059)
    :param search: a keyword to search for in technique names/descriptions
    :return: a dict with query and results list
    """
    attack_data = _get_attack_data()
    results = []
    if technique_id:
        query = technique_id.strip()
        technique = attack_data.get_object_by_attack_id(
            query, "attack-pattern",
        )
        if technique:
            results.append(_technique_to_dict(technique))
    else:
        query = search.strip()
        keyword_lower = query.lower()
        for t in attack_data.get_techniques():
            name = getattr(t, "name", "") or ""
            desc = getattr(t, "description", "") or ""
            if (keyword_lower in name.lower()
                    or keyword_lower in desc.lower()):
                results.append(_technique_to_dict(t))
    return {"query": query, "results": results}


def virustotal_scan(
    scan_type: str, value: str,
) -> dict[str, Any]:
    """
    Look up a resource on VirusTotal by type and value.

    :param scan_type: one of ip, domain, url, hash
    :param value: the indicator value to look up
    :return: a dict with the scan result
    """
    if scan_type not in _VT_VALID_TYPES:
        raise ValueError(
            f"type must be one of: {', '.join(sorted(_VT_VALID_TYPES))}"
        )
    path_map = {
        "ip": f"/ip_addresses/{value}",
        "domain": f"/domains/{value}",
        "url": f"/urls/{vt.url_id(value)}",
        "hash": f"/files/{value}",
    }
    api_key = os.environ.get("VIRUSTOTAL_API_KEY", "")
    if not api_key:
        raise ValueError(
            "VIRUSTOTAL_API_KEY environment variable not set"
        )
    client = vt.Client(api_key)
    try:
        obj = client.get_object(path_map[scan_type])
    finally:
        client.close()
    raw_stats = getattr(obj, "last_analysis_stats", None)
    result: dict[str, Any] = {
        "type": scan_type,
        "value": value,
        "reputation": getattr(obj, "reputation", None),
        "last_analysis_stats": (
            dict(raw_stats) if raw_stats else None
        ),
        "last_analysis_date": getattr(
            obj, "last_analysis_date", None,
        ),
    }
    if result["last_analysis_date"] is not None:
        result["last_analysis_date"] = str(
            result["last_analysis_date"]
        )
    return {"result": result}


def abuseipdb_check(ip: str) -> dict[str, Any]:
    """
    Check an IP address against the AbuseIPDB database.

    :param ip: the IP address to check
    :return: a dict with the check result
    """
    api_key = os.environ.get("ABUSEIPDB_API_KEY", "")
    if not api_key:
        raise ValueError(
            "ABUSEIPDB_API_KEY environment variable not set"
        )
    resp = http_requests.get(
        f"{_ABUSEIPDB_BASE_URL}/check",
        headers={"Key": api_key, "Accept": "application/json"},
        params={"ipAddress": ip.strip()},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json().get("data", {})
    return {
        "result": {
            "ip": data.get("ipAddress", ip.strip()),
            "abuse_confidence_score": data.get(
                "abuseConfidenceScore",
            ),
            "isp": data.get("isp", ""),
            "country_code": data.get("countryCode", ""),
            "total_reports": data.get("totalReports", 0),
            "last_reported_at": data.get("lastReportedAt"),
            "is_public": data.get("isPublic", False),
        },
    }


def otx_search(
    indicator_type: str, value: str,
) -> dict[str, Any]:
    """
    Search OTX for an indicator (IP, domain, hash, CVE, etc.).

    :param indicator_type: one of IPv4, IPv6, domain, hostname,
                           url, hash, cve
    :param value: the indicator value to look up
    :return: a dict with the search result
    """
    if indicator_type not in _OTX_TYPE_MAP:
        raise ValueError(
            f"type must be one of: "
            f"{', '.join(sorted(_OTX_TYPE_MAP.keys()))}"
        )
    api_key = os.environ.get("OTX_API_KEY", "")
    if not api_key:
        raise ValueError(
            "OTX_API_KEY environment variable not set"
        )
    otx = OTXv2(api_key)
    details = otx.get_indicator_details_full(
        _OTX_TYPE_MAP[indicator_type], value.strip(),
    )
    general = details.get("general", {})
    pulse_info = general.get("pulse_info", {})
    pulses = pulse_info.get("pulses", [])
    return {
        "result": {
            "type": indicator_type,
            "value": value.strip(),
            "pulse_count": pulse_info.get("count", 0),
            "reputation": general.get("reputation", None),
            "pulses": [
                {
                    "name": p.get("name", ""),
                    "description": (
                        (p.get("description", "") or "")[:200]
                    ),
                    "created": p.get("created", ""),
                    "tags": p.get("tags", [])[:5],
                }
                for p in pulses[:10]
            ],
        },
    }


def _ensure_python_sandbox(
    client: docker.DockerClient,
) -> docker.models.containers.Container:
    """
    Ensure the Python sandbox container is running.

    If the container does not exist it is created from the sandbox
    image.  If it exists but is stopped it is started.

    :param client: a Docker client instance
    :return: the running sandbox container
    """
    try:
        container = client.containers.get(
            DOCKER.PYTHON_SANDBOX_CONTAINER,
        )
        if container.status != "running":
            container.start()
        return container
    except docker.errors.NotFound:
        container = client.containers.run(
            DOCKER.PYTHON_SANDBOX_IMAGE,
            name=DOCKER.PYTHON_SANDBOX_CONTAINER,
            detach=True,
        )
        return container


def dt_python_exec(code: str) -> dict[str, Any]:
    """
    Execute Python code in the sandbox container.

    :param code: the Python source code to run
    :return: a dict with code, exit_code, and output
    """
    client = docker.from_env()
    ct = _ensure_python_sandbox(client)
    encoded = base64.b64encode(
        code.encode("utf-8"),
    ).decode("ascii")
    write_cmd = (
        f"python3 -c \"import base64; "
        f"open('/workspace/_code.py','wb')"
        f".write(base64.b64decode('{encoded}'))\""
    )
    client.api.exec_start(
        client.api.exec_create(
            ct.id, ["/bin/sh", "-c", write_cmd],
            stdout=True, stderr=True,
        )["Id"],
    )
    run_cmd = "python /workspace/_code.py"
    exec_id = client.api.exec_create(
        ct.id, ["/bin/sh", "-c", run_cmd],
        stdout=True, stderr=True,
    )["Id"]
    output = client.api.exec_start(exec_id).decode(
        "utf-8", errors="replace",
    )
    exit_code = client.api.exec_inspect(exec_id)["ExitCode"]
    return {
        "code": code,
        "exit_code": exit_code,
        "output": output,
    }


def generate_attack_image(
    prompt: str, incident_id: int | None = None,
) -> dict[str, Any]:
    """
    Generate an attack path diagram using AI image generation.

    If *incident_id* is provided the topology image from the
    corresponding example incident is used as a reference so
    that the attack path is overlaid on the network diagram.

    :param prompt: description of the attack path to illustrate
    :param incident_id: optional example incident id for the
                        topology image
    :return: a dict with ``image`` (base64 data URL) and
             ``prompt``, or ``error`` and ``prompt`` on failure
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")
    client = genai.Client(api_key=api_key)

    contents: list[Any] = []

    if incident_id is not None:
        try:
            example = DatabaseFacade.get_example_incident(
                incident_id,
            )
            if example:
                img_url = example.get(
                    "system_description_image", "",
                )
                if img_url and img_url.startswith(
                    "data:image/",
                ):
                    header, b64data = img_url.split(",", 1)
                    mime = header.split(":")[1].split(";")[0]
                    raw = base64.b64decode(b64data)
                    contents.append(
                        genai_types.Part.from_bytes(
                            data=raw, mime_type=mime,
                        ),
                    )
        except Exception:
            pass

    image_prompt = (
        "Generate a professional network security diagram that "
        "visualizes the following cyber-attack path. Draw each "
        "host as a labeled box or node showing its IP address "
        "and role (e.g. 'Server 3 — SSH', 'Server 6 — Samba'). "
        "Connect the hosts with bold red directional arrows "
        "showing the order of compromise. Label each arrow with "
        "the technique or exploit used at that step (e.g. "
        "'SSH Brute Force', 'CVE-2017-7494 SambaCry', "
        "'SQL Injection'). Use a clean, dark-on-light color "
        "scheme suitable for an incident report. Group hosts by "
        "network zone if applicable. Include a title at the top: "
        "'Attack Path Diagram'.\n\n"
        f"Attack path to illustrate:\n{prompt}"
    )
    contents.append(image_prompt)

    try:
        response = client.models.generate_content(
            model=LLM.IMAGE_GENERATION_MODEL,
            contents=contents,
            config=genai_types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )
        candidates = response.candidates or []
        if not candidates:
            return {
                "error": (
                    "Image generation returned no candidates."
                ),
                "prompt": prompt,
            }
        content = candidates[0].content
        parts = (content.parts if content else None) or []
        for part in parts:
            if (part.inline_data is not None
                    and part.inline_data.data is not None):
                img_b64 = base64.b64encode(
                    part.inline_data.data,
                ).decode("ascii")
                mime = part.inline_data.mime_type or (
                    "image/png"
                )
                return {
                    "image": f"data:{mime};base64,{img_b64}",
                    "prompt": prompt,
                }
        return {
            "error": (
                "Image generation produced no image output."
            ),
            "prompt": prompt,
        }
    except Exception as exc:
        return {"error": str(exc), "prompt": prompt}


TOOL_DISPATCH: dict[str, Callable[..., dict[str, Any]]] = {
    "tavily_search": tavily_search,
    "nvd_search": nvd_search,
    "mitre_search": mitre_search,
    "virustotal_scan": virustotal_scan,
    "abuseipdb_check": abuseipdb_check,
    "otx_search": otx_search,
    "dt_exec": dt_exec,
    "dt_restart": dt_restart,
    "dt_python_exec": dt_python_exec,
    "generate_attack_image": generate_attack_image,
}

STREAMING_TOOL_DISPATCH: dict[
    str, Callable[..., Generator[dict[str, Any], None, None]]
] = {
    "dt_exec": dt_exec_stream,
    "dt_restart": dt_restart_stream,
}
