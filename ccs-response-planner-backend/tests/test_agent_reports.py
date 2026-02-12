"""Tests for agent report CRUD endpoints."""
import json


def test_save_report(client, auth_headers):
    """
    POST /api/agents/reports with valid body returns 201.
    """
    res = client.post(
        "/api/agents/reports",
        data=json.dumps({
            "agent_type": "information",
            "report": {"incident_summary": "test"},
        }),
        content_type="application/json",
        headers=auth_headers,
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data["id"] == 1
    assert data["agent_type"] == "information"


def test_save_report_missing_fields(client, auth_headers):
    """
    POST /api/agents/reports without agent_type returns 400.
    """
    res = client.post(
        "/api/agents/reports",
        data=json.dumps({"report": {"foo": "bar"}}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert res.status_code == 400
    assert "agent_type and report are required" in res.get_json()["error"]


def test_save_report_missing_report(client, auth_headers):
    """
    POST /api/agents/reports without report returns 400.
    """
    res = client.post(
        "/api/agents/reports",
        data=json.dumps({"agent_type": "pentest"}),
        content_type="application/json",
        headers=auth_headers,
    )
    assert res.status_code == 400


def test_list_reports(client, auth_headers):
    """
    GET /api/agents/reports returns 200 with a list.
    """
    res = client.get(
        "/api/agents/reports",
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)


def test_list_reports_with_filter(client, auth_headers):
    """
    GET /api/agents/reports?agent_type=pentest returns 200.
    """
    res = client.get(
        "/api/agents/reports?agent_type=pentest",
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)


def test_get_report_not_found(client, auth_headers):
    """
    GET /api/agents/reports/999 returns 404 when not found.
    """
    res = client.get(
        "/api/agents/reports/999",
        headers=auth_headers,
    )
    assert res.status_code == 404
    assert "not found" in res.get_json()["error"].lower()


def test_get_report_found(client, auth_headers, mock_db):
    """
    GET /api/agents/reports/1 returns 200 when found.
    """
    from unittest.mock import patch
    with patch(
        "ccs_response_planner_backend.rest_api.resources.agents"
        ".routes.DatabaseFacade"
    ) as m:
        m.get_agent_report.return_value = {
            "id": 1,
            "agent_type": "information",
            "username": "admin",
            "report": {"test": True},
            "created_at": "2026-01-01 00:00:00",
        }
        res = client.get(
            "/api/agents/reports/1",
            headers=auth_headers,
        )
    assert res.status_code == 200
    assert res.get_json()["id"] == 1


def test_delete_report_not_found(client, auth_headers):
    """
    DELETE /api/agents/reports/999 returns 404 when not found.
    """
    res = client.delete(
        "/api/agents/reports/999",
        headers=auth_headers,
    )
    assert res.status_code == 404


def test_delete_report_found(client, auth_headers):
    """
    DELETE /api/agents/reports/1 returns 200 when found.
    """
    from unittest.mock import patch
    with patch(
        "ccs_response_planner_backend.rest_api.resources.agents"
        ".routes.DatabaseFacade"
    ) as m:
        m.delete_agent_report.return_value = True
        res = client.delete(
            "/api/agents/reports/1",
            headers=auth_headers,
        )
    assert res.status_code == 200
    assert res.get_json()["deleted"] is True


def test_save_report_no_auth(client):
    """
    POST /api/agents/reports without token returns 401.
    """
    res = client.post(
        "/api/agents/reports",
        data=json.dumps({
            "agent_type": "information",
            "report": {},
        }),
        content_type="application/json",
    )
    assert res.status_code == 401


def test_save_report_with_incident_id(client, auth_headers, mock_db):
    """
    POST /api/agents/reports with incident_id returns 201.
    """
    from unittest.mock import patch
    with patch(
        "ccs_response_planner_backend.rest_api.resources.agents"
        ".routes.DatabaseFacade"
    ) as m:
        m.save_agent_report.return_value = {
            "id": 2,
            "agent_type": "information",
            "username": "admin",
            "report": {"summary": "test"},
            "created_at": "2026-01-01 00:00:00",
            "incident_id": 1,
            "incident_name": "Example Incident 1",
        }
        res = client.post(
            "/api/agents/reports",
            data=json.dumps({
                "agent_type": "information",
                "report": {"summary": "test"},
                "incident_id": 1,
            }),
            content_type="application/json",
            headers=auth_headers,
        )
    assert res.status_code == 201
    data = res.get_json()
    assert data["incident_id"] == 1
    assert data["incident_name"] == "Example Incident 1"


def test_list_reports_with_incident_filter(client, auth_headers):
    """
    GET /api/agents/reports?incident_id=1 returns 200.
    """
    res = client.get(
        "/api/agents/reports?incident_id=1",
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)


def test_list_reports_with_both_filters(client, auth_headers):
    """
    GET /api/agents/reports?agent_type=code&incident_id=1 returns 200.
    """
    res = client.get(
        "/api/agents/reports?agent_type=code&incident_id=1",
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)


def test_list_reports_no_auth(client):
    """
    GET /api/agents/reports without token returns 401.
    """
    res = client.get("/api/agents/reports")
    assert res.status_code == 401


def test_get_report_no_auth(client):
    """
    GET /api/agents/reports/1 without token returns 401.
    """
    res = client.get("/api/agents/reports/1")
    assert res.status_code == 401


def test_delete_report_no_auth(client):
    """
    DELETE /api/agents/reports/1 without token returns 401.
    """
    res = client.delete("/api/agents/reports/1")
    assert res.status_code == 401
