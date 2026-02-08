"""
Routes and sub-resources for the /otx resource.
"""
import os
from datetime import datetime, timezone

from flask import Blueprint, Response, jsonify, request
from OTXv2 import OTXv2, IndicatorTypes

from ccs_response_planner_backend.constants.constants import API
from ccs_response_planner_backend.rest_api.util.auth import token_required

otx_bp = Blueprint(
    API.OTX_RESOURCE, __name__,
    url_prefix=f"{API.PREFIX}/{API.OTX_RESOURCE}",
)

TYPE_MAP = {
    "IPv4": IndicatorTypes.IPv4,
    "IPv6": IndicatorTypes.IPv6,
    "domain": IndicatorTypes.DOMAIN,
    "hostname": IndicatorTypes.HOSTNAME,
    "url": IndicatorTypes.URL,
    "hash": IndicatorTypes.FILE_HASH_SHA256,
    "cve": IndicatorTypes.CVE,
}


@otx_bp.route("", methods=["GET"])
@token_required
def otx_status() -> tuple[Response, int]:
    """
    Check OTX API connectivity by searching for a test pulse.

    :return: a tuple of (JSON response, HTTP status code)
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        api_key = os.environ.get("OTX_API_KEY", "")
        if not api_key:
            return jsonify({
                "status": "error",
                "timestamp": timestamp,
                "error": "OTX_API_KEY environment variable not set",
            }), 200
        otx = OTXv2(api_key)
        otx.search_pulses("test", max_results=1)
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


@otx_bp.route("/search", methods=["POST"])
@token_required
def otx_search() -> tuple[Response, int]:
    """
    Search OTX for an indicator (IP, domain, hash, CVE, etc.).

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    indicator_type = body.get("type", "")
    value = body.get("value", "")
    if not indicator_type or not value:
        return jsonify({"error": "type and value are required"}), 400
    if indicator_type not in TYPE_MAP:
        return jsonify({
            "error": (
                f"type must be one of: "
                f"{', '.join(sorted(TYPE_MAP.keys()))}"
            ),
        }), 400
    try:
        api_key = os.environ.get("OTX_API_KEY", "")
        if not api_key:
            return jsonify({
                "error": "OTX_API_KEY environment variable not set",
            }), 500
        otx = OTXv2(api_key)
        details = otx.get_indicator_details_full(
            TYPE_MAP[indicator_type], value.strip(),
        )
        general = details.get("general", {})
        pulse_info = general.get("pulse_info", {})
        pulses = pulse_info.get("pulses", [])
        result = {
            "type": indicator_type,
            "value": value.strip(),
            "pulse_count": pulse_info.get("count", 0),
            "reputation": general.get("reputation", None),
            "pulses": [
                {
                    "name": p.get("name", ""),
                    "description": (p.get("description", "") or "")[:200],
                    "created": p.get("created", ""),
                    "tags": p.get("tags", [])[:5],
                }
                for p in pulses[:10]
            ],
        }
        return jsonify({"result": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
