"""Integration tests for the /api/dt-logs endpoint."""
from unittest.mock import MagicMock, patch

from flask.testing import FlaskClient


@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".dt_logs.routes.docker"
)
def test_dt_logs_returns_connected_status(
    mock_docker: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_container = MagicMock()
    mock_container.name = "ccs_dt_server_1"
    mock_client = MagicMock()
    mock_client.containers.list.return_value = [mock_container]
    mock_docker.from_env.return_value = mock_client

    response = client.get("/api/dt-logs", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "connected"
    assert data["count"] == 1
    assert "ccs_dt_server_1" in data["containers"]
    assert "timestamp" in data


@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".dt_logs.routes.docker"
)
def test_dt_logs_returns_error_status_on_failure(
    mock_docker: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_docker.from_env.side_effect = Exception("Docker not available")

    response = client.get("/api/dt-logs", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "error"
    assert data["error"] == "Docker not available"


def test_dt_logs_returns_401_without_token(
    client: FlaskClient,
) -> None:
    response = client.get("/api/dt-logs")
    assert response.status_code == 401


def test_dt_logs_post_returns_405(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post("/api/dt-logs", headers=auth_headers)
    assert response.status_code == 405


@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".dt_logs.routes.docker"
)
def test_dt_logs_fetch_returns_logs(
    mock_docker: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_container = MagicMock()
    mock_container.logs.return_value = b"line1\nline2\nline3\n"
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container
    mock_docker.from_env.return_value = mock_client
    mock_docker.errors.NotFound = type("NotFound", (Exception,), {})

    response = client.post(
        "/api/dt-logs/fetch",
        json={"container": "server_1", "tail": 50},
        headers=auth_headers,
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["container"] == "server_1"
    assert data["lines"] == 3
    assert "line1" in data["output"]


def test_dt_logs_fetch_returns_400_missing_container(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/dt-logs/fetch",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "container is required" in data["error"]


@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".dt_logs.routes.docker"
)
def test_dt_logs_fetch_returns_404_container_not_found(
    mock_docker: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    not_found = type("NotFound", (Exception,), {})
    mock_docker.errors.NotFound = not_found
    mock_client = MagicMock()
    mock_client.containers.get.side_effect = not_found("not found")
    mock_docker.from_env.return_value = mock_client

    response = client.post(
        "/api/dt-logs/fetch",
        json={"container": "nonexistent"},
        headers=auth_headers,
    )
    assert response.status_code == 404


@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".dt_logs.routes.docker"
)
def test_dt_logs_fetch_returns_500_on_failure(
    mock_docker: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_client = MagicMock()
    mock_client.containers.get.side_effect = RuntimeError("Docker error")
    mock_docker.from_env.return_value = mock_client
    mock_docker.errors.NotFound = type("NotFound", (Exception,), {})

    response = client.post(
        "/api/dt-logs/fetch",
        json={"container": "server_1"},
        headers=auth_headers,
    )
    data = response.get_json()

    assert response.status_code == 500
    assert data["error"] == "Docker error"


def test_dt_logs_fetch_returns_401_without_token(
    client: FlaskClient,
) -> None:
    response = client.post(
        "/api/dt-logs/fetch",
        json={"container": "server_1"},
    )
    assert response.status_code == 401


def test_dt_logs_fetch_get_not_allowed(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.get("/api/dt-logs/fetch", headers=auth_headers)
    assert response.status_code in (404, 405)
