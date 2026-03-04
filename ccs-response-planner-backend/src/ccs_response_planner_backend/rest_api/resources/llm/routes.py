"""
Routes and sub-resources for the /llm resource.
"""
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

from flask import Blueprint, Response, jsonify
from google import genai  # type: ignore[attr-defined]

from ccs_response_planner_backend.agents.anthropic_adapter import (
    list_models as anthropic_list_models,
)
from ccs_response_planner_backend.constants.constants import API
from ccs_response_planner_backend.rest_api.util.auth import token_required

logger = logging.getLogger(__name__)

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


def _fetch_gemini_models() -> list[dict[str, Any]]:
    """
    Fetch available Gemini models that support thinking.

    :return: a list of model info dicts with vendor field
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return []
    models = []
    client = genai.Client(
        api_key=api_key,
    )
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
            "vendor": "gemini",
        })
    return models


def _fetch_anthropic_models() -> list[dict[str, Any]]:
    """
    Fetch available Anthropic Claude models.

    :return: a list of model info dicts with vendor field
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return []
    raw = anthropic_list_models(api_key)
    for m in raw:
        m["vendor"] = "anthropic"
    return raw


@llm_bp.route("", methods=["GET"])
@token_required
def llm_status() -> tuple[Response, int]:
    """
    Check LLM connectivity and return available model information.

    Queries both Gemini and Anthropic vendors independently.
    Returns connected if at least one vendor succeeds.

    :return: a tuple of (JSON response, HTTP status code)
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    models: list[dict[str, Any]] = []
    errors: list[str] = []

    try:
        models.extend(_fetch_gemini_models())
    except Exception as e:
        logger.warning("Gemini model fetch failed: %s", e)
        errors.append(f"Gemini: {e}")

    try:
        models.extend(_fetch_anthropic_models())
    except Exception as e:
        logger.warning(
            "Anthropic model fetch failed: %s", e,
        )
        errors.append(f"Anthropic: {e}")

    if models:
        return jsonify({
            "status": "connected",
            "timestamp": timestamp,
            "models": models,
        }), 200
    else:
        return jsonify({
            "status": "error",
            "timestamp": timestamp,
            "error": "; ".join(errors) if errors
            else "No models available",
        }), 200
