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
                "network": "ccs_dt_network",
                "containers": [
                    {"host_id": "gateway", "container": "ccs_dt_gateway",
                     "status": "running", "image": "ccs-dt-gateway:latest"},
                ],
            }
            mock.validate.return_value = [
                {
                    "host": "gateway",
                    "description": "Check FTP",
                    "command": "curl http://10.0.0.2:21",
                    "passed": True,
                    "output": "220",
                },
                {
                    "host": "gateway",
                    "description": "Check SSH",
                    "command": "ssh admin@10.0.0.3 echo ok",
                    "passed": False,
                    "output": "Connection refused",
                },
            ]
            resp = client.post(
                "/api/digital-twin/validate", headers=auth_headers
            )
        assert resp.status_code == 200
        assert resp.content_type == "application/x-ndjson"
        msgs = _parse_ndjson(resp.data)
        result_msgs = [m for m in msgs if m["type"] == "result"]
        assert len(result_msgs) == 2
        assert result_msgs[0]["passed"] is True
        assert result_msgs[0]["description"] == "Check FTP"
        assert result_msgs[0]["host"] == "gateway"
        assert result_msgs[1]["passed"] is False
        assert result_msgs[1]["description"] == "Check SSH"
        assert result_msgs[1]["host"] == "gateway"
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
