"""
REST API server for the CCS Response Planner.
"""
import os
import secrets
from functools import wraps
from typing import Any, Callable, Optional

import bcrypt
from flask import Flask, Response, jsonify, request, send_from_directory

from ccs_response_planner_backend.constants.constants import API, AUTH, EXAMPLES, GENERAL
from ccs_response_planner_backend.db.database_facade import DatabaseFacade
from ccs_response_planner_backend.planner.incident_response_planner import (
    IncidentResponsePlanner,
)


def create_app(static_folder: str) -> Flask:
    """
    Create and configure the Flask application.

    :param static_folder: path to the static frontend build directory
    :return: a configured Flask app instance
    """
    app = Flask(
        __name__,
        static_folder=os.path.abspath(static_folder),
        static_url_path="",
    )
    planner = IncidentResponsePlanner()

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
            session = DatabaseFacade.get_session_token_by_token(token)
            if session is None:
                return jsonify({"error": "Missing or invalid token"}), 401
            return f(*args, **kwargs)
        return decorated

    @app.route(API.HEALTH_ROUTE, methods=["GET"])
    def health() -> tuple[Response, int]:
        """
        Health check endpoint.

        :return: a tuple of (JSON response, HTTP status code)
        """
        return jsonify({"status": "ok", "app": GENERAL.APP_NAME}), 200

    @app.route(API.EXAMPLE_ROUTE, methods=["GET"])
    @token_required
    def example() -> tuple[Response, int]:
        """
        Return example incident data for the response planner form.

        :return: a tuple of (JSON response, HTTP status code)
        """
        return jsonify({
            "system_description": EXAMPLES.SYSTEM_DESCRIPTION,
            "security_alerts": EXAMPLES.SECURITY_ALERTS,
            "operator_feedback": EXAMPLES.OPERATOR_FEEDBACK,
        }), 200

    @app.route(API.PLAN_ROUTE, methods=["POST"])
    @token_required
    def plan() -> tuple[Response, int]:
        """
        Generate an incident response plan.

        :return: a tuple of (JSON response, HTTP status code)
        """
        data = request.get_json(silent=True) or {}
        incident_description = data.get("incident_description", "")
        if not incident_description:
            return jsonify({"error": "incident_description is required"}), 400
        result = planner.generate_plan(incident_description)
        return jsonify(result), 200

    @app.route(API.LOGIN_ROUTE, methods=["POST"])
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

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve(path: str) -> Any:
        """
        Serve static frontend files with SPA fallback to index.html.

        :param path: the requested URL path
        :return: the static file or index.html
        """
        if path and os.path.exists(
            os.path.join(app.static_folder, path)  # type: ignore[arg-type]
        ):
            return send_from_directory(
                app.static_folder, path  # type: ignore[arg-type]
            )
        return send_from_directory(
            app.static_folder, "index.html"  # type: ignore[arg-type]
        )

    @app.errorhandler(404)
    def not_found(e: Any) -> Any:
        """
        Handle 404 errors with SPA fallback for client-side routes.

        API paths and requests for files (with extensions) return a JSON 404.
        All other paths serve index.html so React Router can handle routing.

        :param e: the original 404 exception
        :return: index.html for SPA routes or a JSON 404
        """
        if request.path.startswith(API.PREFIX + "/"):
            return jsonify({"error": "Not found"}), 404
        last_segment = request.path.rsplit("/", 1)[-1]
        if "." in last_segment:
            return jsonify({"error": "Not found"}), 404
        return send_from_directory(
            app.static_folder, "index.html"  # type: ignore[arg-type]
        )

    return app


def start_server(
    static_folder: str,
    port: int = 8888,
    num_threads: int = 100,
    host: str = "127.0.0.1",
    https: Optional[bool] = False,
) -> None:
    """
    Start the Flask server.

    :param static_folder: path to the static frontend build directory
    :param port: port number to listen on
    :param num_threads: number of threads for the server
    :param host: host address to bind to
    :param https: whether to enable HTTPS (not yet implemented)
    """
    app = create_app(static_folder)
    app.run(
        host=host,
        port=port,
        threaded=True,
        debug=False,
    )
