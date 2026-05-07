"""Integration tests for the /api/llm endpoint."""
import os
from unittest.mock import MagicMock, patch

from flask.testing import FlaskClient


@patch(
    "response_planner_backend.rest_api.resources.llm"
    ".routes._fetch_anthropic_models",
    return_value=[],
)
@patch(
    "response_planner_backend.rest_api.resources.llm.routes.genai"
)
@patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
def test_llm_returns_connected_status(
    mock_genai: MagicMock,
    mock_anthropic: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    fake_model = MagicMock()
    fake_model.name = "models/gemini-2.5-pro"
    fake_model.display_name = "Gemini 2.5 Pro"
    fake_model.description = "A thinking model"
    fake_model.input_token_limit = 1048576
    fake_model.output_token_limit = 8192
    fake_model.supported_actions = ["generateContent"]

    mock_client = MagicMock()
    mock_client.models.list.return_value = [fake_model]
    mock_genai.Client.return_value = mock_client

    response = client.get("/api/llm", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "connected"
    assert "timestamp" in data
    assert len(data["models"]) == 1
    assert data["models"][0]["name"] == "models/gemini-2.5-pro"


@patch(
    "response_planner_backend.rest_api.resources.llm"
    ".routes._fetch_anthropic_models",
    return_value=[],
)
@patch(
    "response_planner_backend.rest_api.resources.llm.routes.genai"
)
@patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
def test_llm_filters_non_thinking_models(
    mock_genai: MagicMock,
    mock_anthropic: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    """
    Models that do not support thinking should be excluded.
    """
    thinking_model = MagicMock()
    thinking_model.name = "models/gemini-2.5-flash"
    thinking_model.display_name = "Gemini 2.5 Flash"
    thinking_model.description = "A thinking model"
    thinking_model.input_token_limit = 1048576
    thinking_model.output_token_limit = 8192
    thinking_model.supported_actions = ["generateContent"]

    non_thinking_model = MagicMock()
    non_thinking_model.name = "models/gemini-2.0-flash"
    non_thinking_model.display_name = "Gemini 2.0 Flash"
    non_thinking_model.description = "A non-thinking model"
    non_thinking_model.input_token_limit = 1048576
    non_thinking_model.output_token_limit = 8192
    non_thinking_model.supported_actions = ["generateContent"]

    mock_client = MagicMock()
    mock_client.models.list.return_value = [
        thinking_model, non_thinking_model,
    ]
    mock_genai.Client.return_value = mock_client

    response = client.get("/api/llm", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert len(data["models"]) == 1
    assert data["models"][0]["name"] == "models/gemini-2.5-flash"


@patch(
    "response_planner_backend.rest_api.resources.llm"
    ".routes._fetch_anthropic_models",
    return_value=[],
)
@patch(
    "response_planner_backend.rest_api.resources.llm.routes.genai"
)
@patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
def test_llm_returns_error_status_on_failure(
    mock_genai: MagicMock,
    mock_anthropic: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_genai.Client.side_effect = Exception("Invalid API key")

    response = client.get("/api/llm", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "error"
    assert "timestamp" in data
    assert "Invalid API key" in data["error"]


def test_llm_returns_401_without_token(
    client: FlaskClient,
) -> None:
    response = client.get("/api/llm")
    assert response.status_code == 401


@patch(
    "response_planner_backend.rest_api.resources.llm"
    ".routes._fetch_anthropic_models",
    return_value=[],
)
@patch(
    "response_planner_backend.rest_api.resources.llm.routes.genai"
)
def test_llm_post_returns_405(
    mock_genai: MagicMock,
    mock_anthropic: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post("/api/llm", headers=auth_headers)
    assert response.status_code == 405
