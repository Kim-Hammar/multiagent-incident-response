"""
REST API server for the CCS Response Planner.
"""
import os
from typing import Any, Optional

from flask import Flask, Response, jsonify, request, send_from_directory

from ccs_response_planner_backend.constants.constants import API, GENERAL
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

    @app.route(API.HEALTH_ROUTE, methods=["GET"])
    def health() -> tuple[Response, int]:
        """
        Health check endpoint.

        :return: a tuple of (JSON response, HTTP status code)
        """
        return jsonify({"status": "ok", "app": GENERAL.APP_NAME}), 200

    @app.route(API.PLAN_ROUTE, methods=["POST"])
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
