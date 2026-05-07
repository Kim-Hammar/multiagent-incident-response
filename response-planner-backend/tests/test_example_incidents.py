"""Tests for the /api/examples endpoints and DT configs list."""
from unittest.mock import patch

from flask.testing import FlaskClient


def test_list_examples_returns_200(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/api/examples", headers=auth_headers)
    assert response.status_code == 200


def test_list_examples_returns_empty_list(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    data = client.get("/api/examples", headers=auth_headers).get_json()
    assert data == []


def test_list_examples_returns_seeded_data(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    with patch(
        "response_planner_backend.rest_api.resources"
        ".example.routes.DatabaseFacade"
    ) as mock:
        mock.get_session_token_by_token.return_value = {
            "token": "test-token",
            "username": "admin",
            "timestamp": "now",
        }
        mock.list_example_incidents.return_value = [
            {"id": 1, "name": "Incident 1"},
        ]
        data = client.get(
            "/api/examples", headers=auth_headers
        ).get_json()
        assert len(data) == 1
        assert data[0]["name"] == "Incident 1"


def test_get_example_by_id_returns_404(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/api/examples/999", headers=auth_headers)
    assert response.status_code == 404


def test_get_example_by_id_returns_data(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    with patch(
        "response_planner_backend.rest_api.resources"
        ".example.routes.DatabaseFacade"
    ) as mock:
        mock.get_session_token_by_token.return_value = {
            "token": "test-token",
            "username": "admin",
            "timestamp": "now",
        }
        mock.get_example_incident.return_value = {
            "id": 1,
            "name": "Incident 1",
            "system_description": "desc",
            "system_description_image": "",
            "security_alerts": "alerts",
            "operator_feedback": "feedback",
            "specification": "spec",
            "incident_report": "report",
            "response_plan": "plan",
        }
        mock.get_config_id_by_incident.return_value = None
        response = client.get(
            "/api/examples/1", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == 1
        assert data["name"] == "Incident 1"
        assert data["system_description"] == "desc"
        assert data["security_alerts"] == "alerts"
        assert data["incident_report"] == "report"
        assert data["response_plan"] == "plan"
        assert "system_description_images" in data


def test_get_example_by_id_includes_images_when_present(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    with patch(
        "response_planner_backend.rest_api.resources"
        ".example.routes.DatabaseFacade"
    ) as mock:
        mock.get_session_token_by_token.return_value = {
            "token": "test-token",
            "username": "admin",
            "timestamp": "now",
        }
        mock.get_example_incident.return_value = {
            "id": 1,
            "name": "Incident 1",
            "system_description": "",
            "system_description_image": "data:image/png;base64,abc",
            "security_alerts": "",
            "operator_feedback": "",
            "specification": "",
            "incident_report": "",
            "response_plan": "",
        }
        mock.get_config_id_by_incident.return_value = None
        data = client.get(
            "/api/examples/1", headers=auth_headers
        ).get_json()
        assert data["system_description_images"] == [
            "data:image/png;base64,abc"
        ]


def test_list_dt_configs_returns_200(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    response = client.get(
        "/api/digital-twin/configs", headers=auth_headers
    )
    assert response.status_code == 200


def test_list_dt_configs_returns_empty_list(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    data = client.get(
        "/api/digital-twin/configs", headers=auth_headers
    ).get_json()
    assert data == []


def test_get_dt_config_by_id_returns_404(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    response = client.get(
        "/api/digital-twin/configs/999", headers=auth_headers
    )
    assert response.status_code == 404


def test_get_dt_config_by_id_returns_data(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    with patch(
        "response_planner_backend.rest_api.resources"
        ".digital_twin.routes.DatabaseFacade"
    ) as mock:
        mock.get_session_token_by_token.return_value = {
            "token": "test-token",
            "username": "admin",
            "timestamp": "now",
        }
        mock.get_digital_twin_config_by_id.return_value = {
            "id": 1,
            "name": "Incident 1",
            "config": {"networks": [], "hosts": [], "links": []},
            "example_incident_id": 1,
        }
        response = client.get(
            "/api/digital-twin/configs/1", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == 1
        assert data["name"] == "Incident 1"
        assert "config" in data


def test_examples_requires_auth(
    client: FlaskClient,
) -> None:
    response = client.get("/api/examples")
    assert response.status_code == 401


def test_examples_id_requires_auth(
    client: FlaskClient,
) -> None:
    response = client.get("/api/examples/1")
    assert response.status_code == 401


def test_dt_configs_requires_auth(
    client: FlaskClient,
) -> None:
    response = client.get("/api/digital-twin/configs")
    assert response.status_code == 401
