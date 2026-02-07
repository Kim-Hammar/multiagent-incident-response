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
        resp = client.post("/api/digital-twin/deploy", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.content_type == "application/x-ndjson"
        msgs = _parse_ndjson(resp.data)
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
            "ccs_response_planner_backend.rest_api.resources"
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
        resp = client.post("/api/digital-twin/stop", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.content_type == "application/x-ndjson"
        msgs = _parse_ndjson(resp.data)
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
            "ccs_response_planner_backend.rest_api.resources"
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
            "ccs_response_planner_backend.rest_api.resources"
            ".digital_twin.routes.DockerManager"
        ) as mock:
            mock.status.side_effect = RuntimeError("Docker is down")
            resp = client.get(
                "/api/digital-twin/status", headers=auth_headers
            )
        assert resp.status_code == 500
        assert "error" in resp.get_json()
