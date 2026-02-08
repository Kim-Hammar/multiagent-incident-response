"""Integration tests for the /api/otx endpoint."""
import os
from unittest.mock import MagicMock, patch

from flask.testing import FlaskClient


@patch.dict(os.environ, {"OTX_API_KEY": "test-key"})
@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".otx.routes.OTXv2"
)
def test_otx_returns_connected_status(
    mock_otx_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_otx = MagicMock()
    mock_otx.search_pulses.return_value = {"results": []}
    mock_otx_cls.return_value = mock_otx

    response = client.get("/api/otx", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "connected"
    assert "timestamp" in data


@patch.dict(os.environ, {"OTX_API_KEY": "test-key"})
@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".otx.routes.OTXv2"
)
def test_otx_returns_error_status_on_failure(
    mock_otx_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_otx_cls.side_effect = Exception("Invalid API key")

    response = client.get("/api/otx", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "error"
    assert data["error"] == "Invalid API key"


def test_otx_returns_401_without_token(
    client: FlaskClient,
) -> None:
    response = client.get("/api/otx")
    assert response.status_code == 401


@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".otx.routes.OTXv2"
)
def test_otx_post_returns_405(
    mock_otx_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post("/api/otx", headers=auth_headers)
    assert response.status_code == 405


@patch.dict(os.environ, {"OTX_API_KEY": "test-key"})
@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".otx.routes.OTXv2"
)
def test_otx_search_returns_results(
    mock_otx_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_otx = MagicMock()
    mock_otx.get_indicator_details_full.return_value = {
        "general": {
            "reputation": 0,
            "pulse_info": {
                "count": 1,
                "pulses": [
                    {
                        "name": "Test Pulse",
                        "description": "A test pulse",
                        "created": "2025-01-01",
                        "tags": ["test"],
                    },
                ],
            },
        },
    }
    mock_otx_cls.return_value = mock_otx

    response = client.post(
        "/api/otx/search",
        json={"type": "IPv4", "value": "8.8.8.8"},
        headers=auth_headers,
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["result"]["type"] == "IPv4"
    assert data["result"]["value"] == "8.8.8.8"
    assert data["result"]["pulse_count"] == 1
    assert len(data["result"]["pulses"]) == 1
    assert data["result"]["pulses"][0]["name"] == "Test Pulse"


def test_otx_search_returns_400_without_params(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/otx/search",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_otx_search_returns_400_invalid_type(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/otx/search",
        json={"type": "invalid", "value": "test"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "type must be one of" in data["error"]


@patch.dict(os.environ, {"OTX_API_KEY": "test-key"})
@patch(
    "ccs_response_planner_backend.rest_api.resources"
    ".otx.routes.OTXv2"
)
def test_otx_search_returns_500_on_failure(
    mock_otx_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_otx = MagicMock()
    mock_otx.get_indicator_details_full.side_effect = Exception(
        "OTX error",
    )
    mock_otx_cls.return_value = mock_otx

    response = client.post(
        "/api/otx/search",
        json={"type": "IPv4", "value": "1.2.3.4"},
        headers=auth_headers,
    )
    data = response.get_json()

    assert response.status_code == 500
    assert data["error"] == "OTX error"


def test_otx_search_returns_401_without_token(
    client: FlaskClient,
) -> None:
    response = client.post(
        "/api/otx/search",
        json={"type": "IPv4", "value": "1.2.3.4"},
    )
    assert response.status_code == 401


def test_otx_search_get_not_allowed(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.get("/api/otx/search", headers=auth_headers)
    assert response.status_code in (404, 405)
