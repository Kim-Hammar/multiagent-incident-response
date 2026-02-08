"""Integration tests for the /api/abuseipdb endpoint."""
import os
from unittest.mock import MagicMock, patch

from flask.testing import FlaskClient


@patch.dict(os.environ, {"ABUSEIPDB_API_KEY": "test-key"})
@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".abuseipdb.routes.http_requests"
)
def test_abuseipdb_returns_connected_status(
    mock_requests: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_requests.get.return_value = mock_resp

    response = client.get("/api/abuseipdb", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "connected"
    assert "timestamp" in data


@patch.dict(os.environ, {"ABUSEIPDB_API_KEY": "test-key"})
@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".abuseipdb.routes.http_requests"
)
def test_abuseipdb_returns_error_status_on_failure(
    mock_requests: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_requests.get.side_effect = Exception("Connection refused")

    response = client.get("/api/abuseipdb", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "error"
    assert data["error"] == "Connection refused"


def test_abuseipdb_returns_401_without_token(
    client: FlaskClient,
) -> None:
    response = client.get("/api/abuseipdb")
    assert response.status_code == 401


@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".abuseipdb.routes.http_requests"
)
def test_abuseipdb_post_returns_405(
    mock_requests: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post("/api/abuseipdb", headers=auth_headers)
    assert response.status_code == 405


@patch.dict(os.environ, {"ABUSEIPDB_API_KEY": "test-key"})
@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".abuseipdb.routes.http_requests"
)
def test_abuseipdb_check_returns_results(
    mock_requests: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "data": {
            "ipAddress": "1.2.3.4",
            "abuseConfidenceScore": 75,
            "isp": "Example ISP",
            "countryCode": "US",
            "totalReports": 42,
            "lastReportedAt": "2025-01-01T00:00:00+00:00",
            "isPublic": True,
        }
    }
    mock_requests.get.return_value = mock_resp

    response = client.post(
        "/api/abuseipdb/check",
        json={"ip": "1.2.3.4"},
        headers=auth_headers,
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["result"]["ip"] == "1.2.3.4"
    assert data["result"]["abuse_confidence_score"] == 75
    assert data["result"]["isp"] == "Example ISP"
    assert data["result"]["country_code"] == "US"
    assert data["result"]["total_reports"] == 42


def test_abuseipdb_check_returns_400_without_ip(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/abuseipdb/check",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


@patch.dict(os.environ, {"ABUSEIPDB_API_KEY": "test-key"})
@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".abuseipdb.routes.http_requests"
)
def test_abuseipdb_check_returns_500_on_failure(
    mock_requests: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_requests.get.side_effect = Exception("API error")

    response = client.post(
        "/api/abuseipdb/check",
        json={"ip": "1.2.3.4"},
        headers=auth_headers,
    )
    data = response.get_json()

    assert response.status_code == 500
    assert data["error"] == "API error"


def test_abuseipdb_check_returns_401_without_token(
    client: FlaskClient,
) -> None:
    response = client.post(
        "/api/abuseipdb/check",
        json={"ip": "1.2.3.4"},
    )
    assert response.status_code == 401


def test_abuseipdb_check_get_not_allowed(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.get(
        "/api/abuseipdb/check", headers=auth_headers,
    )
    assert response.status_code in (404, 405)
