"""Integration tests for the /api/digital-twin endpoint."""
from unittest.mock import patch

from flask.testing import FlaskClient

from ccs_response_planner_backend.constants.constants import DIGITAL_TWIN


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
        "ccs_response_planner_backend.rest_api.resources.digital_twin"
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
