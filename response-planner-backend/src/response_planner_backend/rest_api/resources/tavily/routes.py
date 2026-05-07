"""
Routes and sub-resources for the /tavily resource.
"""
import os
from datetime import datetime, timezone

from flask import Blueprint, Response, jsonify, request
from tavily import TavilyClient

from response_planner_backend.constants.constants import API
from response_planner_backend.rest_api.util.auth import token_required

tavily_bp = Blueprint(
    API.TAVILY_RESOURCE, __name__,
    url_prefix=f"{API.PREFIX}/{API.TAVILY_RESOURCE}",
)


@tavily_bp.route("", methods=["GET"])
@token_required
def tavily_status() -> tuple[Response, int]:
    """
    Check Tavily API connectivity by running a test search.

    :return: a tuple of (JSON response, HTTP status code)
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        api_key = os.environ.get("TAVILY_API_KEY", "")
        client = TavilyClient(api_key=api_key)
        result = client.search(
            query="test", max_results=1,
        )
        return jsonify({
            "status": "connected",
            "timestamp": timestamp,
            "response_time": result.get("response_time"),
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "timestamp": timestamp,
            "error": str(e),
        }), 200


@tavily_bp.route("/search", methods=["POST"])
@token_required
def tavily_search() -> tuple[Response, int]:
    """
    Search via the Tavily API and return results.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    query = body.get("query", "")
    if not query or not isinstance(query, str) or not query.strip():
        return jsonify({"error": "query is required"}), 400
    max_results = body.get("max_results", 5)
    try:
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
        return jsonify({
            "query": query.strip(),
            "results": results,
            "response_time": result.get("response_time"),
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
