"""Integration tests for the /api/example endpoint."""
from flask.testing import FlaskClient

from ccs_response_planner_backend.constants.constants import EXAMPLES


def test_example_returns_200(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/api/example", headers=auth_headers)
    assert response.status_code == 200


def test_example_returns_json_content_type(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/api/example", headers=auth_headers)
    assert response.content_type == "application/json"


def test_example_body_has_system_description(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    data = client.get("/api/example", headers=auth_headers).get_json()
    assert data["system_description"] == EXAMPLES.SYSTEM_DESCRIPTION


def test_example_body_has_security_alerts(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    data = client.get("/api/example", headers=auth_headers).get_json()
    assert data["security_alerts"] == EXAMPLES.SECURITY_ALERTS


def test_example_body_has_operator_feedback(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    data = client.get("/api/example", headers=auth_headers).get_json()
    assert data["operator_feedback"] == EXAMPLES.OPERATOR_FEEDBACK


def test_example_body_has_exactly_five_keys(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    data = client.get("/api/example", headers=auth_headers).get_json()
    assert len(data) == 5


def test_example_body_has_system_description_images(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    data = client.get("/api/example", headers=auth_headers).get_json()
    assert "system_description_images" in data
    assert isinstance(data["system_description_images"], list)


def test_example_body_has_specification(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    data = client.get("/api/example", headers=auth_headers).get_json()
    assert data["specification"] == EXAMPLES.SPECIFICATION


def test_example_post_returns_405(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    response = client.post("/api/example", headers=auth_headers)
    assert response.status_code == 405
