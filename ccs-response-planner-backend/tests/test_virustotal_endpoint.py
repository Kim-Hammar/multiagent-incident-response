"""Integration tests for the /api/virustotal endpoint."""
import os
from unittest.mock import MagicMock, patch

from flask.testing import FlaskClient


@patch.dict(os.environ, {"VIRUSTOTAL_API_KEY": "test-key"})
@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".virustotal.routes.vt"
)
def test_virustotal_returns_connected_status(
    mock_vt: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_client = MagicMock()
    mock_vt.Client.return_value = mock_client

    response = client.get("/api/virustotal", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "connected"
    assert "timestamp" in data
    mock_client.close.assert_called_once()


@patch.dict(os.environ, {"VIRUSTOTAL_API_KEY": "test-key"})
@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".virustotal.routes.vt"
)
def test_virustotal_returns_error_status_on_failure(
    mock_vt: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_vt.Client.side_effect = Exception("Invalid API key")

    response = client.get("/api/virustotal", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "error"
    assert data["error"] == "Invalid API key"


def test_virustotal_returns_401_without_token(
    client: FlaskClient,
) -> None:
    response = client.get("/api/virustotal")
    assert response.status_code == 401


@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".virustotal.routes.vt"
)
def test_virustotal_post_returns_405(
    mock_vt: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post("/api/virustotal", headers=auth_headers)
    assert response.status_code == 405


@patch.dict(os.environ, {"VIRUSTOTAL_API_KEY": "test-key"})
@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".virustotal.routes.vt"
)
def test_virustotal_scan_returns_results(
    mock_vt: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_client = MagicMock()
    mock_obj = MagicMock()
    mock_obj.reputation = 5
    mock_obj.last_analysis_stats = {"malicious": 0, "harmless": 70}
    mock_obj.last_analysis_date = None
    mock_client.get_object.return_value = mock_obj
    mock_vt.Client.return_value = mock_client

    response = client.post(
        "/api/virustotal/scan",
        json={"type": "domain", "value": "example.com"},
        headers=auth_headers,
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["result"]["type"] == "domain"
    assert data["result"]["value"] == "example.com"
    assert data["result"]["reputation"] == 5
    mock_client.close.assert_called_once()


def test_virustotal_scan_returns_400_without_params(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/virustotal/scan",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_virustotal_scan_returns_400_invalid_type(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/virustotal/scan",
        json={"type": "invalid", "value": "test"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "type must be one of" in data["error"]


@patch.dict(os.environ, {"VIRUSTOTAL_API_KEY": "test-key"})
@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".virustotal.routes.vt"
)
def test_virustotal_scan_returns_500_on_failure(
    mock_vt: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_client = MagicMock()
    mock_client.get_object.side_effect = Exception("VT error")
    mock_vt.Client.return_value = mock_client

    response = client.post(
        "/api/virustotal/scan",
        json={"type": "ip", "value": "1.2.3.4"},
        headers=auth_headers,
    )
    data = response.get_json()

    assert response.status_code == 500
    assert data["error"] == "VT error"


def test_virustotal_scan_returns_401_without_token(
    client: FlaskClient,
) -> None:
    response = client.post(
        "/api/virustotal/scan",
        json={"type": "ip", "value": "1.2.3.4"},
    )
    assert response.status_code == 401


def test_virustotal_scan_get_not_allowed(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.get(
        "/api/virustotal/scan", headers=auth_headers,
    )
    assert response.status_code in (404, 405)
