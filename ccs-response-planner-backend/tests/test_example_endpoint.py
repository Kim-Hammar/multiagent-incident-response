"""Integration tests for the /api/example endpoint."""
from flask.testing import FlaskClient

from ccs_response_planner_backend.constants.constants import EXAMPLES


def test_example_returns_200(client: FlaskClient) -> None:
    response = client.get("/api/example")
    assert response.status_code == 200


def test_example_returns_json_content_type(client: FlaskClient) -> None:
    response = client.get("/api/example")
    assert response.content_type == "application/json"


def test_example_body_has_system_description(client: FlaskClient) -> None:
    data = client.get("/api/example").get_json()
    assert data["system_description"] == EXAMPLES.SYSTEM_DESCRIPTION


def test_example_body_has_security_alerts(client: FlaskClient) -> None:
    data = client.get("/api/example").get_json()
    assert data["security_alerts"] == EXAMPLES.SECURITY_ALERTS


def test_example_body_has_operator_feedback(client: FlaskClient) -> None:
    data = client.get("/api/example").get_json()
    assert data["operator_feedback"] == EXAMPLES.OPERATOR_FEEDBACK


def test_example_body_has_exactly_three_keys(client: FlaskClient) -> None:
    data = client.get("/api/example").get_json()
    assert len(data) == 3


def test_example_post_returns_405(client: FlaskClient) -> None:
    response = client.post("/api/example")
    assert response.status_code == 405
