"""
Docker management facade for digital-twin deployment.
"""
from typing import Any, Callable, Optional

import docker
from docker.errors import NotFound

from ccs_response_planner_backend.constants.constants import DOCKER


class DockerManager:
    """
    Static-method facade for Docker operations on the digital twin.
    """

    @staticmethod
    def _client() -> docker.DockerClient:
        """
        Create a Docker client from the environment.

        :return: a Docker client instance
        """
        return docker.from_env()

    @staticmethod
    def deploy(
        config: dict[str, Any],
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> dict[str, Any]:
        """
        Deploy the digital twin as Docker containers on a bridge network.

        Creates the network if it does not exist, pulls images, and starts
        containers with assigned IPs. Idempotent: skips existing containers.

        :param config: the digital twin configuration with hosts list
        :param on_progress: optional callback invoked with status messages
        :return: a dict with network name and list of created containers
        """
        def emit(msg: str) -> None:
            if on_progress:
                on_progress(msg)

        client = DockerManager._client()

        try:
            network = client.networks.get(DOCKER.NETWORK_NAME)
            emit(f"Using existing network {DOCKER.NETWORK_NAME}")
        except NotFound:
            emit(f"Creating network {DOCKER.NETWORK_NAME} "
                 f"({DOCKER.SUBNET})")
            ipam_pool = docker.types.IPAMPool(
                subnet=DOCKER.SUBNET,
                gateway=DOCKER.GATEWAY,
            )
            ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
            network = client.networks.create(
                DOCKER.NETWORK_NAME,
                driver="bridge",
                ipam=ipam_config,
            )
            emit(f"Network {DOCKER.NETWORK_NAME} created")

        containers = []
        hosts = config.get("hosts", [])
        total = len(hosts)
        for idx, host in enumerate(hosts, 1):
            container_name = f"{DOCKER.CONTAINER_PREFIX}{host['id']}"
            try:
                existing = client.containers.get(container_name)
                emit(f"[{idx}/{total}] Container {container_name} "
                     f"already exists (status: {existing.status})")
                containers.append({
                    "host_id": host["id"],
                    "container": existing.name,
                    "status": existing.status,
                    "image": host["docker_image"],
                })
                continue
            except NotFound:
                pass

            ip_addr = (host.get("ip_addresses") or [None])[0]
            emit(f"[{idx}/{total}] Starting {container_name} "
                 f"({host['docker_image']})")

            container = client.containers.run(
                host["docker_image"],
                command="sleep infinity",
                name=container_name,
                network=DOCKER.NETWORK_NAME,
                detach=True,
            )

            if ip_addr:
                emit(f"[{idx}/{total}] Assigning IP {ip_addr} "
                     f"to {container_name}")
                try:
                    network.disconnect(container)
                except Exception:
                    pass
                network.connect(container, ipv4_address=ip_addr)

            emit(f"[{idx}/{total}] Container {container_name} started")
            containers.append({
                "host_id": host["id"],
                "container": container.name,
                "status": container.status,
                "image": host["docker_image"],
            })

        emit("Deployment complete")
        return {"network": DOCKER.NETWORK_NAME, "containers": containers}

    @staticmethod
    def stop(
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> dict[str, Any]:
        """
        Stop and remove all digital twin containers and the network.

        :param on_progress: optional callback invoked with status messages
        :return: a dict with the list of removed container names
        """
        def emit(msg: str) -> None:
            if on_progress:
                on_progress(msg)

        client = DockerManager._client()
        removed = []

        dt_containers = [
            c for c in client.containers.list(all=True)
            if c.name.startswith(DOCKER.CONTAINER_PREFIX)
        ]
        total = len(dt_containers)
        for idx, container in enumerate(dt_containers, 1):
            emit(f"[{idx}/{total}] Removing {container.name}")
            container.remove(force=True)
            removed.append(container.name)
            emit(f"[{idx}/{total}] Removed {container.name}")

        try:
            network = client.networks.get(DOCKER.NETWORK_NAME)
            emit(f"Removing network {DOCKER.NETWORK_NAME}")
            network.remove()
            emit(f"Network {DOCKER.NETWORK_NAME} removed")
        except NotFound:
            pass

        emit("Shutdown complete")
        return {"removed": removed}

    @staticmethod
    def status() -> dict[str, Any]:
        """
        Get the status of digital twin containers and network.

        :return: a dict with deployed flag, network info, and container list
        """
        client = DockerManager._client()

        network_info = None
        try:
            network = client.networks.get(DOCKER.NETWORK_NAME)
            network_info = network.name
        except NotFound:
            pass

        containers = []
        for container in client.containers.list(all=True):
            if container.name.startswith(DOCKER.CONTAINER_PREFIX):
                host_id = container.name[len(DOCKER.CONTAINER_PREFIX):]
                containers.append({
                    "host_id": host_id,
                    "container": container.name,
                    "status": container.status,
                    "image": (container.image.tags or ["unknown"])[0],
                })

        return {
            "deployed": len(containers) > 0,
            "network": network_info,
            "containers": containers,
        }

    @staticmethod
    def exec_create(
        container_name: str,
    ) -> tuple[Any, str]:
        """
        Create an exec instance with TTY and stdin on a container.

        The Docker SDK returns a read-only ``socket.SocketIO`` wrapper,
        so we extract the underlying ``socket.socket`` for bidirectional
        I/O via ``recv`` / ``sendall``.

        :param container_name: the name of the Docker container
        :return: a tuple of (raw socket, exec_id)
        """
        client = DockerManager._client()
        exec_id = client.api.exec_create(
            container_name,
            "/bin/sh",
            stdin=True,
            tty=True,
            stdout=True,
            stderr=True,
        )["Id"]
        sock = client.api.exec_start(exec_id, socket=True, tty=True)
        # sock is a read-only SocketIO; unwrap to the raw socket
        raw = getattr(sock, "_sock", sock)
        return raw, exec_id

    @staticmethod
    def exec_resize(exec_id: str, rows: int, cols: int) -> None:
        """
        Resize the TTY session of an exec instance.

        :param exec_id: the exec instance ID
        :param rows: number of rows
        :param cols: number of columns
        """
        client = DockerManager._client()
        client.api.exec_resize(exec_id, height=rows, width=cols)
