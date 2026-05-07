"""
Routes and sub-resources for the /login resource.
"""
import secrets

import bcrypt
from flask import Blueprint, Response, g, jsonify, request

from response_planner_backend.constants.constants import API, AUTH
from response_planner_backend.db.database_facade import DatabaseFacade
from response_planner_backend.rest_api.util.auth import token_required

login_bp = Blueprint(
    API.LOGIN_RESOURCE, __name__,
    url_prefix=f"{API.PREFIX}/{API.LOGIN_RESOURCE}",
)


@login_bp.route("", methods=["GET"])
@token_required
def session_check() -> tuple[Response, int]:
    """
    Validate the current session token.

    :return: a tuple of (JSON response, HTTP status code)
    """
    return jsonify({"valid": True, "username": g.username}), 200


@login_bp.route("", methods=["POST"])
def login() -> tuple[Response, int]:
    """
    Authenticate a user and return a session token.

    :return: a tuple of (JSON response, HTTP status code)
    """
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400
    user = DatabaseFacade.get_user_by_username(username)
    if user is None:
        return jsonify({"error": "Invalid credentials"}), 401
    if not bcrypt.checkpw(
        password.encode("utf-8"), user["password"].encode("utf-8")
    ):
        return jsonify({"error": "Invalid credentials"}), 401
    token = secrets.token_urlsafe(AUTH.TOKEN_LENGTH)
    DatabaseFacade.update_session_token(username, token)
    return jsonify({"token": token, "username": username}), 200
