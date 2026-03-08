"""
Authentication utilities for the REST API.
"""
import logging
from functools import wraps
from typing import Any, Callable

from flask import g, jsonify, request
from psycopg_pool import PoolTimeout

from ccs_response_planner_backend.constants.constants import AUTH
from ccs_response_planner_backend.db.database_facade import DatabaseFacade

logger = logging.getLogger(__name__)


def token_required(f: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator that requires a valid Bearer token in the Authorization header.

    :param f: the route function to protect
    :return: the decorated function
    """
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        """
        Check for a valid session token before calling the wrapped function.

        :return: the wrapped function result or a 401 JSON error
        """
        auth_header = request.headers.get(AUTH.TOKEN_HEADER, "")
        if not auth_header.startswith(AUTH.TOKEN_PREFIX):
            return jsonify({"error": "Missing or invalid token"}), 401
        token = auth_header[len(AUTH.TOKEN_PREFIX):]
        try:
            session = DatabaseFacade.get_session_token_by_token(token)
        except PoolTimeout:
            logger.error(
                "Database connection pool exhausted "
                "during token validation"
            )
            return jsonify({
                "error": (
                    "Database temporarily unavailable, "
                    "please try again"
                ),
            }), 503
        if session is None:
            return jsonify({"error": "Missing or invalid token"}), 401
        g.username = session["username"]
        return f(*args, **kwargs)
    return decorated
