"""Tests for digital twin validate endpoint."""
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


class TestValidateEndpoint:
    """Tests for POST /api/digital-twin/validate."""

    def test_validate_requires_auth(
        self, client: FlaskClient
    ) -> None:
        """
        Validate should return 401 without a valid token.
        """
        resp = client.post("/api/digital-twin/validate")
        assert resp.status_code == 401

    def test_validate_returns_not_deployed_error(
        self, client: FlaskClient, auth_headers: dict[str, str]
    ) -> None:
        """
        Validate should stream an error when DT is not deployed.
        """
        resp = client.post(
            "/api/digital-twin/validate", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.content_type == "application/x-ndjson"
        msgs = _parse_ndjson(resp.data)
        error_msgs = [m for m in msgs if m["type"] == "error"]
        assert len(error_msgs) == 1
        assert "not deployed" in error_msgs[0]["message"]

    def test_validate_streams_results_when_deployed(
        self, client: FlaskClient, auth_headers: dict[str, str]
    ) -> None:
        """
        Validate should stream progress, result, and done lines.
        """
        with patch(
            "ccs_response_planner_backend.rest_api.resources"
            ".digital_twin.routes.DockerManager"
        ) as mock:
            mock.status.return_value = {
                "deployed": True,
                "networks": ["ccs_dt_net_perimeter"],
                "containers": [
                    {"host_id": "i1_gateway", "container": "ccs_dt_i1_gateway",
                     "status": "running", "image": "ccs-dt-i1-gateway:latest"},
                ],
            }
            mock.validate.return_value = iter([
                {
                    "type": "progress",
                    "message": "[1/2] Running on i1_gateway: Check FTP...",
                },
                {
                    "type": "progress",
                    "message": "[1/2] PASS: Check FTP",
                },
                {
                    "type": "result",
                    "host": "i1_gateway",
                    "description": "Check FTP",
                    "command": "curl http://10.0.0.2:21",
                    "passed": True,
                    "output": "220",
                },
                {
                    "type": "progress",
                    "message": "[2/2] Running on i1_gateway: Check SSH...",
                },
                {
                    "type": "progress",
                    "message": "[2/2] FAIL: Check SSH",
                },
                {
                    "type": "result",
                    "host": "i1_gateway",
                    "description": "Check SSH",
                    "command": "ssh admin@10.0.0.3 echo ok",
                    "passed": False,
                    "output": "Connection refused",
                },
            ])
            resp = client.post(
                "/api/digital-twin/validate", headers=auth_headers
            )
        assert resp.status_code == 200
        assert resp.content_type == "application/x-ndjson"
        msgs = _parse_ndjson(resp.data)
        progress_msgs = [m for m in msgs if m["type"] == "progress"]
        result_msgs = [m for m in msgs if m["type"] == "result"]
        assert len(progress_msgs) == 4
        assert len(result_msgs) == 2
        assert result_msgs[0]["passed"] is True
        assert result_msgs[0]["description"] == "Check FTP"
        assert result_msgs[0]["host"] == "i1_gateway"
        assert result_msgs[1]["passed"] is False
        assert result_msgs[1]["description"] == "Check SSH"
        assert result_msgs[1]["host"] == "i1_gateway"
        done_msgs = [m for m in msgs if m["type"] == "done"]
        assert len(done_msgs) == 1

    def test_validate_returns_error_on_docker_failure(
        self, client: FlaskClient, auth_headers: dict[str, str]
    ) -> None:
        """
        Validate should stream an error when DockerManager raises.
        """
        with patch(
            "ccs_response_planner_backend.rest_api.resources"
            ".digital_twin.routes.DockerManager"
        ) as mock:
            mock.status.side_effect = RuntimeError("Docker is down")
            resp = client.post(
                "/api/digital-twin/validate", headers=auth_headers
            )
        assert resp.status_code == 200
        msgs = _parse_ndjson(resp.data)
        error_msgs = [m for m in msgs if m["type"] == "error"]
        assert len(error_msgs) == 1
        assert "Docker is down" in error_msgs[0]["message"]


class TestValidateConfigEndpoint:
    """Tests for POST /api/digital-twin/configs/<id>/validate."""

    def test_validate_config_requires_auth(
        self, client: FlaskClient
    ) -> None:
        """
        Per-config validate should return 401 without a valid token.
        """
        resp = client.post(
            "/api/digital-twin/configs/1/validate"
        )
        assert resp.status_code == 401

    def test_validate_config_not_found(
        self, client: FlaskClient, auth_headers: dict[str, str]
    ) -> None:
        """
        Per-config validate should stream an error when config
        does not exist.
        """
        resp = client.post(
            "/api/digital-twin/configs/999/validate",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        msgs = _parse_ndjson(resp.data)
        error_msgs = [m for m in msgs if m["type"] == "error"]
        assert len(error_msgs) == 1
        assert "999" in error_msgs[0]["message"]

    def test_validate_config_not_deployed(
        self, client: FlaskClient, auth_headers: dict[str, str]
    ) -> None:
        """
        Per-config validate should stream an error when not deployed.
        """
        with patch(
            "ccs_response_planner_backend.rest_api.resources"
            ".digital_twin.routes.DatabaseFacade"
        ) as db_mock, patch(
            "ccs_response_planner_backend.rest_api.resources"
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
                "config": {
                    "networks": [], "hosts": [],
                    "specification_commands": [
                        {"host": "gw", "command": "echo ok",
                         "description": "Test"},
                    ],
                },
            }
            docker_mock.status.return_value = {
                "deployed": False,
                "networks": [],
                "containers": [],
            }
            resp = client.post(
                "/api/digital-twin/configs/1/validate",
                headers=auth_headers,
            )
        assert resp.status_code == 200
        msgs = _parse_ndjson(resp.data)
        error_msgs = [m for m in msgs if m["type"] == "error"]
        assert len(error_msgs) == 1
        assert "not deployed" in error_msgs[0]["message"]

    def test_validate_config_streams_results(
        self, client: FlaskClient, auth_headers: dict[str, str]
    ) -> None:
        """
        Per-config validate should stream results when deployed.
        """
        with patch(
            "ccs_response_planner_backend.rest_api.resources"
            ".digital_twin.routes.DatabaseFacade"
        ) as db_mock, patch(
            "ccs_response_planner_backend.rest_api.resources"
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
                "config": {
                    "networks": [], "hosts": [],
                    "specification_commands": [
                        {"host": "gw", "command": "echo ok",
                         "description": "Check echo"},
                    ],
                },
            }
            docker_mock.status.return_value = {
                "deployed": True,
                "networks": ["ccs_dt_net_1_zone1"],
                "containers": [
                    {"host_id": "gw",
                     "container": "ccs_dt_gw",
                     "status": "running",
                     "image": "img:latest"},
                ],
            }
            docker_mock.validate.return_value = iter([
                {"type": "progress",
                 "message": "[1/1] Running: echo ok"},
                {"type": "result",
                 "host": "gw",
                 "description": "Check echo",
                 "command": "echo ok",
                 "passed": True,
                 "output": "ok"},
            ])
            resp = client.post(
                "/api/digital-twin/configs/1/validate",
                headers=auth_headers,
            )
        assert resp.status_code == 200
        assert resp.content_type == "application/x-ndjson"
        msgs = _parse_ndjson(resp.data)
        result_msgs = [m for m in msgs if m["type"] == "result"]
        assert len(result_msgs) == 1
        assert result_msgs[0]["passed"] is True
        done_msgs = [m for m in msgs if m["type"] == "done"]
        assert len(done_msgs) == 1
