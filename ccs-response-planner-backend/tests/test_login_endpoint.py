"""Integration tests for the /api/login endpoint and token-based auth."""
from unittest.mock import MagicMock

import bcrypt
from flask.testing import FlaskClient


def test_login_valid_credentials(
    client: FlaskClient, mock_db: MagicMock
) -> None:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(b"secret", salt)
    mock_db.get_user_by_username.return_value = {
        "id": 1,
        "username": "admin",
        "password": hashed.decode("utf-8"),
        "salt": salt.decode("utf-8"),
    }
    response = client.post(
        "/api/login",
        json={"username": "admin", "password": "secret"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "token" in data
    assert data["username"] == "admin"


def test_login_wrong_password(
    client: FlaskClient, mock_db: MagicMock
) -> None:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(b"secret", salt)
    mock_db.get_user_by_username.return_value = {
        "id": 1,
        "username": "admin",
        "password": hashed.decode("utf-8"),
        "salt": salt.decode("utf-8"),
    }
    response = client.post(
        "/api/login",
        json={"username": "admin", "password": "wrong"},
    )
    assert response.status_code == 401
    assert response.get_json()["error"] == "Invalid credentials"


def test_login_nonexistent_user(
    client: FlaskClient, mock_db: MagicMock
) -> None:
    mock_db.get_user_by_username.return_value = None
    response = client.post(
        "/api/login",
        json={"username": "nobody", "password": "secret"},
    )
    assert response.status_code == 401
    assert response.get_json()["error"] == "Invalid credentials"


def test_login_missing_fields(client: FlaskClient) -> None:
    response = client.post(
        "/api/login",
        json={"username": "admin"},
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "username and password are required"


def test_login_empty_body(client: FlaskClient) -> None:
    response = client.post(
        "/api/login",
        content_type="application/json",
    )
    assert response.status_code == 400


def test_login_get_not_allowed(client: FlaskClient) -> None:
    response = client.get("/api/login")
    assert response.status_code in (404, 405)


def test_protected_endpoint_without_token(client: FlaskClient) -> None:
    response = client.get("/api/example")
    assert response.status_code == 401
    assert response.get_json()["error"] == "Missing or invalid token"


def test_protected_endpoint_with_invalid_token(
    client: FlaskClient
) -> None:
    response = client.get(
        "/api/example",
        headers={"Authorization": "Bearer bad-token"},
    )
    assert response.status_code == 401
    assert response.get_json()["error"] == "Missing or invalid token"
