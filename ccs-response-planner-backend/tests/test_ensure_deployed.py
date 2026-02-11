"""Tests for auto-deploy logic in DockerManager and agent tools."""
from unittest.mock import MagicMock, patch

from ccs_response_planner_backend.docker_manager.docker_manager import (
    DockerManager,
)

DOCKER_MODULE = (
    "ccs_response_planner_backend"
    ".docker_manager.docker_manager.docker"
)
SHARED_TOOLS_MODULE = (
    "ccs_response_planner_backend.agents.shared_tools"
)
PENTEST_MODULE = (
    "ccs_response_planner_backend"
    ".agents.penetration_test_agent.tools"
)


class TestEnsureDeployed:
    """Tests for DockerManager.ensure_deployed."""

    @patch(DOCKER_MODULE)
    def test_noop_when_already_deployed(
        self, mock_docker: MagicMock,
    ) -> None:
        """
        ensure_deployed should return immediately when the DT is
        already deployed.
        """
        client = MagicMock()
        mock_docker.from_env.return_value = client
        c1 = MagicMock()
        c1.name = "ccs_dt_server_1"
        c1.status = "running"
        c1.image.tags = ["ubuntu:22.04"]
        client.containers.list.return_value = [c1]
        n1 = MagicMock()
        n1.name = "ccs_dt_net_zone1"
        client.networks.list.return_value = [n1]

        with patch.object(
            DockerManager, "deploy"
        ) as mock_deploy:
            DockerManager.ensure_deployed()
            mock_deploy.assert_not_called()

    @patch(
        "ccs_response_planner_backend"
        ".db.database_facade.DatabaseFacade"
        ".get_digital_twin_config",
        return_value=None,
    )
    @patch(DOCKER_MODULE)
    def test_deploys_when_not_deployed(
        self,
        mock_docker: MagicMock,
        mock_get_config: MagicMock,
    ) -> None:
        """
        ensure_deployed should call deploy when no containers exist.
        """
        client = MagicMock()
        mock_docker.from_env.return_value = client
        client.containers.list.return_value = []
        client.networks.list.return_value = []

        with patch.object(
            DockerManager, "deploy",
            return_value=iter([
                {"type": "progress",
                 "message": "Deploying..."},
                {"type": "result",
                 "data": {"networks": [],
                          "containers": []}},
            ]),
        ) as mock_deploy:
            DockerManager.ensure_deployed()
            mock_deploy.assert_called_once()

    @patch(
        "ccs_response_planner_backend"
        ".db.database_facade.DatabaseFacade"
        ".get_digital_twin_config",
    )
    @patch(DOCKER_MODULE)
    def test_uses_saved_config_when_available(
        self,
        mock_docker: MagicMock,
        mock_get_config: MagicMock,
    ) -> None:
        """
        ensure_deployed should use saved DB config over default.
        """
        client = MagicMock()
        mock_docker.from_env.return_value = client
        client.containers.list.return_value = []
        client.networks.list.return_value = []
        saved_config = {"networks": [], "hosts": []}
        mock_get_config.return_value = saved_config

        with patch.object(
            DockerManager, "deploy",
            return_value=iter([
                {"type": "result",
                 "data": {"networks": [],
                          "containers": []}},
            ]),
        ) as mock_deploy:
            DockerManager.ensure_deployed()
            mock_deploy.assert_called_once_with(saved_config)


class TestDtExecAutoDeploy:
    """Tests for dt_exec auto-deploy on NotFound."""

    @patch(f"{SHARED_TOOLS_MODULE}.DockerManager")
    @patch(f"{SHARED_TOOLS_MODULE}.docker")
    def test_auto_deploys_on_not_found(
        self,
        mock_docker: MagicMock,
        mock_manager: MagicMock,
    ) -> None:
        """
        dt_exec should auto-deploy and retry when the container
        is not found.
        """
        from ccs_response_planner_backend.agents.shared_tools \
            import dt_exec

        client = MagicMock()
        mock_docker.from_env.return_value = client
        from docker.errors import NotFound
        mock_docker.errors.NotFound = NotFound

        ct = MagicMock()
        ct.id = "abc123"
        client.containers.get.side_effect = [
            NotFound("not found"),
            ct,
        ]
        client.api.exec_create.return_value = {
            "Id": "exec1"
        }
        client.api.exec_start.return_value = b"hello"
        client.api.exec_inspect.return_value = {
            "ExitCode": 0
        }

        result = dt_exec("gateway", "echo hello")

        mock_manager.ensure_deployed.assert_called_once()
        assert result["exit_code"] == 0
        assert result["output"] == "hello"

    @patch(f"{SHARED_TOOLS_MODULE}.DockerManager")
    @patch(f"{SHARED_TOOLS_MODULE}.docker")
    def test_returns_error_on_deploy_failure(
        self,
        mock_docker: MagicMock,
        mock_manager: MagicMock,
    ) -> None:
        """
        dt_exec should return an error dict when auto-deploy fails.
        """
        from ccs_response_planner_backend.agents.shared_tools \
            import dt_exec

        client = MagicMock()
        mock_docker.from_env.return_value = client
        from docker.errors import NotFound
        mock_docker.errors.NotFound = NotFound
        client.containers.get.side_effect = NotFound(
            "not found"
        )
        mock_manager.ensure_deployed.side_effect = (
            RuntimeError("deploy boom")
        )

        result = dt_exec("gateway", "echo hi")
        assert "error" in result
        assert "auto-deploy failed" in result["error"]


class TestPentestExecAutoDeploy:
    """Tests for pentest_exec auto-deploy on NotFound."""

    @patch(f"{PENTEST_MODULE}.DockerManager")
    @patch(f"{PENTEST_MODULE}.docker")
    def test_auto_deploys_on_not_found(
        self,
        mock_docker: MagicMock,
        mock_manager: MagicMock,
    ) -> None:
        """
        pentest_exec should auto-deploy and retry when the
        attacker container is not found.
        """
        from ccs_response_planner_backend.agents \
            .penetration_test_agent.tools import pentest_exec

        client = MagicMock()
        mock_docker.from_env.return_value = client
        from docker.errors import NotFound
        mock_docker.errors.NotFound = NotFound

        ct = MagicMock()
        ct.id = "att123"
        client.containers.get.side_effect = [
            NotFound("not found"),
            ct,
        ]
        client.api.exec_create.return_value = {
            "Id": "exec1"
        }
        client.api.exec_start.return_value = b"scan output"
        client.api.exec_inspect.return_value = {
            "ExitCode": 0
        }

        result = pentest_exec("nmap -sV 10.0.2.1")

        mock_manager.ensure_deployed.assert_called_once()
        assert result["exit_code"] == 0
        assert result["output"] == "scan output"

    @patch(f"{PENTEST_MODULE}.DockerManager")
    @patch(f"{PENTEST_MODULE}.docker")
    def test_returns_error_on_deploy_failure(
        self,
        mock_docker: MagicMock,
        mock_manager: MagicMock,
    ) -> None:
        """
        pentest_exec should return error when auto-deploy fails.
        """
        from ccs_response_planner_backend.agents \
            .penetration_test_agent.tools import pentest_exec

        client = MagicMock()
        mock_docker.from_env.return_value = client
        from docker.errors import NotFound
        mock_docker.errors.NotFound = NotFound
        client.containers.get.side_effect = NotFound(
            "not found"
        )
        mock_manager.ensure_deployed.side_effect = (
            RuntimeError("deploy boom")
        )

        result = pentest_exec("nmap 10.0.2.1")
        assert "error" in result
        assert "auto-deploy failed" in result["error"]
