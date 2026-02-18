"""Tests for planning session endpoints."""
import json
from unittest.mock import MagicMock, patch

from flask.testing import FlaskClient


class TestGetActiveSession:
    """Tests for GET /api/agents/sessions/active."""

    def test_returns_401_without_token(
        self, client: FlaskClient,
    ) -> None:
        """
        Verify that the endpoint requires authentication.
        """
        resp = client.get("/api/agents/sessions/active")
        assert resp.status_code == 401

    @patch(
        "ccs_response_planner_backend.rest_api.resources"
        ".agents.routes.DatabaseFacade",
    )
    def test_returns_null_when_no_session(
        self, mock_db: MagicMock,
        client: FlaskClient,
        auth_headers: dict[str, str],
    ) -> None:
        """
        Verify that the endpoint returns null when no active session.
        """
        from tests.conftest import _mock_get_token
        mock_db.get_session_token_by_token.side_effect = (
            _mock_get_token
        )
        mock_db.get_active_planning_session.return_value = (
            None
        )
        resp = client.get(
            "/api/agents/sessions/active",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["session"] is None

    @patch(
        "ccs_response_planner_backend.rest_api.resources"
        ".agents.routes.DatabaseFacade",
    )
    def test_returns_active_session(
        self, mock_db: MagicMock,
        client: FlaskClient,
        auth_headers: dict[str, str],
    ) -> None:
        """
        Verify that the endpoint returns an active session.
        """
        from tests.conftest import _mock_get_token
        mock_db.get_session_token_by_token.side_effect = (
            _mock_get_token
        )
        session = {
            "id": 1,
            "username": "admin",
            "status": "active",
            "conversation_history": [],
            "pending_proposal": None,
            "incident_inputs": {"systemDescription": "x"},
            "agent_config": {"orchestratorModel": "m"},
            "context_usage": None,
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
        }
        mock_db.get_active_planning_session.return_value = (
            session
        )
        resp = client.get(
            "/api/agents/sessions/active",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["session"]["id"] == 1
        assert data["session"]["status"] == "active"

    @patch(
        "ccs_response_planner_backend.rest_api.resources"
        ".agents.routes.DatabaseFacade",
    )
    def test_passes_agent_type_to_facade(
        self, mock_db: MagicMock,
        client: FlaskClient,
        auth_headers: dict[str, str],
    ) -> None:
        """
        Verify that the agent_type query param is passed
        to get_active_planning_session.
        """
        from tests.conftest import _mock_get_token
        mock_db.get_session_token_by_token.side_effect = (
            _mock_get_token
        )
        mock_db.get_active_planning_session.return_value = (
            None
        )
        resp = client.get(
            "/api/agents/sessions/active"
            "?agent_type=report",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        mock_db.get_active_planning_session.assert_called_once_with(
            "admin", agent_type="report",
        )

    @patch(
        "ccs_response_planner_backend.rest_api.resources"
        ".agents.routes.DatabaseFacade",
    )
    def test_passes_none_agent_type_when_omitted(
        self, mock_db: MagicMock,
        client: FlaskClient,
        auth_headers: dict[str, str],
    ) -> None:
        """
        Verify that agent_type defaults to None when not
        provided in query params.
        """
        from tests.conftest import _mock_get_token
        mock_db.get_session_token_by_token.side_effect = (
            _mock_get_token
        )
        mock_db.get_active_planning_session.return_value = (
            None
        )
        resp = client.get(
            "/api/agents/sessions/active",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        mock_db.get_active_planning_session.assert_called_once_with(
            "admin", agent_type=None,
        )


class TestCreateSession:
    """Tests for POST /api/agents/sessions."""

    def test_returns_401_without_token(
        self, client: FlaskClient,
    ) -> None:
        """
        Verify that the endpoint requires authentication.
        """
        resp = client.post(
            "/api/agents/sessions",
            data=json.dumps({
                "incident_inputs": {"a": 1},
                "agent_config": {"b": 2},
            }),
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_returns_400_without_incident_inputs(
        self, client: FlaskClient,
        auth_headers: dict[str, str],
    ) -> None:
        """
        Verify that incident_inputs is required.
        """
        resp = client.post(
            "/api/agents/sessions",
            data=json.dumps({"agent_config": {"b": 2}}),
            content_type="application/json",
            headers=auth_headers,
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "incident_inputs" in data["error"]

    def test_returns_400_without_agent_config(
        self, client: FlaskClient,
        auth_headers: dict[str, str],
    ) -> None:
        """
        Verify that agent_config is required.
        """
        resp = client.post(
            "/api/agents/sessions",
            data=json.dumps({
                "incident_inputs": {"a": 1},
            }),
            content_type="application/json",
            headers=auth_headers,
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "agent_config" in data["error"]

    @patch(
        "ccs_response_planner_backend.rest_api.resources"
        ".agents.routes.DatabaseFacade",
    )
    def test_creates_session(
        self, mock_db: MagicMock,
        client: FlaskClient,
        auth_headers: dict[str, str],
    ) -> None:
        """
        Verify that a session is created successfully.
        """
        from tests.conftest import _mock_get_token
        mock_db.get_session_token_by_token.side_effect = (
            _mock_get_token
        )
        mock_db.create_planning_session.return_value = {
            "id": 42,
            "username": "admin",
            "status": "active",
            "conversation_history": [],
            "pending_proposal": None,
            "incident_inputs": {"systemDescription": "x"},
            "agent_config": {"orchestratorModel": "m"},
            "context_usage": None,
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
        }
        resp = client.post(
            "/api/agents/sessions",
            data=json.dumps({
                "incident_inputs": {
                    "systemDescription": "x",
                },
                "agent_config": {
                    "orchestratorModel": "m",
                },
            }),
            content_type="application/json",
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["session"]["id"] == 42
        mock_db.create_planning_session.assert_called_once()

    @patch(
        "ccs_response_planner_backend.rest_api.resources"
        ".agents.routes.DatabaseFacade",
    )
    def test_passes_agent_type_to_facade(
        self, mock_db: MagicMock,
        client: FlaskClient,
        auth_headers: dict[str, str],
    ) -> None:
        """
        Verify that agent_type in the body is passed to
        create_planning_session.
        """
        from tests.conftest import _mock_get_token
        mock_db.get_session_token_by_token.side_effect = (
            _mock_get_token
        )
        mock_db.create_planning_session.return_value = {
            "id": 43,
            "username": "admin",
            "status": "active",
            "conversation_history": [],
            "pending_proposal": None,
            "incident_inputs": {"systemDescription": "x"},
            "agent_config": {"model": "m"},
            "context_usage": None,
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
            "agent_type": "report",
        }
        resp = client.post(
            "/api/agents/sessions",
            data=json.dumps({
                "incident_inputs": {
                    "systemDescription": "x",
                },
                "agent_config": {"model": "m"},
                "agent_type": "report",
            }),
            content_type="application/json",
            headers=auth_headers,
        )
        assert resp.status_code == 201
        call_kwargs = (
            mock_db.create_planning_session.call_args
        )
        assert call_kwargs[1]["agent_type"] == "report"

    @patch(
        "ccs_response_planner_backend.rest_api.resources"
        ".agents.routes.DatabaseFacade",
    )
    def test_agent_type_defaults_to_none(
        self, mock_db: MagicMock,
        client: FlaskClient,
        auth_headers: dict[str, str],
    ) -> None:
        """
        Verify that agent_type defaults to None when not in body.
        """
        from tests.conftest import _mock_get_token
        mock_db.get_session_token_by_token.side_effect = (
            _mock_get_token
        )
        mock_db.create_planning_session.return_value = {
            "id": 44,
            "username": "admin",
            "status": "active",
            "conversation_history": [],
            "pending_proposal": None,
            "incident_inputs": {"systemDescription": "x"},
            "agent_config": {"model": "m"},
            "context_usage": None,
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
        }
        resp = client.post(
            "/api/agents/sessions",
            data=json.dumps({
                "incident_inputs": {
                    "systemDescription": "x",
                },
                "agent_config": {"model": "m"},
            }),
            content_type="application/json",
            headers=auth_headers,
        )
        assert resp.status_code == 201
        call_kwargs = (
            mock_db.create_planning_session.call_args
        )
        assert call_kwargs[1]["agent_type"] is None


class TestUpdateSession:
    """Tests for PUT /api/agents/sessions/<id>."""

    def test_returns_401_without_token(
        self, client: FlaskClient,
    ) -> None:
        """
        Verify that the endpoint requires authentication.
        """
        resp = client.put(
            "/api/agents/sessions/1",
            data=json.dumps({"status": "completed"}),
            content_type="application/json",
        )
        assert resp.status_code == 401

    @patch(
        "ccs_response_planner_backend.rest_api.resources"
        ".agents.routes.DatabaseFacade",
    )
    def test_updates_session(
        self, mock_db: MagicMock,
        client: FlaskClient,
        auth_headers: dict[str, str],
    ) -> None:
        """
        Verify that a session is updated successfully.
        """
        from tests.conftest import _mock_get_token
        mock_db.get_session_token_by_token.side_effect = (
            _mock_get_token
        )
        mock_db.update_planning_session.return_value = True
        resp = client.put(
            "/api/agents/sessions/1",
            data=json.dumps({
                "status": "completed",
                "conversation_history": [
                    {"type": "reasoning", "text": "hi"},
                ],
            }),
            content_type="application/json",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    @patch(
        "ccs_response_planner_backend.rest_api.resources"
        ".agents.routes.DatabaseFacade",
    )
    def test_returns_404_when_not_found(
        self, mock_db: MagicMock,
        client: FlaskClient,
        auth_headers: dict[str, str],
    ) -> None:
        """
        Verify that 404 is returned for non-existent session.
        """
        from tests.conftest import _mock_get_token
        mock_db.get_session_token_by_token.side_effect = (
            _mock_get_token
        )
        mock_db.update_planning_session.return_value = False
        resp = client.put(
            "/api/agents/sessions/999",
            data=json.dumps({"status": "completed"}),
            content_type="application/json",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @patch(
        "ccs_response_planner_backend.rest_api.resources"
        ".agents.routes.DatabaseFacade",
    )
    def test_updates_session_with_ui_state(
        self, mock_db: MagicMock,
        client: FlaskClient,
        auth_headers: dict[str, str],
    ) -> None:
        """
        Verify that ui_state is passed through to the facade.
        """
        from tests.conftest import _mock_get_token
        mock_db.get_session_token_by_token.side_effect = (
            _mock_get_token
        )
        mock_db.update_planning_session.return_value = True
        ui = {"running": True, "executingTool": "nmap"}
        resp = client.put(
            "/api/agents/sessions/1",
            data=json.dumps({"ui_state": ui}),
            content_type="application/json",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        call_kwargs = (
            mock_db.update_planning_session.call_args
        )
        assert call_kwargs[1]["ui_state"] == ui

    @patch(
        "ccs_response_planner_backend.rest_api.resources"
        ".agents.routes.DatabaseFacade",
    )
    def test_clears_pending_proposal_with_null(
        self, mock_db: MagicMock,
        client: FlaskClient,
        auth_headers: dict[str, str],
    ) -> None:
        """
        Verify that passing pending_proposal=null clears it.
        """
        from tests.conftest import _mock_get_token
        mock_db.get_session_token_by_token.side_effect = (
            _mock_get_token
        )
        mock_db.update_planning_session.return_value = True
        resp = client.put(
            "/api/agents/sessions/1",
            data=json.dumps({
                "pending_proposal": None,
            }),
            content_type="application/json",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        call_kwargs = (
            mock_db.update_planning_session.call_args
        )
        assert call_kwargs[1]["pending_proposal"] is False


class TestDeleteSession:
    """Tests for DELETE /api/agents/sessions/<id>."""

    def test_returns_401_without_token(
        self, client: FlaskClient,
    ) -> None:
        """
        Verify that the endpoint requires authentication.
        """
        resp = client.delete("/api/agents/sessions/1")
        assert resp.status_code == 401

    @patch(
        "ccs_response_planner_backend.rest_api.resources"
        ".agents.routes.DatabaseFacade",
    )
    def test_deletes_session(
        self, mock_db: MagicMock,
        client: FlaskClient,
        auth_headers: dict[str, str],
    ) -> None:
        """
        Verify that a session is deleted successfully.
        """
        from tests.conftest import _mock_get_token
        mock_db.get_session_token_by_token.side_effect = (
            _mock_get_token
        )
        mock_db.delete_planning_session.return_value = True
        resp = client.delete(
            "/api/agents/sessions/1",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    @patch(
        "ccs_response_planner_backend.rest_api.resources"
        ".agents.routes.DatabaseFacade",
    )
    def test_returns_404_when_not_found(
        self, mock_db: MagicMock,
        client: FlaskClient,
        auth_headers: dict[str, str],
    ) -> None:
        """
        Verify that 404 is returned for non-existent session.
        """
        from tests.conftest import _mock_get_token
        mock_db.get_session_token_by_token.side_effect = (
            _mock_get_token
        )
        mock_db.delete_planning_session.return_value = (
            False
        )
        resp = client.delete(
            "/api/agents/sessions/999",
            headers=auth_headers,
        )
        assert resp.status_code == 404
