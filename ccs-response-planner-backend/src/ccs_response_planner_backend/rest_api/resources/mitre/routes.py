"""
Routes and sub-resources for the /mitre resource.
"""
import os
import tempfile
from datetime import datetime, timezone
from typing import Any

import requests as http_requests
from flask import Blueprint, Response, jsonify, request
from mitreattack.stix20 import MitreAttackData

from ccs_response_planner_backend.constants.constants import API
from ccs_response_planner_backend.rest_api.util.auth import token_required

mitre_bp = Blueprint(
    API.MITRE_RESOURCE, __name__,
    url_prefix=f"{API.PREFIX}/{API.MITRE_RESOURCE}",
)

_STIX_URL = (
    "https://raw.githubusercontent.com/mitre/cti"
    "/master/enterprise-attack/enterprise-attack.json"
)
_STIX_CACHE = os.path.join(
    tempfile.gettempdir(), "enterprise-attack.json",
)


def _get_attack_data() -> MitreAttackData:
    """
    Load the MITRE ATT&CK STIX data bundle, downloading it on first use.

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


@mitre_bp.route("", methods=["GET"])
@token_required
def mitre_status() -> tuple[Response, int]:
    """
    Check MITRE ATT&CK data availability by loading the STIX bundle.

    :return: a tuple of (JSON response, HTTP status code)
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        attack_data = _get_attack_data()
        techniques = attack_data.get_techniques()
        return jsonify({
            "status": "connected",
            "timestamp": timestamp,
            "technique_count": len(techniques),
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "timestamp": timestamp,
            "error": str(e),
        }), 200


@mitre_bp.route("/search", methods=["POST"])
@token_required
def mitre_search() -> tuple[Response, int]:
    """
    Search MITRE ATT&CK techniques by ID or keyword.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    technique_id = body.get("technique_id", "")
    search = body.get("search", "")
    if not technique_id and not search:
        return jsonify({
            "error": "technique_id or search is required",
        }), 400
    try:
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
        return jsonify({
            "query": query,
            "results": results,
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
