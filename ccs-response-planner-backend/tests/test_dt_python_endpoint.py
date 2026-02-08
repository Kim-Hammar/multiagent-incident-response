"""Integration tests for the /api/dt-python endpoint."""
from unittest.mock import MagicMock, patch

from flask.testing import FlaskClient


@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".dt_python.routes.docker"
)
def test_dt_python_returns_connected_status(
    mock_docker: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container
    mock_docker.from_env.return_value = mock_client
    mock_docker.errors.NotFound = type("NotFound", (Exception,), {})

    response = client.get("/api/dt-python", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "connected"
    assert data["container_status"] == "running"
    assert "timestamp" in data


@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".dt_python.routes.docker"
)
def test_dt_python_returns_stopped_status(
    mock_docker: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_container = MagicMock()
    mock_container.status = "exited"
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container
    mock_docker.from_env.return_value = mock_client
    mock_docker.errors.NotFound = type("NotFound", (Exception,), {})

    response = client.get("/api/dt-python", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "connected"
    assert data["container_status"] == "exited"


@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".dt_python.routes.docker"
)
def test_dt_python_returns_not_found_status(
    mock_docker: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    not_found = type("NotFound", (Exception,), {})
    mock_docker.errors.NotFound = not_found
    mock_client = MagicMock()
    mock_client.containers.get.side_effect = not_found("not found")
    mock_docker.from_env.return_value = mock_client

    response = client.get("/api/dt-python", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "connected"
    assert data["container_status"] == "not_found"


@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".dt_python.routes.docker"
)
def test_dt_python_returns_error_on_docker_failure(
    mock_docker: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_docker.from_env.side_effect = Exception("Docker not available")
    mock_docker.errors.NotFound = type("NotFound", (Exception,), {})

    response = client.get("/api/dt-python", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "error"
    assert data["error"] == "Docker not available"


def test_dt_python_returns_401_without_token(
    client: FlaskClient,
) -> None:
    response = client.get("/api/dt-python")
    assert response.status_code == 401


def test_dt_python_post_returns_405(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post("/api/dt-python", headers=auth_headers)
    assert response.status_code == 405


@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".dt_python.routes.docker"
)
def test_dt_python_run_returns_output(
    mock_docker: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_container = MagicMock()
    mock_container.id = "abc123"
    mock_container.status = "running"
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container
    mock_client.api.exec_create.return_value = {"Id": "exec123"}
    mock_client.api.exec_start.return_value = b"42\n"
    mock_client.api.exec_inspect.return_value = {"ExitCode": 0}
    mock_docker.from_env.return_value = mock_client
    mock_docker.errors.NotFound = type("NotFound", (Exception,), {})

    response = client.post(
        "/api/dt-python/run",
        json={"code": "print(42)"},
        headers=auth_headers,
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["exit_code"] == 0
    assert data["output"] == "42\n"
    assert data["test"] is False


@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".dt_python.routes.docker"
)
def test_dt_python_run_with_test_flag(
    mock_docker: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_container = MagicMock()
    mock_container.id = "abc123"
    mock_container.status = "running"
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container
    mock_client.api.exec_create.return_value = {"Id": "exec123"}
    mock_client.api.exec_start.return_value = b"1 passed\n"
    mock_client.api.exec_inspect.return_value = {"ExitCode": 0}
    mock_docker.from_env.return_value = mock_client
    mock_docker.errors.NotFound = type("NotFound", (Exception,), {})

    response = client.post(
        "/api/dt-python/run",
        json={"code": "def test_ok(): assert True", "test": True},
        headers=auth_headers,
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["test"] is True
    assert data["exit_code"] == 0


def test_dt_python_run_returns_400_missing_code(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/dt-python/run",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "code is required" in data["error"]


@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".dt_python.routes.docker"
)
def test_dt_python_run_returns_500_on_failure(
    mock_docker: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_docker.from_env.side_effect = RuntimeError("Docker error")

    response = client.post(
        "/api/dt-python/run",
        json={"code": "print(1)"},
        headers=auth_headers,
    )
    data = response.get_json()

    assert response.status_code == 500
    assert data["error"] == "Docker error"


def test_dt_python_run_returns_401_without_token(
    client: FlaskClient,
) -> None:
    response = client.post(
        "/api/dt-python/run",
        json={"code": "print(1)"},
    )
    assert response.status_code == 401


def test_dt_python_run_get_not_allowed(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.get("/api/dt-python/run", headers=auth_headers)
    assert response.status_code in (404, 405)
