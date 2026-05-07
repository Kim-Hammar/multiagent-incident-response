"""
Routes and sub-resources for the /abuseipdb resource.
"""
import os
from datetime import datetime, timezone

import requests as http_requests
from flask import Blueprint, Response, jsonify, request

from response_planner_backend.constants.constants import API
from response_planner_backend.rest_api.util.auth import token_required

abuseipdb_bp = Blueprint(
    API.ABUSEIPDB_RESOURCE, __name__,
    url_prefix=f"{API.PREFIX}/{API.ABUSEIPDB_RESOURCE}",
)

BASE_URL = "https://api.abuseipdb.com/api/v2"


@abuseipdb_bp.route("", methods=["GET"])
@token_required
def abuseipdb_status() -> tuple[Response, int]:
    """
    Check AbuseIPDB API connectivity by looking up 8.8.8.8.

    :return: a tuple of (JSON response, HTTP status code)
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        api_key = os.environ.get("ABUSEIPDB_API_KEY", "")
        if not api_key:
            return jsonify({
                "status": "error",
                "timestamp": timestamp,
                "error": "ABUSEIPDB_API_KEY environment variable not set",
            }), 200
        resp = http_requests.get(
            f"{BASE_URL}/check",
            headers={"Key": api_key, "Accept": "application/json"},
            params={"ipAddress": "8.8.8.8"},
            timeout=10,
        )
        resp.raise_for_status()
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


@abuseipdb_bp.route("/check", methods=["POST"])
@token_required
def abuseipdb_check() -> tuple[Response, int]:
    """
    Check an IP address against the AbuseIPDB database.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    ip = body.get("ip", "")
    if not ip or not isinstance(ip, str) or not ip.strip():
        return jsonify({"error": "ip is required"}), 400
    try:
        api_key = os.environ.get("ABUSEIPDB_API_KEY", "")
        if not api_key:
            return jsonify({
                "error": "ABUSEIPDB_API_KEY environment variable not set",
            }), 500
        resp = http_requests.get(
            f"{BASE_URL}/check",
            headers={"Key": api_key, "Accept": "application/json"},
            params={"ipAddress": ip.strip()},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        result = {
            "ip": data.get("ipAddress", ip.strip()),
            "abuse_confidence_score": data.get(
                "abuseConfidenceScore",
            ),
            "isp": data.get("isp", ""),
            "country_code": data.get("countryCode", ""),
            "total_reports": data.get("totalReports", 0),
            "last_reported_at": data.get("lastReportedAt"),
            "is_public": data.get("isPublic", False),
        }
        return jsonify({"result": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
