"""Shared fixtures for backend integration tests."""
import pytest
from flask import Flask
from flask.testing import FlaskClient

from ccs_response_planner_backend.rest_api.rest_api import create_app


@pytest.fixture()
def static_dir(tmp_path: pytest.TempPathFactory) -> str:
    """
    Create a temporary directory with a minimal index.html.

    :param tmp_path: pytest built-in temp directory fixture
    :return: path to the temporary static directory
    """
    index = tmp_path / "index.html"
    index.write_text("<html><body>test</body></html>")
    return str(tmp_path)


@pytest.fixture()
def app(static_dir: str) -> Flask:
    """
    Create a Flask app configured for testing.

    :param static_dir: path to the temporary static directory
    :return: a configured Flask app instance
    """
    application = create_app(static_folder=static_dir)
    application.config["TESTING"] = True
    return application


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    """
    Create a Flask test client.

    :param app: the Flask application
    :return: a Flask test client
    """
    return app.test_client()
