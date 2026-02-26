"""
Standalone tool functions for the ReportAgent.

Each function encapsulates the SDK call logic extracted from
the corresponding route handler, reads its API key from the
environment, and returns a plain dict (no Flask dependency).
"""
import base64
import logging
import os
import queue
import tempfile
import threading
import time
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

import httpx

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

_logger = logging.getLogger(__name__)

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
        "Below is an incident report description. Generate an "
        "image that illustrates the attack path. The image "
        "should have one box/component representing the "
        "attacker's starting point, with arrows going to boxes "
        "representing servers in the system. Each arrow should "
        "be labeled with the attack method used at that step. "
        "Each box/component should include information about "
        "the server, e.g. IP address, name, network zone, and "
        "services running on it.\n\n"
        f"Incident report:\n{prompt}"
    )
    contents.append(image_prompt)

    try:
        response = client.models.generate_content(
            model=LLM.IMAGE_GENERATION_MODEL,
            contents=contents,
            config=genai_types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
                image_config=genai_types.ImageConfig(
                    image_size="1K",
                ),
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


_MAX_INNER_STEPS = 50
_CONCURRENCY_LIMIT = 3
_OUTPUT_LIMIT = 2000


def _truncate_sub_result(
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    Return a copy of a tool result with long strings truncated.

    :param result: the original tool result dict
    :return: a truncated copy of the result
    """
    out: dict[str, Any] = {}
    for key, val in result.items():
        if key == "image":
            out[key] = val
        elif (
            isinstance(val, str) and len(val) > _OUTPUT_LIMIT
        ):
            out[key] = (
                val[:_OUTPUT_LIMIT] + "... (truncated)"
            )
        else:
            out[key] = val
    return out


def _run_single_host_analyzer(
    host: dict[str, Any],
    context: dict[str, Any],
    event_queue: "queue.Queue[dict[str, Any]]",
    semaphore: threading.Semaphore,
) -> None:
    """
    Run a HostAnalyzerAgent for a single host in a thread.

    Puts tagged sub_event dicts onto *event_queue*. When
    finished, puts an ``_agent_done`` sentinel.

    :param host: dict with host_id and host_description
    :param context: incident context (system_description,
        security_alerts, etc.)
    :param event_queue: shared queue for emitting events
    :param semaphore: limits concurrent LLM API calls
    """
    from ccs_response_planner_backend.agents.host_analyzer_agent.agent import (  # noqa: E501
        HostAnalyzerAgent,
    )

    agent_id = host.get("host_id", "unknown")
    agent_label = f"Analysis of host {agent_id}"

    try:
        agent = HostAnalyzerAgent()
        conversation_history: list[dict[str, Any]] = []
        host_analysis = None

        for step_num in range(_MAX_INNER_STEPS):
            step_reasoning = ""
            step_start = time.monotonic()

            ha_kwargs: dict[str, Any] = {
                "system_description": context.get(
                    "system_description", "",
                ),
                "security_alerts": context.get(
                    "security_alerts", "",
                ),
                "operator_feedback": context.get(
                    "operator_feedback", "",
                ),
                "host_description": (
                    host.get("host_description", "")
                ),
                "conversation_history": (
                    conversation_history
                ),
                "images": context.get("images"),
                "model_name": context.get(
                    "host_analyzer_model",
                ),
                "dt_config": context.get("dt_config"),
                "info_tools_enabled": context.get(
                    "info_tools_enabled", True,
                ),
            }

            with semaphore:
                try:
                    for event in agent.step_stream(
                        **ha_kwargs,
                    ):
                        etype = event.get("type")

                        if etype == "system_prompt":
                            event_queue.put({
                                "type": "sub_event",
                                "agent_id": agent_id,
                                "agent_label": (
                                    agent_label
                                ),
                                "event": {
                                    "type": "prompt",
                                    "text": event.get(
                                        "text", "",
                                    ),
                                    "images": event.get(
                                        "images", [],
                                    ),
                                },
                            })
                        elif etype == "thinking":
                            step_reasoning += event.get(
                                "delta", "",
                            )
                            event_queue.put({
                                "type": "sub_event",
                                "agent_id": agent_id,
                                "agent_label": (
                                    agent_label
                                ),
                                "event": {
                                    "type": (
                                        "thinking_delta"
                                    ),
                                    "text": event.get(
                                        "delta", "",
                                    ),
                                },
                            })
                        elif etype == "text":
                            step_reasoning += event.get(
                                "delta", "",
                            )
                        elif etype == "host_analysis":
                            host_analysis = event.get(
                                "host_analysis", {},
                            )
                            if step_reasoning:
                                conversation_history.append({
                                    "role": "model",
                                    "type": "reasoning",
                                    "text": (
                                        step_reasoning
                                    ),
                                })
                                step_reasoning = ""
                            conversation_history.append({
                                "role": "model",
                                "type": "host_analysis",
                                "host_analysis": (
                                    host_analysis
                                ),
                            })
                            event_queue.put({
                                "type": "sub_event",
                                "agent_id": agent_id,
                                "agent_label": (
                                    agent_label
                                ),
                                "event": {
                                    "type": "report",
                                    "host_analysis": (
                                        host_analysis
                                    ),
                                },
                            })
                        elif etype == "context_usage":
                            event_queue.put({
                                "type": "sub_event",
                                "agent_id": agent_id,
                                "agent_label": (
                                    agent_label
                                ),
                                "event": {
                                    "type": (
                                        "context_usage"
                                    ),
                                    "prompt_tokens": (
                                        event.get(
                                            "prompt_tokens",
                                            0,
                                        )
                                    ),
                                    "candidates_tokens": (
                                        event.get(
                                            "candidates_tokens",
                                            0,
                                        )
                                    ),
                                    "total_tokens": (
                                        event.get(
                                            "total_tokens",
                                            0,
                                        )
                                    ),
                                    "context_limit": (
                                        event.get(
                                            "context_limit",
                                            0,
                                        )
                                    ),
                                },
                            })
                        elif etype == "tool_proposal":
                            tool_name = event.get(
                                "tool_name", "",
                            )
                            tool_args = event.get(
                                "tool_args", {},
                            )
                            event_queue.put({
                                "type": "sub_event",
                                "agent_id": agent_id,
                                "agent_label": (
                                    agent_label
                                ),
                                "event": {
                                    "type": "tool_call",
                                    "tool_name": (
                                        tool_name
                                    ),
                                    "tool_args": (
                                        tool_args
                                    ),
                                },
                            })
                            if step_reasoning:
                                conversation_history.append({
                                    "role": "model",
                                    "type": "reasoning",
                                    "text": (
                                        step_reasoning
                                    ),
                                })
                                step_reasoning = ""
                            conversation_history.append({
                                "role": "model",
                                "type": "tool_proposal",
                                "tool_name": tool_name,
                                "tool_args": tool_args,
                                "rationale": event.get(
                                    "rationale", "",
                                ),
                                "_model_parts": (
                                    event.get(
                                        "_model_parts",
                                    )
                                ),
                                "_vendor": event.get(
                                    "_vendor",
                                ),
                            })
                            conversation_history.append({
                                "role": "user",
                                "type": "tool_approval",
                                "tool_name": tool_name,
                                "approved": True,
                            })
                            try:
                                result = (
                                    agent.execute_tool(
                                        tool_name,
                                        tool_args,
                                    )
                                )
                                tool_result = result.get(
                                    "result", {},
                                )
                                if result.get("error"):
                                    tool_result = {
                                        "error": (
                                            result[
                                                "error"
                                            ]
                                        ),
                                    }
                            except Exception as e:
                                tool_result = {
                                    "error": str(e),
                                }
                            conversation_history.append({
                                "role": "tool",
                                "type": "tool_result",
                                "tool_name": tool_name,
                                "result": tool_result,
                            })
                            sub_result = (
                                _truncate_sub_result(
                                    tool_result,
                                )
                            )
                            event_queue.put({
                                "type": "sub_event",
                                "agent_id": agent_id,
                                "agent_label": (
                                    agent_label
                                ),
                                "event": {
                                    "type": (
                                        "tool_result"
                                    ),
                                    "tool_name": (
                                        tool_name
                                    ),
                                    "result": (
                                        sub_result
                                    ),
                                },
                            })
                except (
                    TimeoutError,
                    OSError,
                    httpx.TimeoutException,
                ) as e:
                    elapsed = round(
                        time.monotonic() - step_start,
                    )
                    _logger.error(
                        "HostAnalyzer[%s] step %d "
                        "TIMED OUT after %ds: %s",
                        agent_id, step_num + 1,
                        elapsed, e,
                    )
                    event_queue.put({
                        "type": "sub_event",
                        "agent_id": agent_id,
                        "agent_label": agent_label,
                        "event": {
                            "type": "text_delta",
                            "text": (
                                f"Timeout after "
                                f"{elapsed}s: {e}\n"
                            ),
                        },
                    })
                    break

            if host_analysis is not None:
                break

        if host_analysis is None:
            host_analysis = {
                "host_id": agent_id,
                "summary": (
                    "HostAnalyzerAgent did not produce"
                    " an analysis within the step "
                    "limit."
                ),
            }

        event_queue.put({
            "type": "_agent_done",
            "agent_id": agent_id,
            "agent_label": agent_label,
            "host_analysis": host_analysis,
        })
    except Exception as exc:
        _logger.exception(
            "HostAnalyzer[%s] failed: %s",
            agent_id, exc,
        )
        event_queue.put({
            "type": "sub_event",
            "agent_id": agent_id,
            "agent_label": agent_label,
            "event": {
                "type": "text_delta",
                "text": f"Error: {exc}\n",
            },
        })
        event_queue.put({
            "type": "_agent_done",
            "agent_id": agent_id,
            "agent_label": agent_label,
            "host_analysis": {
                "host_id": agent_id,
                "error": str(exc),
            },
        })


def run_host_analyzers_stream(
    hosts: list[dict[str, Any]],
    context: dict[str, Any] | None = None,
) -> Generator[dict[str, Any], None, None]:
    """
    Run parallel HostAnalyzerAgents for multiple hosts.

    Spawns one thread per host, each running a
    HostAnalyzerAgent to completion with auto-approved
    tool calls. Uses a shared queue to yield tagged
    sub_event dicts and a final done event.

    :param hosts: list of dicts with host_id and
        host_description
    :param context: incident context dict injected by the
        route handler
    :return: generator yielding event dicts
    """
    ctx = context or {}
    if not hosts:
        yield {
            "type": "done",
            "result": {"host_analyses": {}},
        }
        return

    yield {
        "type": "sub_event",
        "event": {
            "type": "parallel_start",
            "hosts": [
                {
                    "agent_id": h.get(
                        "host_id", f"host_{i}",
                    ),
                    "agent_label": (
                        f"Analysis of host "
                        f"{h.get('host_id', f'host_{i}')}"
                    ),
                }
                for i, h in enumerate(hosts)
            ],
        },
    }

    event_queue: queue.Queue[dict[str, Any]] = (
        queue.Queue()
    )
    semaphore = threading.Semaphore(_CONCURRENCY_LIMIT)
    threads: list[threading.Thread] = []

    for host in hosts:
        t = threading.Thread(
            target=_run_single_host_analyzer,
            args=(host, ctx, event_queue, semaphore),
            daemon=True,
        )
        threads.append(t)
        t.start()

    done_count = 0
    total = len(hosts)
    host_analyses: dict[str, Any] = {}

    while done_count < total:
        try:
            event = event_queue.get(timeout=600)
        except queue.Empty:
            yield {
                "type": "output_chunk",
                "text": (
                    "[HostAnalyzers] Timed out "
                    "waiting for agents.\n"
                ),
            }
            break

        if event.get("type") == "_agent_done":
            done_count += 1
            agent_id = event.get("agent_id", "")
            host_analyses[agent_id] = event.get(
                "host_analysis", {},
            )
            yield {
                "type": "sub_event",
                "agent_id": agent_id,
                "agent_label": event.get(
                    "agent_label", agent_id,
                ),
                "event": {"type": "agent_done"},
            }
            yield {
                "type": "output_chunk",
                "text": (
                    f"[HostAnalyzers] {agent_id} "
                    f"done ({done_count}/{total}).\n"
                ),
            }
        else:
            yield event

    for t in threads:
        t.join(timeout=5)

    yield {
        "type": "done",
        "result": {"host_analyses": host_analyses},
    }


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
    "run_host_analyzers": run_host_analyzers_stream,
}
