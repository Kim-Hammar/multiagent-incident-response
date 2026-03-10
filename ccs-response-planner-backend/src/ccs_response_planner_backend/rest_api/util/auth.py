"""
Authentication utilities for the REST API.
"""
import logging
import time
from functools import wraps
from typing import Any, Callable, Optional

from flask import g, jsonify, request
from psycopg_pool import PoolTimeout

from ccs_response_planner_backend.constants.constants import AUTH
from ccs_response_planner_backend.db.database_facade import DatabaseFacade

logger = logging.getLogger(__name__)

_TOKEN_CACHE_TTL = 30.0

_token_cache: dict[str, tuple[str, float]] = {}


def _lookup_token(token: str) -> Optional[str]:
    """
    Look up a token, returning the cached username if still valid
    or querying the database otherwise.

    :param token: the bearer token string
    :return: the username or None if invalid
    """
    now = time.monotonic()
    cached = _token_cache.get(token)
    if cached is not None:
        username, expires = cached
        if now < expires:
            return username
        del _token_cache[token]
    session = DatabaseFacade.get_session_token_by_token(token)
    if session is None:
        return None
    uname: str = session["username"]
    _token_cache[token] = (uname, now + _TOKEN_CACHE_TTL)
    return uname


def invalidate_token_cache(token: str) -> None:
    """
    Remove a token from the validation cache (e.g. on logout).

    :param token: the bearer token string to invalidate
    """
    _token_cache.pop(token, None)


def token_required(f: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator that requires a valid Bearer token in the
    Authorization header.

    Validated tokens are cached in memory for up to
    ``_TOKEN_CACHE_TTL`` seconds to avoid a database round-trip
    on every request.

    :param f: the route function to protect
    :return: the decorated function
    """
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        """
        Check for a valid session token before calling
        the wrapped function.

        :return: the wrapped function result or a 401 error
        """
        auth_header = request.headers.get(
            AUTH.TOKEN_HEADER, "",
        )
        if not auth_header.startswith(AUTH.TOKEN_PREFIX):
            return jsonify({
                "error": "Missing or invalid token",
            }), 401
        token = auth_header[len(AUTH.TOKEN_PREFIX):]
        try:
            username = _lookup_token(token)
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
        if username is None:
            return jsonify({
                "error": "Missing or invalid token",
            }), 401
        g.username = username
        return f(*args, **kwargs)
    return decorated
