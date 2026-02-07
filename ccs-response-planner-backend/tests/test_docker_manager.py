"""Tests for DockerManager facade."""
from unittest.mock import MagicMock, patch

from ccs_response_planner_backend.docker_manager.docker_manager import (
    DockerManager,
)


DOCKER_MODULE = (
    "ccs_response_planner_backend.docker_manager.docker_manager.docker"
)


class TestDeploy:
    """Tests for DockerManager.deploy."""

    @patch(DOCKER_MODULE)
    def test_deploy_creates_network_and_containers(
        self, mock_docker: MagicMock
    ) -> None:
        """
        Deploy should create a network and start containers.
        """
        client = MagicMock()
        mock_docker.from_env.return_value = client
        from docker.errors import NotFound
        client.networks.get.side_effect = NotFound("not found")
        network = MagicMock()
        client.networks.create.return_value = network
        container = MagicMock()
        container.name = "ccs_dt_server_1"
        container.status = "running"
        client.containers.get.side_effect = NotFound("not found")
        client.containers.run.return_value = container
        client.api.create_networking_config.return_value = {}
        client.api.create_endpoint_config.return_value = {}

        config = {
            "hosts": [
                {
                    "id": "server_1",
                    "docker_image": "ubuntu:22.04",
                    "ip_addresses": ["10.0.0.1"],
                }
            ]
        }
        result = DockerManager.deploy(config)
        assert result["network"] == "ccs_dt_network"
        assert len(result["containers"]) == 1
        assert result["containers"][0]["host_id"] == "server_1"

    @patch(DOCKER_MODULE)
    def test_deploy_reuses_existing_network(
        self, mock_docker: MagicMock
    ) -> None:
        """
        Deploy should reuse an existing network instead of creating one.
        """
        client = MagicMock()
        mock_docker.from_env.return_value = client
        network = MagicMock()
        client.networks.get.return_value = network
        from docker.errors import NotFound
        client.containers.get.side_effect = NotFound("not found")
        container = MagicMock()
        container.name = "ccs_dt_gw"
        container.status = "running"
        client.containers.run.return_value = container

        config = {
            "hosts": [
                {
                    "id": "gw",
                    "docker_image": "alpine:3",
                    "ip_addresses": ["10.0.0.254"],
                }
            ]
        }
        result = DockerManager.deploy(config)
        client.networks.create.assert_not_called()
        assert result["network"] == "ccs_dt_network"

    @patch(DOCKER_MODULE)
    def test_deploy_skips_existing_container(
        self, mock_docker: MagicMock
    ) -> None:
        """
        Deploy should skip containers that already exist.
        """
        client = MagicMock()
        mock_docker.from_env.return_value = client
        network = MagicMock()
        client.networks.get.return_value = network
        existing = MagicMock()
        existing.name = "ccs_dt_server_1"
        existing.status = "running"
        client.containers.get.return_value = existing

        config = {
            "hosts": [
                {
                    "id": "server_1",
                    "docker_image": "ubuntu:22.04",
                    "ip_addresses": ["10.0.0.1"],
                }
            ]
        }
        result = DockerManager.deploy(config)
        client.containers.run.assert_not_called()
        assert result["containers"][0]["status"] == "running"

    @patch(DOCKER_MODULE)
    def test_deploy_emits_progress_messages(
        self, mock_docker: MagicMock
    ) -> None:
        """
        Deploy should call on_progress with step messages.
        """
        client = MagicMock()
        mock_docker.from_env.return_value = client
        from docker.errors import NotFound
        client.networks.get.side_effect = NotFound("not found")
        network = MagicMock()
        client.networks.create.return_value = network
        container = MagicMock()
        container.name = "ccs_dt_s1"
        container.status = "running"
        client.containers.get.side_effect = NotFound("not found")
        client.containers.run.return_value = container

        messages: list[str] = []
        config = {
            "hosts": [
                {
                    "id": "s1",
                    "docker_image": "alpine:3",
                    "ip_addresses": ["10.0.0.1"],
                }
            ]
        }
        DockerManager.deploy(config, on_progress=messages.append)
        assert any("Creating network" in m for m in messages)
        assert any("Starting" in m for m in messages)
        assert any("Deployment complete" in m for m in messages)


class TestStop:
    """Tests for DockerManager.stop."""

    @patch(DOCKER_MODULE)
    def test_stop_removes_containers_and_network(
        self, mock_docker: MagicMock
    ) -> None:
        """
        Stop should remove all ccs_dt_ containers and the network.
        """
        client = MagicMock()
        mock_docker.from_env.return_value = client
        c1 = MagicMock()
        c1.name = "ccs_dt_server_1"
        c2 = MagicMock()
        c2.name = "ccs_dt_server_2"
        client.containers.list.return_value = [c1, c2]
        network = MagicMock()
        client.networks.get.return_value = network

        result = DockerManager.stop()
        assert len(result["removed"]) == 2
        c1.remove.assert_called_once_with(force=True)
        c2.remove.assert_called_once_with(force=True)
        network.remove.assert_called_once()

    @patch(DOCKER_MODULE)
    def test_stop_handles_missing_network(
        self, mock_docker: MagicMock
    ) -> None:
        """
        Stop should handle the case where the network does not exist.
        """
        client = MagicMock()
        mock_docker.from_env.return_value = client
        client.containers.list.return_value = []
        from docker.errors import NotFound
        client.networks.get.side_effect = NotFound("not found")

        result = DockerManager.stop()
        assert result["removed"] == []

    @patch(DOCKER_MODULE)
    def test_stop_emits_progress_messages(
        self, mock_docker: MagicMock
    ) -> None:
        """
        Stop should call on_progress with step messages.
        """
        client = MagicMock()
        mock_docker.from_env.return_value = client
        c1 = MagicMock()
        c1.name = "ccs_dt_server_1"
        client.containers.list.return_value = [c1]
        network = MagicMock()
        client.networks.get.return_value = network

        messages: list[str] = []
        DockerManager.stop(on_progress=messages.append)
        assert any("Removing ccs_dt_server_1" in m for m in messages)
        assert any("Removed ccs_dt_server_1" in m for m in messages)
        assert any("Shutdown complete" in m for m in messages)


class TestStatus:
    """Tests for DockerManager.status."""

    @patch(DOCKER_MODULE)
    def test_status_returns_deployed_true(
        self, mock_docker: MagicMock
    ) -> None:
        """
        Status should return deployed=True when containers exist.
        """
        client = MagicMock()
        mock_docker.from_env.return_value = client
        network = MagicMock()
        network.name = "ccs_dt_network"
        client.networks.get.return_value = network
        c1 = MagicMock()
        c1.name = "ccs_dt_server_1"
        c1.status = "running"
        c1.image.tags = ["ubuntu:22.04"]
        client.containers.list.return_value = [c1]

        result = DockerManager.status()
        assert result["deployed"] is True
        assert len(result["containers"]) == 1

    @patch(DOCKER_MODULE)
    def test_status_returns_deployed_false(
        self, mock_docker: MagicMock
    ) -> None:
        """
        Status should return deployed=False when no containers exist.
        """
        client = MagicMock()
        mock_docker.from_env.return_value = client
        from docker.errors import NotFound
        client.networks.get.side_effect = NotFound("not found")
        client.containers.list.return_value = []

        result = DockerManager.status()
        assert result["deployed"] is False
        assert result["containers"] == []


class TestExec:
    """Tests for DockerManager.exec_create and exec_resize."""

    @patch(DOCKER_MODULE)
    def test_exec_create_returns_raw_socket_and_id(
        self, mock_docker: MagicMock
    ) -> None:
        """
        exec_create should unwrap the SocketIO and return the raw socket.
        """
        client = MagicMock()
        mock_docker.from_env.return_value = client
        client.api.exec_create.return_value = {"Id": "exec123"}
        raw = MagicMock()
        wrapper = MagicMock()
        wrapper._sock = raw
        client.api.exec_start.return_value = wrapper

        result_sock, result_id = DockerManager.exec_create("ccs_dt_s1")
        assert result_sock is raw
        assert result_id == "exec123"

    @patch(DOCKER_MODULE)
    def test_exec_resize_calls_api(self, mock_docker: MagicMock) -> None:
        """
        exec_resize should call the Docker API resize method.
        """
        client = MagicMock()
        mock_docker.from_env.return_value = client

        DockerManager.exec_resize("exec123", 24, 80)
        client.api.exec_resize.assert_called_once_with(
            "exec123", height=24, width=80
        )
