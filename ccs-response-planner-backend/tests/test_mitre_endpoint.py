"""Integration tests for the /api/mitre endpoint."""
from unittest.mock import MagicMock, patch

from flask.testing import FlaskClient


def _make_technique(
    name: str = "Brute Force",
    description: str = "Adversaries may use brute force techniques.",
    attack_id: str = "T1110",
    url: str = "https://attack.mitre.org/techniques/T1110",
    phase_name: str = "credential-access",
) -> MagicMock:
    technique = MagicMock()
    technique.name = name
    technique.description = description
    ref = MagicMock()
    ref.source_name = "mitre-attack"
    ref.external_id = attack_id
    ref.url = url
    technique.external_references = [ref]
    phase = MagicMock()
    phase.phase_name = phase_name
    technique.kill_chain_phases = [phase]
    return technique


@patch(
    "ccs_response_planner_backend.rest_api.resources.mitre.routes"
    "._get_attack_data"
)
def test_mitre_returns_connected_status(
    mock_get_data: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_data = MagicMock()
    mock_data.get_techniques.return_value = [_make_technique()]
    mock_get_data.return_value = mock_data

    response = client.get("/api/mitre", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "connected"
    assert "timestamp" in data
    assert data["technique_count"] == 1


@patch(
    "ccs_response_planner_backend.rest_api.resources.mitre.routes"
    "._get_attack_data"
)
def test_mitre_returns_error_status_on_failure(
    mock_get_data: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_get_data.side_effect = Exception("STIX load error")

    response = client.get("/api/mitre", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "error"
    assert data["error"] == "STIX load error"


def test_mitre_returns_401_without_token(
    client: FlaskClient,
) -> None:
    response = client.get("/api/mitre")
    assert response.status_code == 401


@patch(
    "ccs_response_planner_backend.rest_api.resources.mitre.routes"
    "._get_attack_data"
)
def test_mitre_post_returns_405(
    mock_get_data: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post("/api/mitre", headers=auth_headers)
    assert response.status_code == 405


@patch(
    "ccs_response_planner_backend.rest_api.resources.mitre.routes"
    "._get_attack_data"
)
def test_mitre_search_by_keyword(
    mock_get_data: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_data = MagicMock()
    mock_data.get_techniques.return_value = [
        _make_technique(name="Brute Force"),
        _make_technique(
            name="Phishing", attack_id="T1566",
            description="Adversaries may send phishing messages.",
        ),
    ]
    mock_get_data.return_value = mock_data

    response = client.post(
        "/api/mitre/search",
        json={"search": "brute"},
        headers=auth_headers,
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["query"] == "brute"
    assert len(data["results"]) == 1
    assert data["results"][0]["name"] == "Brute Force"


@patch(
    "ccs_response_planner_backend.rest_api.resources.mitre.routes"
    "._get_attack_data"
)
def test_mitre_search_by_id(
    mock_get_data: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_data = MagicMock()
    mock_data.get_object_by_attack_id.return_value = (
        _make_technique()
    )
    mock_get_data.return_value = mock_data

    response = client.post(
        "/api/mitre/search",
        json={"technique_id": "T1110"},
        headers=auth_headers,
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["query"] == "T1110"
    assert len(data["results"]) == 1
    assert data["results"][0]["id"] == "T1110"


def test_mitre_search_returns_400_without_params(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/mitre/search",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 400


@patch(
    "ccs_response_planner_backend.rest_api.resources.mitre.routes"
    "._get_attack_data"
)
def test_mitre_search_returns_500_on_failure(
    mock_get_data: MagicMock,
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    mock_get_data.side_effect = Exception("STIX error")

    response = client.post(
        "/api/mitre/search",
        json={"search": "test"},
        headers=auth_headers,
    )
    data = response.get_json()

    assert response.status_code == 500
    assert data["error"] == "STIX error"


def test_mitre_search_returns_401_without_token(
    client: FlaskClient,
) -> None:
    response = client.post(
        "/api/mitre/search",
        json={"search": "test"},
    )
    assert response.status_code == 401


def test_mitre_search_get_not_allowed(
    client: FlaskClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.get("/api/mitre/search", headers=auth_headers)
    assert response.status_code in (404, 405)
