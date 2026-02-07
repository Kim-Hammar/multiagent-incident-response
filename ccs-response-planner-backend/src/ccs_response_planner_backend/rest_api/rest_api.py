"""
REST API server for the CCS Response Planner.
"""
import os
from typing import Any, Optional

from flask import Flask, jsonify, request, send_from_directory

from ccs_response_planner_backend.constants.constants import API
from ccs_response_planner_backend.rest_api.resources.example.routes import (
    example_bp,
)
from ccs_response_planner_backend.rest_api.resources.health.routes import (
    health_bp,
)
from ccs_response_planner_backend.rest_api.resources.login.routes import (
    login_bp,
)
from ccs_response_planner_backend.rest_api.resources.plan.routes import (
    plan_bp,
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

    app.register_blueprint(health_bp)
    app.register_blueprint(example_bp)
    app.register_blueprint(plan_bp)
    app.register_blueprint(login_bp)

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
