"""Integration tests for the /api/health endpoint."""
from flask.testing import FlaskClient

from ccs_response_planner_backend.constants.constants import GENERAL


def test_health_returns_200(client: FlaskClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_returns_json_content_type(client: FlaskClient) -> None:
    response = client.get("/api/health")
    assert response.content_type == "application/json"


def test_health_body_has_status_ok(client: FlaskClient) -> None:
    data = client.get("/api/health").get_json()
    assert data["status"] == "ok"


def test_health_body_has_correct_app_name(client: FlaskClient) -> None:
    data = client.get("/api/health").get_json()
    assert data["app"] == GENERAL.APP_NAME


def test_health_post_returns_405(client: FlaskClient) -> None:
    response = client.post("/api/health")
    assert response.status_code == 405
