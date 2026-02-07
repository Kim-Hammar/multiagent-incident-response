"""Shared fixtures for backend integration tests."""
from typing import Any, Generator
from unittest.mock import MagicMock, patch

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
def mock_db() -> Generator[MagicMock, None, None]:
    """
    Patch DatabaseFacade so tests run without a real PostgreSQL instance.

    By default, get_session_token_by_token returns a valid session
    for the token 'test-token'.

    :return: the mocked DatabaseFacade class
    """
    with patch(
        "ccs_response_planner_backend.rest_api.util.auth.DatabaseFacade"
    ) as auth_mock, patch(
        "ccs_response_planner_backend.rest_api.resources.login.routes"
        ".DatabaseFacade"
    ) as login_mock, patch(
        "ccs_response_planner_backend.rest_api.resources.digital_twin"
        ".routes.DatabaseFacade"
    ) as dt_mock, patch(
        "ccs_response_planner_backend.rest_api.resources.digital_twin"
        ".routes.DockerManager"
    ) as docker_mgr_mock, patch(
        "ccs_response_planner_backend.rest_api.resources.digital_twin"
        ".terminal.DatabaseFacade"
    ) as terminal_db_mock:
        for mock in (auth_mock, login_mock, dt_mock, terminal_db_mock):
            mock.get_session_token_by_token.side_effect = _mock_get_token
            mock.get_user_by_username.return_value = None
            mock.update_session_token.return_value = None
        dt_mock.get_digital_twin_config.return_value = None
        dt_mock.save_digital_twin_config.return_value = None
        dt_mock.delete_digital_twin_config.return_value = None
        docker_mgr_mock.deploy.return_value = {
            "network": "ccs_dt_network",
            "containers": [],
        }
        docker_mgr_mock.stop.return_value = {"removed": []}
        docker_mgr_mock.status.return_value = {
            "deployed": False,
            "network": None,
            "containers": [],
        }
        docker_mgr_mock.validate.return_value = []
        yield login_mock


def _mock_get_token(token: str) -> Any:
    """
    Return a fake session dict for 'test-token', None otherwise.

    :param token: the token to look up
    :return: a session dict or None
    """
    if token == "test-token":
        return {"token": "test-token", "username": "admin", "timestamp": "now"}
    return None


@pytest.fixture()
def app(static_dir: str, mock_db: MagicMock) -> Flask:
    """
    Create a Flask app configured for testing.

    :param static_dir: path to the temporary static directory
    :param mock_db: the mocked DatabaseFacade
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


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    """
    Return headers with a valid Bearer token for authenticated requests.

    :return: a dict with the Authorization header
    """
    return {"Authorization": "Bearer test-token"}
