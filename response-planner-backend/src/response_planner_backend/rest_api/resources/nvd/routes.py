"""
Routes and sub-resources for the /nvd resource.
"""
import os
from datetime import datetime, timezone
from typing import Any

import nvdlib
from flask import Blueprint, Response, jsonify, request

from response_planner_backend.constants.constants import API
from response_planner_backend.rest_api.util.auth import token_required

nvd_bp = Blueprint(
    API.NVD_RESOURCE, __name__,
    url_prefix=f"{API.PREFIX}/{API.NVD_RESOURCE}",
)


@nvd_bp.route("", methods=["GET"])
@token_required
def nvd_status() -> tuple[Response, int]:
    """
    Check NVD API connectivity by looking up a known CVE.

    :return: a tuple of (JSON response, HTTP status code)
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        api_key = os.environ.get("NVD_API_KEY")
        kwargs: dict[str, str] = {"cveId": "CVE-2021-44228"}
        if api_key:
            kwargs["key"] = api_key
        results = nvdlib.searchCVE(**kwargs)
        cve_list = list(results)
        return jsonify({
            "status": "connected",
            "timestamp": timestamp,
            "cve_count": len(cve_list),
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "timestamp": timestamp,
            "error": str(e),
        }), 200


@nvd_bp.route("/search", methods=["POST"])
@token_required
def nvd_search() -> tuple[Response, int]:
    """
    Search the NVD database by CVE ID or keyword.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    cve_id = body.get("cve_id", "")
    keyword = body.get("keyword", "")
    if not cve_id and not keyword:
        return jsonify({"error": "cve_id or keyword is required"}), 400
    results_per_page = body.get("results_per_page", 5)
    try:
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
                "url": f"https://nvd.nist.gov/vuln/detail/{getattr(cve, 'id', '')}",
            })
        return jsonify({
            "query": query,
            "results": results,
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
