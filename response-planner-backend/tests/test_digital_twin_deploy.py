"""Tests for digital twin deploy, stop, and status endpoints."""
import json
from unittest.mock import patch

from flask.testing import FlaskClient


def _parse_ndjson(data: bytes) -> list[dict]:
    """
    Parse NDJSON response bytes into a list of dicts.

    :param data: raw response bytes
    :return: list of parsed JSON objects
    """
    lines = data.decode("utf-8").strip().split("\n")
    return [json.loads(line) for line in lines if line.strip()]


class TestDeployEndpoint:
    """Tests for POST /api/digital-twin/deploy."""

    def test_deploy_returns_200_with_auth(
        self, client: FlaskClient, auth_headers: dict[str, str]
    ) -> None:
        """
        Deploy should stream NDJSON with progress and a result line.
        """
        with patch(
            "response_planner_backend.rest_api.resources"
            ".digital_twin.routes.DockerManager"
        ) as mock:
            mock.deploy.return_value = iter([
                {"type": "progress",
                 "message": "Creating network dt_net_zone1"},
                {"type": "progress",
                 "message": "Deployment complete"},
                {"type": "result", "data": {
                    "networks": ["dt_net_zone1"],
                    "containers": [{"host_id": "i1_server_1"}],
                }},
            ])
            resp = client.post(
                "/api/digital-twin/deploy", headers=auth_headers
            )
        assert resp.status_code == 200
        assert resp.content_type == "application/x-ndjson"
        msgs = _parse_ndjson(resp.data)
        progress_msgs = [m for m in msgs if m["type"] == "progress"]
        assert len(progress_msgs) == 2
        result_msgs = [m for m in msgs if m["type"] == "result"]
        assert len(result_msgs) == 1
        assert "networks" in result_msgs[0]["data"]
        assert "containers" in result_msgs[0]["data"]

    def test_deploy_requires_auth(self, client: FlaskClient) -> None:
        """
        Deploy should return 401 without a valid token.
        """
        resp = client.post("/api/digital-twin/deploy")
        assert resp.status_code == 401

    def test_deploy_returns_error_on_docker_failure(
        self, client: FlaskClient, auth_headers: dict[str, str]
    ) -> None:
        """
        Deploy should stream an error line when DockerManager raises.
        """
        with patch(
            "response_planner_backend.rest_api.resources"
            ".digital_twin.routes.DockerManager"
        ) as mock:
            mock.deploy.side_effect = RuntimeError("Docker is down")
            resp = client.post(
                "/api/digital-twin/deploy", headers=auth_headers
            )
        assert resp.status_code == 200
        msgs = _parse_ndjson(resp.data)
        error_msgs = [m for m in msgs if m["type"] == "error"]
        assert len(error_msgs) == 1
        assert "Docker is down" in error_msgs[0]["message"]


class TestStopEndpoint:
    """Tests for POST /api/digital-twin/stop."""

    def test_stop_returns_200_with_auth(
        self, client: FlaskClient, auth_headers: dict[str, str]
    ) -> None:
        """
        Stop should stream NDJSON with progress and a result line.
        """
        with patch(
            "response_planner_backend.rest_api.resources"
            ".digital_twin.routes.DockerManager"
        ) as mock:
            mock.stop.return_value = iter([
                {"type": "progress",
                 "message": "[1/1] Removing dt_i1_server_1"},
                {"type": "progress",
                 "message": "Shutdown complete"},
                {"type": "result",
                 "data": {"removed": ["dt_i1_server_1"]}},
            ])
            resp = client.post(
                "/api/digital-twin/stop", headers=auth_headers
            )
        assert resp.status_code == 200
        assert resp.content_type == "application/x-ndjson"
        msgs = _parse_ndjson(resp.data)
        progress_msgs = [m for m in msgs if m["type"] == "progress"]
        assert len(progress_msgs) == 2
        result_msgs = [m for m in msgs if m["type"] == "result"]
        assert len(result_msgs) == 1
        assert "removed" in result_msgs[0]["data"]

    def test_stop_requires_auth(self, client: FlaskClient) -> None:
        """
        Stop should return 401 without a valid token.
        """
        resp = client.post("/api/digital-twin/stop")
        assert resp.status_code == 401

    def test_stop_returns_error_on_docker_failure(
        self, client: FlaskClient, auth_headers: dict[str, str]
    ) -> None:
        """
        Stop should stream an error line when DockerManager raises.
        """
        with patch(
            "response_planner_backend.rest_api.resources"
            ".digital_twin.routes.DockerManager"
        ) as mock:
            mock.stop.side_effect = RuntimeError("Docker is down")
            resp = client.post(
                "/api/digital-twin/stop", headers=auth_headers
            )
        assert resp.status_code == 200
        msgs = _parse_ndjson(resp.data)
        error_msgs = [m for m in msgs if m["type"] == "error"]
        assert len(error_msgs) == 1
        assert "Docker is down" in error_msgs[0]["message"]


class TestStatusEndpoint:
    """Tests for GET /api/digital-twin/status."""

    def test_status_returns_200_with_auth(
        self, client: FlaskClient, auth_headers: dict[str, str]
    ) -> None:
        """
        Status should return 200 with deployment state when authenticated.
        """
        resp = client.get("/api/digital-twin/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "deployed" in data
        assert "containers" in data

    def test_status_requires_auth(self, client: FlaskClient) -> None:
        """
        Status should return 401 without a valid token.
        """
        resp = client.get("/api/digital-twin/status")
        assert resp.status_code == 401

    def test_status_returns_500_on_docker_error(
        self, client: FlaskClient, auth_headers: dict[str, str]
    ) -> None:
        """
        Status should return 500 when DockerManager raises an exception.
        """
        with patch(
            "response_planner_backend.rest_api.resources"
            ".digital_twin.routes.DockerManager"
        ) as mock:
            mock.status.side_effect = RuntimeError("Docker is down")
            resp = client.get(
                "/api/digital-twin/status", headers=auth_headers
            )
        assert resp.status_code == 500
        assert "error" in resp.get_json()


class TestDeployConfigEndpoint:
    """Tests for POST /api/digital-twin/configs/<id>/deploy."""

    def test_deploy_config_requires_auth(
        self, client: FlaskClient
    ) -> None:
        """
        Per-config deploy should return 401 without a valid token.
        """
        resp = client.post("/api/digital-twin/configs/1/deploy")
        assert resp.status_code == 401

    def test_deploy_config_not_found(
        self, client: FlaskClient, auth_headers: dict[str, str]
    ) -> None:
        """
        Per-config deploy should stream an error when config
        does not exist.
        """
        resp = client.post(
            "/api/digital-twin/configs/999/deploy",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        msgs = _parse_ndjson(resp.data)
        error_msgs = [m for m in msgs if m["type"] == "error"]
        assert len(error_msgs) == 1
        assert "999" in error_msgs[0]["message"]

    def test_deploy_config_streams_progress(
        self, client: FlaskClient, auth_headers: dict[str, str]
    ) -> None:
        """
        Per-config deploy should stream NDJSON when config exists.
        """
        with patch(
            "response_planner_backend.rest_api.resources"
            ".digital_twin.routes.DatabaseFacade"
        ) as db_mock, patch(
            "response_planner_backend.rest_api.resources"
            ".digital_twin.routes.DockerManager"
        ) as docker_mock:
            db_mock.get_session_token_by_token.return_value = {
                "token": "test-token",
                "username": "admin",
                "timestamp": "now",
            }
            db_mock.get_digital_twin_config_by_id.return_value = {
                "id": 1,
                "name": "Incident 1",
                "config": {"networks": [], "hosts": []},
            }
            docker_mock.deploy.return_value = iter([
                {"type": "progress",
                 "message": "Creating network"},
                {"type": "result",
                 "data": {"networks": [], "containers": []}},
            ])
            resp = client.post(
                "/api/digital-twin/configs/1/deploy",
                headers=auth_headers,
            )
        assert resp.status_code == 200
        assert resp.content_type == "application/x-ndjson"
        msgs = _parse_ndjson(resp.data)
        progress_msgs = [m for m in msgs if m["type"] == "progress"]
        assert len(progress_msgs) == 1


class TestStopConfigEndpoint:
    """Tests for POST /api/digital-twin/configs/<id>/stop."""

    def test_stop_config_requires_auth(
        self, client: FlaskClient
    ) -> None:
        """
        Per-config stop should return 401 without a valid token.
        """
        resp = client.post("/api/digital-twin/configs/1/stop")
        assert resp.status_code == 401

    def test_stop_config_not_found(
        self, client: FlaskClient, auth_headers: dict[str, str]
    ) -> None:
        """
        Per-config stop should stream an error when config
        does not exist.
        """
        resp = client.post(
            "/api/digital-twin/configs/999/stop",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        msgs = _parse_ndjson(resp.data)
        error_msgs = [m for m in msgs if m["type"] == "error"]
        assert len(error_msgs) == 1
        assert "999" in error_msgs[0]["message"]

    def test_stop_config_streams_progress(
        self, client: FlaskClient, auth_headers: dict[str, str]
    ) -> None:
        """
        Per-config stop should stream NDJSON when config exists.
        """
        with patch(
            "response_planner_backend.rest_api.resources"
            ".digital_twin.routes.DatabaseFacade"
        ) as db_mock, patch(
            "response_planner_backend.rest_api.resources"
            ".digital_twin.routes.DockerManager"
        ) as docker_mock:
            db_mock.get_session_token_by_token.return_value = {
                "token": "test-token",
                "username": "admin",
                "timestamp": "now",
            }
            db_mock.get_digital_twin_config_by_id.return_value = {
                "id": 1,
                "name": "Incident 1",
                "config": {"networks": [], "hosts": []},
            }
            docker_mock.stop.return_value = iter([
                {"type": "progress",
                 "message": "Stopping containers"},
                {"type": "result",
                 "data": {"removed": []}},
            ])
            resp = client.post(
                "/api/digital-twin/configs/1/stop",
                headers=auth_headers,
            )
        assert resp.status_code == 200
        assert resp.content_type == "application/x-ndjson"
        msgs = _parse_ndjson(resp.data)
        progress_msgs = [m for m in msgs if m["type"] == "progress"]
        assert len(progress_msgs) == 1


class TestStatusConfigEndpoint:
    """Tests for GET /api/digital-twin/configs/<id>/status."""

    def test_status_config_requires_auth(
        self, client: FlaskClient
    ) -> None:
        """
        Per-config status should return 401 without a valid token.
        """
        resp = client.get("/api/digital-twin/configs/1/status")
        assert resp.status_code == 401

    def test_status_config_not_found(
        self, client: FlaskClient, auth_headers: dict[str, str]
    ) -> None:
        """
        Per-config status should return 404 when config
        does not exist.
        """
        resp = client.get(
            "/api/digital-twin/configs/999/status",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_status_config_returns_200(
        self, client: FlaskClient, auth_headers: dict[str, str]
    ) -> None:
        """
        Per-config status should return 200 with deployment state.
        """
        with patch(
            "response_planner_backend.rest_api.resources"
            ".digital_twin.routes.DatabaseFacade"
        ) as db_mock, patch(
            "response_planner_backend.rest_api.resources"
            ".digital_twin.routes.DockerManager"
        ) as docker_mock:
            db_mock.get_session_token_by_token.return_value = {
                "token": "test-token",
                "username": "admin",
                "timestamp": "now",
            }
            db_mock.get_digital_twin_config_by_id.return_value = {
                "id": 1,
                "name": "Incident 1",
                "config": {"networks": [], "hosts": []},
            }
            docker_mock.status.return_value = {
                "deployed": True,
                "networks": [],
                "containers": [],
            }
            resp = client.get(
                "/api/digital-twin/configs/1/status",
                headers=auth_headers,
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "deployed" in data
        assert data["deployed"] is True
