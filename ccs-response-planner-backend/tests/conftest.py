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
        "ccs_response_planner_backend.rest_api.rest_api.DatabaseFacade"
    ) as mock:
        mock.get_session_token_by_token.side_effect = _mock_get_token
        mock.get_user_by_username.return_value = None
        mock.update_session_token.return_value = None
        yield mock


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
