"""Integration tests for the /api/digital-twin endpoint."""
from unittest.mock import patch

from flask.testing import FlaskClient

from response_planner_backend.constants.constants import DIGITAL_TWIN


def test_get_returns_default_when_none_saved(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/api/digital-twin", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data == DIGITAL_TWIN.DEFAULT_CONFIG


def test_get_returns_saved_config(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    saved = {"hosts": [{"id": "a"}], "links": []}
    with patch(
        "response_planner_backend.rest_api.resources.digital_twin"
        ".routes.DatabaseFacade"
    ) as m:
        m.get_digital_twin_config.return_value = saved
        response = client.get(
            "/api/digital-twin", headers=auth_headers
        )
    assert response.status_code == 200
    assert response.get_json() == saved


def test_get_requires_auth(client: FlaskClient) -> None:
    response = client.get("/api/digital-twin")
    assert response.status_code == 401


def test_put_saves_valid_config(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    payload = {"networks": [], "hosts": [{"id": "x"}], "links": []}
    response = client.put(
        "/api/digital-twin",
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.get_json()["message"] == "Configuration saved"


def test_put_rejects_missing_networks(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    response = client.put(
        "/api/digital-twin",
        json={"hosts": [], "links": []},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_put_rejects_missing_hosts(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    response = client.put(
        "/api/digital-twin",
        json={"networks": [], "links": []},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_put_rejects_missing_links(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    response = client.put(
        "/api/digital-twin",
        json={"networks": [], "hosts": []},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_put_rejects_empty_body(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    response = client.put(
        "/api/digital-twin",
        headers=auth_headers,
        content_type="application/json",
    )
    assert response.status_code == 400


def test_put_requires_auth(client: FlaskClient) -> None:
    response = client.put(
        "/api/digital-twin",
        json={"networks": [], "hosts": [], "links": []},
    )
    assert response.status_code == 401


def test_reset_returns_default(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/digital-twin/reset", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.get_json() == DIGITAL_TWIN.DEFAULT_CONFIG


def test_reset_requires_auth(client: FlaskClient) -> None:
    response = client.post("/api/digital-twin/reset")
    assert response.status_code == 401


def test_post_to_base_returns_405(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/digital-twin", headers=auth_headers
    )
    assert response.status_code == 405


def test_delete_returns_405(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    response = client.delete(
        "/api/digital-twin", headers=auth_headers
    )
    assert response.status_code == 405


def test_validation_results_saved_after_validate(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    mock_config_row = {
        "id": 1,
        "name": "test",
        "config": {
            "specification_commands": [
                {
                    "host": "h1",
                    "command": "echo ok",
                    "description": "test cmd",
                },
            ],
        },
        "example_incident_id": None,
    }
    mock_results = [
        {
            "type": "result",
            "host": "h1",
            "command": "echo ok",
            "description": "test cmd",
            "passed": True,
            "output": "ok",
        },
    ]
    with patch(
        "response_planner_backend.rest_api.resources"
        ".digital_twin.routes.DatabaseFacade"
    ) as m:
        m.get_digital_twin_config_by_id.return_value = (
            mock_config_row
        )
        m.get_session_token_by_token.return_value = {
            "token": "t", "username": "u", "timestamp": "now",
        }
        with patch(
            "response_planner_backend.rest_api.resources"
            ".digital_twin.routes.DockerManager"
        ) as dm:
            dm.status.return_value = {"deployed": True}
            dm.validate.return_value = iter(mock_results)
            response = client.post(
                "/api/digital-twin/configs/1/validate",
                headers=auth_headers,
            )
            assert response.status_code == 200
            lines = [
                line for line in
                response.data.decode().strip().split("\n")
                if line.strip()
            ]
            import json
            parsed = [json.loads(l) for l in lines]
            assert any(p["type"] == "done" for p in parsed)
            m.save_validation_results.assert_called_once()
            call_args = (
                m.save_validation_results.call_args[0]
            )
            assert call_args[0] == 1
            assert len(call_args[1]) == 1
            assert call_args[1][0]["passed"] is True


def test_get_validation_results_empty(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    with patch(
        "response_planner_backend.rest_api.resources"
        ".digital_twin.routes.DatabaseFacade"
    ) as m:
        m.get_session_token_by_token.return_value = {
            "token": "t", "username": "u", "timestamp": "now",
        }
        m.get_validation_results.return_value = None
        response = client.get(
            "/api/digital-twin/configs/1/validation-results",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.get_json() is None


def test_get_validation_results_returns_data(
    client: FlaskClient, auth_headers: dict[str, str]
) -> None:
    stored = {
        "results": [{"passed": True, "host": "h1"}],
        "tested_at": "2026-02-12T10:00:00+00:00",
    }
    with patch(
        "response_planner_backend.rest_api.resources"
        ".digital_twin.routes.DatabaseFacade"
    ) as m:
        m.get_session_token_by_token.return_value = {
            "token": "t", "username": "u", "timestamp": "now",
        }
        m.get_validation_results.return_value = stored
        response = client.get(
            "/api/digital-twin/configs/1/validation-results",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["results"][0]["passed"] is True
        assert data["tested_at"] == "2026-02-12T10:00:00+00:00"
