"""Integration tests for the /api/plan endpoint."""
from flask.testing import FlaskClient


def test_plan_returns_200_with_valid_input(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/plan",
        json={"incident_description": "Server compromised"},
        headers=auth_headers,
    )
    assert response.status_code == 200


def test_plan_returns_json_content_type(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/plan",
        json={"incident_description": "Server compromised"},
        headers=auth_headers,
    )
    assert response.content_type == "application/json"


def test_plan_echoes_incident_description(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    desc = "Server compromised via SSH brute force"
    data = client.post(
        "/api/plan", json={"incident_description": desc},
        headers=auth_headers,
    ).get_json()
    assert data["incident_description"] == desc


def test_plan_has_severity(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    data = client.post(
        "/api/plan",
        json={"incident_description": "Server compromised"},
        headers=auth_headers,
    ).get_json()
    assert "severity" in data
    assert isinstance(data["severity"], str)


def test_plan_has_status(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    data = client.post(
        "/api/plan",
        json={"incident_description": "Server compromised"},
        headers=auth_headers,
    ).get_json()
    assert "status" in data
    assert isinstance(data["status"], str)


def test_plan_has_non_empty_steps(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    data = client.post(
        "/api/plan",
        json={"incident_description": "Server compromised"},
        headers=auth_headers,
    ).get_json()
    assert "steps" in data
    assert isinstance(data["steps"], list)
    assert len(data["steps"]) > 0


def test_plan_returns_400_when_key_missing(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/plan", json={"wrong_key": "value"},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_plan_returns_400_when_value_empty(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/plan", json={"incident_description": ""},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_plan_returns_400_when_no_json_body(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/plan", content_type="application/json",
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_plan_error_message_is_correct(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    data = client.post(
        "/api/plan", json={"wrong_key": "value"},
        headers=auth_headers,
    ).get_json()
    assert data["error"] == "incident_description is required"


def test_plan_get_not_allowed(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/api/plan", headers=auth_headers)
    assert response.status_code in (404, 405)


def test_plan_steps_are_strings(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    data = client.post(
        "/api/plan",
        json={"incident_description": "Server compromised"},
        headers=auth_headers,
    ).get_json()
    for step in data["steps"]:
        assert isinstance(step, str)
