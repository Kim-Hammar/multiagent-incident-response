"""
Routes and sub-resources for the /virustotal resource.
"""
import os
from datetime import datetime, timezone

import vt
from flask import Blueprint, Response, jsonify, request

from response_planner_backend.constants.constants import API
from response_planner_backend.rest_api.util.auth import token_required

virustotal_bp = Blueprint(
    API.VIRUSTOTAL_RESOURCE, __name__,
    url_prefix=f"{API.PREFIX}/{API.VIRUSTOTAL_RESOURCE}",
)

VALID_TYPES = {"ip", "domain", "url", "hash"}


@virustotal_bp.route("", methods=["GET"])
@token_required
def virustotal_status() -> tuple[Response, int]:
    """
    Check VirusTotal API connectivity by looking up a known domain.

    :return: a tuple of (JSON response, HTTP status code)
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        api_key = os.environ.get("VIRUSTOTAL_API_KEY", "")
        if not api_key:
            return jsonify({
                "status": "error",
                "timestamp": timestamp,
                "error": "VIRUSTOTAL_API_KEY environment variable not set",
            }), 200
        client = vt.Client(api_key)
        try:
            client.get_object("/domains/google.com")
        finally:
            client.close()
        return jsonify({
            "status": "connected",
            "timestamp": timestamp,
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "timestamp": timestamp,
            "error": str(e),
        }), 200


@virustotal_bp.route("/scan", methods=["POST"])
@token_required
def virustotal_scan() -> tuple[Response, int]:
    """
    Look up a resource on VirusTotal by type and value.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    scan_type = body.get("type", "")
    value = body.get("value", "")
    if not scan_type or not value:
        return jsonify({"error": "type and value are required"}), 400
    if scan_type not in VALID_TYPES:
        return jsonify({
            "error": f"type must be one of: {', '.join(sorted(VALID_TYPES))}",
        }), 400
    path_map = {
        "ip": f"/ip_addresses/{value}",
        "domain": f"/domains/{value}",
        "url": f"/urls/{vt.url_id(value)}",
        "hash": f"/files/{value}",
    }
    try:
        api_key = os.environ.get("VIRUSTOTAL_API_KEY", "")
        if not api_key:
            return jsonify({
                "error": "VIRUSTOTAL_API_KEY environment variable not set",
            }), 500
        client = vt.Client(api_key)
        try:
            obj = client.get_object(path_map[scan_type])
        finally:
            client.close()
        raw_stats = getattr(obj, "last_analysis_stats", None)
        result = {
            "type": scan_type,
            "value": value,
            "reputation": getattr(obj, "reputation", None),
            "last_analysis_stats": dict(raw_stats) if raw_stats else None,
            "last_analysis_date": getattr(
                obj, "last_analysis_date", None,
            ),
        }
        if result["last_analysis_date"] is not None:
            result["last_analysis_date"] = str(
                result["last_analysis_date"]
            )
        return jsonify({"result": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
