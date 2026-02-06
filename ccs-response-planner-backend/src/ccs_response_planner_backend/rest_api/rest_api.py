"""REST API server for the CCS Response Planner."""
import os
from typing import Any, Optional

from flask import Flask, Response, jsonify, request, send_from_directory

from ccs_response_planner_backend.constants.constants import (
    APP_NAME,
    HEALTH_ROUTE,
    PLAN_ROUTE,
)
from ccs_response_planner_backend.planner.incident_response_planner import (
    IncidentResponsePlanner,
)


def create_app(static_folder: str) -> Flask:
    """Create and configure the Flask application.

    Args:
        static_folder: Path to the static frontend build directory.

    Returns:
        A configured Flask app instance.
    """
    app = Flask(
        __name__,
        static_folder=os.path.abspath(static_folder),
        static_url_path="",
    )
    planner = IncidentResponsePlanner()

    @app.route(HEALTH_ROUTE, methods=["GET"])
    def health() -> tuple[Response, int]:
        return jsonify({"status": "ok", "app": APP_NAME}), 200

    @app.route(PLAN_ROUTE, methods=["POST"])
    def plan() -> tuple[Response, int]:
        data = request.get_json(silent=True) or {}
        incident_description = data.get("incident_description", "")
        if not incident_description:
            return jsonify({"error": "incident_description is required"}), 400
        result = planner.generate_plan(incident_description)
        return jsonify(result), 200

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve(path: str) -> Any:
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
    """Start the Flask server.

    Args:
        static_folder: Path to the static frontend build directory.
        port: Port number to listen on.
        num_threads: Number of threads for the server.
        host: Host address to bind to.
        https: Whether to enable HTTPS (not yet implemented).
    """
    app = create_app(static_folder)
    app.run(
        host=host,
        port=port,
        threaded=True,
        debug=False,
    )
