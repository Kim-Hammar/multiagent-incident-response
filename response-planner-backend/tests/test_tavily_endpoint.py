"""Integration tests for the /api/tavily endpoint."""
from unittest.mock import MagicMock, patch

from flask.testing import FlaskClient


@patch(
    "response_planner_backend.rest_api.resources.tavily.routes.TavilyClient"
)
def test_tavily_returns_connected_status(
    mock_tavily_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_client = MagicMock()
    mock_client.search.return_value = {"response_time": 0.42}
    mock_tavily_cls.return_value = mock_client

    response = client.get("/api/tavily", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "connected"
    assert "timestamp" in data
    assert data["response_time"] == 0.42


@patch(
    "response_planner_backend.rest_api.resources.tavily.routes.TavilyClient"
)
def test_tavily_returns_error_status_on_failure(
    mock_tavily_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_tavily_cls.side_effect = Exception("Invalid API key")

    response = client.get("/api/tavily", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "error"
    assert "timestamp" in data
    assert data["error"] == "Invalid API key"


def test_tavily_returns_401_without_token(
    client: FlaskClient,
) -> None:
    response = client.get("/api/tavily")
    assert response.status_code == 401


@patch(
    "response_planner_backend.rest_api.resources.tavily.routes.TavilyClient"
)
def test_tavily_post_returns_405(
    mock_tavily_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post("/api/tavily", headers=auth_headers)
    assert response.status_code == 405


@patch(
    "response_planner_backend.rest_api.resources.tavily.routes.TavilyClient"
)
def test_tavily_search_returns_results(
    mock_tavily_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_client = MagicMock()
    mock_client.search.return_value = {
        "response_time": 0.55,
        "results": [
            {
                "title": "Example",
                "url": "https://example.com",
                "content": "Some content",
                "score": 0.9,
            },
        ],
    }
    mock_tavily_cls.return_value = mock_client

    response = client.post(
        "/api/tavily/search",
        json={"query": "test query", "max_results": 3},
        headers=auth_headers,
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["query"] == "test query"
    assert len(data["results"]) == 1
    assert data["results"][0]["title"] == "Example"
    assert data["response_time"] == 0.55


def test_tavily_search_returns_400_without_query(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/tavily/search",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


@patch(
    "response_planner_backend.rest_api.resources.tavily.routes.TavilyClient"
)
def test_tavily_search_returns_500_on_failure(
    mock_tavily_cls: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_client = MagicMock()
    mock_client.search.side_effect = Exception("API error")
    mock_tavily_cls.return_value = mock_client

    response = client.post(
        "/api/tavily/search",
        json={"query": "test"},
        headers=auth_headers,
    )
    data = response.get_json()

    assert response.status_code == 500
    assert data["error"] == "API error"


def test_tavily_search_returns_401_without_token(
    client: FlaskClient,
) -> None:
    response = client.post(
        "/api/tavily/search",
        json={"query": "test"},
    )
    assert response.status_code == 401


def test_tavily_search_get_not_allowed(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.get("/api/tavily/search", headers=auth_headers)
    assert response.status_code in (404, 405)
