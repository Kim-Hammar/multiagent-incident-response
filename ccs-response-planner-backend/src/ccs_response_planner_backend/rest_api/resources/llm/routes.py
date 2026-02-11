"""
Routes and sub-resources for the /llm resource.
"""
import os
import re
from datetime import datetime, timezone

from flask import Blueprint, Response, jsonify
from google import genai  # type: ignore[attr-defined]

from ccs_response_planner_backend.constants.constants import API
from ccs_response_planner_backend.rest_api.util.auth import token_required

llm_bp = Blueprint(
    API.LLM_RESOURCE, __name__,
    url_prefix=f"{API.PREFIX}/{API.LLM_RESOURCE}",
)

_THINKING_RE = re.compile(
    r"gemini-(2\.5|3[\.\-]|flash-latest|pro-latest"
    r"|flash-lite-latest|robotics)"
)

_NO_THINKING_RE = re.compile(
    r"(tts|image|computer-use|deep-research|nano-banana)"
)


def _supports_thinking(model_name: str) -> bool:
    """
    Check whether a model supports ThinkingConfig.

    Gemini 2.5+, 3.x, and their "-latest" aliases support thinking.
    TTS, image generation, computer-use, and Gemma models do not.

    :param model_name: the full model name (e.g. "models/gemini-2.5-pro")
    :return: True if the model supports thinking
    """
    name = model_name.lower()
    if "gemma" in name:
        return False
    if _NO_THINKING_RE.search(name):
        return False
    if _THINKING_RE.search(name):
        return True
    return False


@llm_bp.route("", methods=["GET"])
@token_required
def llm_status() -> tuple[Response, int]:
    """
    Check LLM connectivity and return available model information.

    Only models that support thinking are included because the
    agent loops require ThinkingConfig.

    :return: a tuple of (JSON response, HTTP status code)
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        client = genai.Client(
            api_key=os.environ.get("GEMINI_API_KEY", ""),
        )
        models = []
        for m in client.models.list():
            actions = m.supported_actions or []
            if "generateContent" not in actions:
                continue
            if not m.name or not _supports_thinking(m.name):
                continue
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
