"""Tests for DockerManager facade."""
from unittest.mock import MagicMock, patch

from ccs_response_planner_backend.docker_manager.docker_manager import (
    DockerManager,
)


DOCKER_MODULE = (
    "ccs_response_planner_backend.docker_manager.docker_manager.docker"
)


def _make_config(
    hosts: list[dict] | None = None,
    networks: list[dict] | None = None,
) -> dict:
    """
    Build a minimal deploy config for tests.

    :param hosts: list of host dicts
    :param networks: list of network dicts
    :return: a config dict
    """
    if networks is None:
        networks = [
            {"id": "zone1", "subnet": "10.0.2.0/24",
             "gateway": "10.0.2.100"},
        ]
    if hosts is None:
        hosts = [
            {
                "id": "server_1",
                "docker_image": "ubuntu:22.04",
                "ip_addresses": {"zone1": "10.0.2.1"},
            }
        ]
    return {"networks": networks, "hosts": hosts}


class TestDeploy:
    """Tests for DockerManager.deploy."""

    @patch(DOCKER_MODULE)
    def test_deploy_creates_networks_and_containers(
        self, mock_docker: MagicMock
    ) -> None:
        """
        Deploy should create networks and start containers.
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
        client.containers.create.return_value = container

        result = DockerManager.deploy(_make_config())
        assert "networks" in result
        assert len(result["networks"]) == 1
        assert result["networks"][0] == "ccs_dt_net_zone1"
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
        client.containers.create.return_value = container

        config = _make_config(
            hosts=[{
                "id": "gw",
                "docker_image": "alpine:3",
                "ip_addresses": {"zone1": "10.0.2.254"},
            }],
        )
        result = DockerManager.deploy(config)
        client.networks.create.assert_not_called()
        assert "ccs_dt_net_zone1" in result["networks"]

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

        result = DockerManager.deploy(_make_config())
        client.containers.create.assert_not_called()
        assert result["containers"][0]["status"] == "running"

    @patch(DOCKER_MODULE)
    def test_deploy_uses_image_entrypoint(
        self, mock_docker: MagicMock
    ) -> None:
        """
        Deploy should not pass command when use_image_entrypoint is True.
        """
        client = MagicMock()
        mock_docker.from_env.return_value = client
        network = MagicMock()
        client.networks.get.return_value = network
        from docker.errors import NotFound
        client.containers.get.side_effect = NotFound("not found")
        container = MagicMock()
        container.name = "ccs_dt_server_1"
        container.status = "running"
        client.containers.create.return_value = container

        config = _make_config(
            hosts=[{
                "id": "server_1",
                "docker_image": "ccs-dt-server1:latest",
                "ip_addresses": {"zone1": "10.0.2.1"},
                "use_image_entrypoint": True,
            }],
        )
        DockerManager.deploy(config)
        call_kwargs = client.containers.create.call_args
        assert "command" not in call_kwargs.kwargs

    @patch(DOCKER_MODULE)
    def test_deploy_passes_capabilities(
        self, mock_docker: MagicMock
    ) -> None:
        """
        Deploy should pass cap_add when capabilities are specified.
        """
        client = MagicMock()
        mock_docker.from_env.return_value = client
        network = MagicMock()
        client.networks.get.return_value = network
        from docker.errors import NotFound
        client.containers.get.side_effect = NotFound("not found")
        container = MagicMock()
        container.name = "ccs_dt_gateway"
        container.status = "running"
        client.containers.create.return_value = container

        config = _make_config(
            networks=[
                {"id": "perimeter", "subnet": "10.0.1.0/24",
                 "gateway": "10.0.1.100"},
            ],
            hosts=[{
                "id": "gateway",
                "docker_image": "ccs-dt-gateway:latest",
                "ip_addresses": {"perimeter": "10.0.1.254"},
                "use_image_entrypoint": True,
                "capabilities": ["NET_ADMIN", "NET_RAW"],
            }],
        )
        DockerManager.deploy(config)
        call_kwargs = client.containers.create.call_args
        assert call_kwargs.kwargs["cap_add"] == ["NET_ADMIN", "NET_RAW"]

    @patch(DOCKER_MODULE)
    def test_deploy_backward_compatible_no_entrypoint(
        self, mock_docker: MagicMock
    ) -> None:
        """
        Deploy should still pass sleep infinity when use_image_entrypoint
        is absent.
        """
        client = MagicMock()
        mock_docker.from_env.return_value = client
        network = MagicMock()
        client.networks.get.return_value = network
        from docker.errors import NotFound
        client.containers.get.side_effect = NotFound("not found")
        container = MagicMock()
        container.name = "ccs_dt_server_1"
        container.status = "running"
        client.containers.create.return_value = container

        DockerManager.deploy(_make_config())
        call_kwargs = client.containers.create.call_args
        assert call_kwargs.kwargs["command"] == "sleep infinity"

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
        client.containers.create.return_value = container

        messages: list[str] = []
        config = _make_config(
            hosts=[{
                "id": "s1",
                "docker_image": "alpine:3",
                "ip_addresses": {"zone1": "10.0.2.1"},
            }],
        )
        DockerManager.deploy(config, on_progress=messages.append)
        assert any("Creating network" in m for m in messages)
        assert any("Starting" in m for m in messages)
        assert any("Deployment complete" in m for m in messages)

    @patch(DOCKER_MODULE)
    def test_deploy_connects_multi_network_host(
        self, mock_docker: MagicMock
    ) -> None:
        """
        Deploy should connect a host to multiple networks.
        """
        client = MagicMock()
        mock_docker.from_env.return_value = client
        net1 = MagicMock()
        net2 = MagicMock()

        def get_net(name: str) -> MagicMock:
            if name == "ccs_dt_net_zone1":
                return net1
            return net2

        client.networks.get.side_effect = get_net
        from docker.errors import NotFound
        client.containers.get.side_effect = NotFound("not found")
        container = MagicMock()
        container.name = "ccs_dt_ids"
        container.status = "running"
        client.containers.create.return_value = container

        config = _make_config(
            networks=[
                {"id": "zone1", "subnet": "10.0.2.0/24",
                 "gateway": "10.0.2.100"},
                {"id": "zone2", "subnet": "10.0.3.0/24",
                 "gateway": "10.0.3.100"},
            ],
            hosts=[{
                "id": "ids",
                "docker_image": "ccs-dt-ids:latest",
                "ip_addresses": {
                    "zone1": "10.0.2.252",
                    "zone2": "10.0.3.252",
                },
                "use_image_entrypoint": True,
            }],
        )
        DockerManager.deploy(config)
        net1.connect.assert_called_once()
        net2.connect.assert_called_once()


class TestStop:
    """Tests for DockerManager.stop."""

    @patch(DOCKER_MODULE)
    def test_stop_removes_containers_and_networks(
        self, mock_docker: MagicMock
    ) -> None:
        """
        Stop should remove all ccs_dt_ containers and networks.
        """
        client = MagicMock()
        mock_docker.from_env.return_value = client
        c1 = MagicMock()
        c1.name = "ccs_dt_server_1"
        c2 = MagicMock()
        c2.name = "ccs_dt_server_2"
        client.containers.list.return_value = [c1, c2]
        n1 = MagicMock()
        n1.name = "ccs_dt_net_zone1"
        n2 = MagicMock()
        n2.name = "ccs_dt_net_zone2"
        other = MagicMock()
        other.name = "bridge"
        client.networks.list.return_value = [n1, n2, other]

        result = DockerManager.stop()
        assert len(result["removed"]) == 2
        c1.remove.assert_called_once_with(force=True)
        c2.remove.assert_called_once_with(force=True)
        n1.remove.assert_called_once()
        n2.remove.assert_called_once()

    @patch(DOCKER_MODULE)
    def test_stop_handles_no_networks(
        self, mock_docker: MagicMock
    ) -> None:
        """
        Stop should handle the case where no DT networks exist.
        """
        client = MagicMock()
        mock_docker.from_env.return_value = client
        client.containers.list.return_value = []
        client.networks.list.return_value = []

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
        n1 = MagicMock()
        n1.name = "ccs_dt_net_zone1"
        client.networks.list.return_value = [n1]

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
        n1 = MagicMock()
        n1.name = "ccs_dt_net_zone1"
        client.networks.list.return_value = [n1]
        c1 = MagicMock()
        c1.name = "ccs_dt_server_1"
        c1.status = "running"
        c1.image.tags = ["ubuntu:22.04"]
        client.containers.list.return_value = [c1]

        result = DockerManager.status()
        assert result["deployed"] is True
        assert len(result["containers"]) == 1
        assert result["networks"] == ["ccs_dt_net_zone1"]

    @patch(DOCKER_MODULE)
    def test_status_returns_deployed_false(
        self, mock_docker: MagicMock
    ) -> None:
        """
        Status should return deployed=False when no containers exist.
        """
        client = MagicMock()
        mock_docker.from_env.return_value = client
        client.networks.list.return_value = []
        client.containers.list.return_value = []

        result = DockerManager.status()
        assert result["deployed"] is False
        assert result["containers"] == []
        assert result["networks"] == []


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
