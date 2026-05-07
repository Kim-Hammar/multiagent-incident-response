"""Integration tests for the /api/dt-exec endpoint."""
from unittest.mock import MagicMock, patch

from flask.testing import FlaskClient


@patch(
    "response_planner_backend.rest_api.resources"
    ".dt_exec.routes.docker"
)
def test_dt_exec_returns_connected_status(
    mock_docker: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_container = MagicMock()
    mock_container.name = "dt_i1_gateway"
    mock_client = MagicMock()
    mock_client.containers.list.return_value = [mock_container]
    mock_docker.from_env.return_value = mock_client

    response = client.get("/api/dt-exec", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "connected"
    assert data["count"] == 1
    assert "dt_i1_gateway" in data["containers"]
    assert "timestamp" in data


@patch(
    "response_planner_backend.rest_api.resources"
    ".dt_exec.routes.docker"
)
def test_dt_exec_returns_error_status_on_failure(
    mock_docker: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_docker.from_env.side_effect = Exception("Docker not available")

    response = client.get("/api/dt-exec", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "error"
    assert data["error"] == "Docker not available"


def test_dt_exec_returns_401_without_token(
    client: FlaskClient,
) -> None:
    response = client.get("/api/dt-exec")
    assert response.status_code == 401


def test_dt_exec_post_returns_405(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post("/api/dt-exec", headers=auth_headers)
    assert response.status_code == 405


@patch(
    "response_planner_backend.rest_api.resources"
    ".dt_exec.routes.docker"
)
def test_dt_exec_run_returns_output(
    mock_docker: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_container.id = "abc123"
    mock_client.containers.get.return_value = mock_container
    mock_client.api.exec_create.return_value = {"Id": "exec123"}
    mock_client.api.exec_start.return_value = b"hello world\n"
    mock_client.api.exec_inspect.return_value = {"ExitCode": 0}
    mock_docker.from_env.return_value = mock_client
    mock_docker.errors.NotFound = type("NotFound", (Exception,), {})

    response = client.post(
        "/api/dt-exec/run",
        json={"container": "i1_gateway", "command": "echo hello"},
        headers=auth_headers,
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["container"] == "i1_gateway"
    assert data["command"] == "echo hello"
    assert data["exit_code"] == 0
    assert data["output"] == "hello world\n"


def test_dt_exec_run_returns_400_missing_params(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/dt-exec/run",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "container and command are required" in data["error"]


@patch(
    "response_planner_backend.rest_api.resources"
    ".dt_exec.routes.docker"
)
def test_dt_exec_run_returns_404_container_not_found(
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
        "/api/dt-exec/run",
        json={"container": "nonexistent", "command": "ls"},
        headers=auth_headers,
    )
    assert response.status_code == 404


@patch(
    "response_planner_backend.rest_api.resources"
    ".dt_exec.routes.docker"
)
def test_dt_exec_run_returns_500_on_failure(
    mock_docker: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_client = MagicMock()
    mock_client.containers.get.side_effect = RuntimeError("Docker error")
    mock_docker.from_env.return_value = mock_client
    mock_docker.errors.NotFound = type("NotFound", (Exception,), {})

    response = client.post(
        "/api/dt-exec/run",
        json={"container": "i1_gateway", "command": "ls"},
        headers=auth_headers,
    )
    data = response.get_json()

    assert response.status_code == 500
    assert data["error"] == "Docker error"


def test_dt_exec_run_returns_401_without_token(
    client: FlaskClient,
) -> None:
    response = client.post(
        "/api/dt-exec/run",
        json={"container": "i1_gateway", "command": "ls"},
    )
    assert response.status_code == 401


def test_dt_exec_run_get_not_allowed(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.get("/api/dt-exec/run", headers=auth_headers)
    assert response.status_code in (404, 405)
