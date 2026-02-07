"""
Routes and sub-resources for the /llm resource.
"""
import os
from datetime import datetime, timezone

import google.generativeai as genai
from flask import Blueprint, Response, jsonify

from ccs_response_planner_backend.constants.constants import API
from ccs_response_planner_backend.rest_api.util.auth import token_required

llm_bp = Blueprint(
    API.LLM_RESOURCE, __name__,
    url_prefix=f"{API.PREFIX}/{API.LLM_RESOURCE}",
)


@llm_bp.route("", methods=["GET"])
@token_required
def llm_status() -> tuple[Response, int]:
    """
    Check LLM connectivity and return available model information.

    :return: a tuple of (JSON response, HTTP status code)
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))  # type: ignore[attr-defined]
        models = []
        for m in genai.list_models():  # type: ignore[attr-defined]
            if "generateContent" in (m.supported_generation_methods or []):
                models.append({
                    "name": m.name,
                    "display_name": m.display_name,
                    "description": m.description,
                    "input_token_limit": m.input_token_limit,
                    "output_token_limit": m.output_token_limit,
                })
        return jsonify({
            "status": "connected",
            "timestamp": timestamp,
            "models": models,
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "timestamp": timestamp,
            "error": str(e),
        }), 200
