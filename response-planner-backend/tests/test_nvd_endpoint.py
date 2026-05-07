"""Integration tests for the /api/nvd endpoint."""
from unittest.mock import MagicMock, patch

from flask.testing import FlaskClient


@patch(
    "response_planner_backend.rest_api.resources.nvd.routes.nvdlib"
)
def test_nvd_returns_connected_status(
    mock_nvdlib: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_cve = MagicMock()
    mock_cve.id = "CVE-2021-44228"
    mock_nvdlib.searchCVE.return_value = [mock_cve]

    response = client.get("/api/nvd", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "connected"
    assert "timestamp" in data
    assert data["cve_count"] == 1


@patch(
    "response_planner_backend.rest_api.resources.nvd.routes.nvdlib"
)
def test_nvd_returns_error_status_on_failure(
    mock_nvdlib: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_nvdlib.searchCVE.side_effect = Exception("API error")

    response = client.get("/api/nvd", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "error"
    assert "timestamp" in data
    assert data["error"] == "API error"


def test_nvd_returns_401_without_token(
    client: FlaskClient,
) -> None:
    response = client.get("/api/nvd")
    assert response.status_code == 401


@patch(
    "response_planner_backend.rest_api.resources.nvd.routes.nvdlib"
)
def test_nvd_post_returns_405(
    mock_nvdlib: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post("/api/nvd", headers=auth_headers)
    assert response.status_code == 405


@patch(
    "response_planner_backend.rest_api.resources.nvd.routes.nvdlib"
)
def test_nvd_search_returns_results(
    mock_nvdlib: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_cve = MagicMock()
    mock_cve.id = "CVE-2021-44228"
    mock_desc = MagicMock()
    mock_desc.lang = "en"
    mock_desc.value = "Log4Shell vulnerability"
    mock_cve.descriptions = [mock_desc]
    mock_cve.v31score = 10.0
    mock_cve.published = "2021-12-10"
    mock_nvdlib.searchCVE.return_value = [mock_cve]

    response = client.post(
        "/api/nvd/search",
        json={"cve_id": "CVE-2021-44228"},
        headers=auth_headers,
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["query"] == "CVE-2021-44228"
    assert len(data["results"]) == 1
    assert data["results"][0]["id"] == "CVE-2021-44228"
    assert data["results"][0]["description"] == "Log4Shell vulnerability"
    assert data["results"][0]["score"] == 10.0


def test_nvd_search_returns_400_without_params(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/nvd/search",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


@patch(
    "response_planner_backend.rest_api.resources.nvd.routes.nvdlib"
)
def test_nvd_search_returns_500_on_failure(
    mock_nvdlib: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_nvdlib.searchCVE.side_effect = Exception("NVD API error")

    response = client.post(
        "/api/nvd/search",
        json={"keyword": "log4j"},
        headers=auth_headers,
    )
    data = response.get_json()

    assert response.status_code == 500
    assert data["error"] == "NVD API error"


def test_nvd_search_returns_401_without_token(
    client: FlaskClient,
) -> None:
    response = client.post(
        "/api/nvd/search",
        json={"keyword": "test"},
    )
    assert response.status_code == 401


def test_nvd_search_get_not_allowed(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.get("/api/nvd/search", headers=auth_headers)
    assert response.status_code in (404, 405)
