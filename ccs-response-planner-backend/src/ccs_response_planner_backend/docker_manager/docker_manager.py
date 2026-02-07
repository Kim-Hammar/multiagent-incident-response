"""
Docker management facade for digital-twin deployment.
"""
from typing import Any, Generator

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
    ) -> Generator[dict[str, Any], None, None]:
        """
        Deploy the digital twin on multiple segmented Docker networks.

        Yields progress dicts as each step completes, enabling
        real-time streaming to clients. The final yield is a result
        dict with networks and containers lists.

        :param config: the digital twin configuration with networks/hosts
        :return: a generator of progress/result dicts
        """
        client = DockerManager._client()

        # Create networks
        networks_by_id: dict[str, Any] = {}
        network_names: list[str] = []
        for net_def in config.get("networks", []):
            net_name = f"{DOCKER.NETWORK_PREFIX}{net_def['id']}"
            try:
                net_obj = client.networks.get(net_name)
                yield {"type": "progress",
                       "message": f"Using existing network "
                                  f"{net_name}"}
            except NotFound:
                yield {"type": "progress",
                       "message": f"Creating network {net_name}"
                                  f" ({net_def['subnet']})"}
                ipam_pool = docker.types.IPAMPool(
                    subnet=net_def["subnet"],
                    gateway=net_def.get("gateway"),
                )
                ipam_config = docker.types.IPAMConfig(
                    pool_configs=[ipam_pool],
                )
                net_obj = client.networks.create(
                    net_name, driver="bridge", ipam=ipam_config,
                )
                yield {"type": "progress",
                       "message": f"Network {net_name} created"}
            networks_by_id[net_def["id"]] = net_obj
            network_names.append(net_name)

        # Create and start containers
        containers: list[dict[str, Any]] = []
        hosts = config.get("hosts", [])
        total = len(hosts)
        for idx, host in enumerate(hosts, 1):
            container_name = f"{DOCKER.CONTAINER_PREFIX}{host['id']}"
            try:
                existing = client.containers.get(container_name)
                yield {
                    "type": "progress",
                    "message":
                        f"[{idx}/{total}] Container "
                        f"{container_name} already exists "
                        f"(status: {existing.status})",
                }
                containers.append({
                    "host_id": host["id"],
                    "container": existing.name,
                    "status": existing.status,
                    "image": host["docker_image"],
                })
                continue
            except NotFound:
                pass

            yield {
                "type": "progress",
                "message": f"[{idx}/{total}] Starting "
                           f"{container_name} "
                           f"({host['docker_image']})",
            }

            create_kwargs: dict[str, Any] = {
                "name": container_name,
                "detach": True,
            }
            if not host.get("use_image_entrypoint", False):
                create_kwargs["command"] = "sleep infinity"
            if host.get("capabilities"):
                create_kwargs["cap_add"] = host["capabilities"]
            if host.get("privileged", False):
                create_kwargs["privileged"] = True
            if host.get("sysctls"):
                create_kwargs["sysctls"] = host["sysctls"]

            container = client.containers.create(
                host["docker_image"], **create_kwargs
            )

            # Connect to each assigned network with its static IP
            ip_addrs = host.get("ip_addresses") or {}
            if isinstance(ip_addrs, dict):
                for net_id, ip_addr in ip_addrs.items():
                    if net_id in networks_by_id:
                        yield {
                            "type": "progress",
                            "message":
                                f"[{idx}/{total}] Connecting "
                                f"{container_name} to {net_id} "
                                f"({ip_addr})",
                        }
                        networks_by_id[net_id].connect(
                            container, ipv4_address=ip_addr,
                        )
            container.start()

            # Disconnect from default bridge to enforce zone
            # segmentation
            try:
                client.networks.get("bridge").disconnect(
                    container
                )
            except Exception:
                pass

            yield {
                "type": "progress",
                "message": f"[{idx}/{total}] Container "
                           f"{container_name} started",
            }
            containers.append({
                "host_id": host["id"],
                "container": container.name,
                "status": container.status,
                "image": host["docker_image"],
            })

        # Apply static routes
        for host in hosts:
            routes = host.get("routes", [])
            if not routes:
                continue
            container_name = f"{DOCKER.CONTAINER_PREFIX}{host['id']}"
            for route in routes:
                cmd = (f"ip route add {route['destination']} "
                       f"via {route['via']}")
                yield {
                    "type": "progress",
                    "message":
                        f"Adding route on {host['id']}: "
                        f"{route['destination']} "
                        f"via {route['via']}",
                }
                try:
                    exec_id = client.api.exec_create(
                        container_name, ["/bin/sh", "-c", cmd],
                    )["Id"]
                    client.api.exec_start(exec_id)
                except Exception:
                    pass

        yield {"type": "progress",
               "message": "Deployment complete"}
        yield {
            "type": "result",
            "data": {
                "networks": network_names,
                "containers": containers,
            },
        }

    @staticmethod
    def stop() -> Generator[dict[str, Any], None, None]:
        """
        Stop and remove all digital twin containers and networks.

        Yields progress dicts as each step completes. The final
        yield is a result dict with the removed container names.

        :return: a generator of progress/result dicts
        """
        client = DockerManager._client()
        removed: list[str] = []

        dt_containers = [
            c for c in client.containers.list(all=True)
            if c.name.startswith(DOCKER.CONTAINER_PREFIX)
        ]
        total = len(dt_containers)
        for idx, container in enumerate(dt_containers, 1):
            yield {
                "type": "progress",
                "message": f"[{idx}/{total}] Removing "
                           f"{container.name}",
            }
            container.remove(force=True)
            removed.append(container.name)
            yield {
                "type": "progress",
                "message": f"[{idx}/{total}] Removed "
                           f"{container.name}",
            }

        for network in client.networks.list():
            if network.name.startswith(DOCKER.NETWORK_PREFIX):
                yield {
                    "type": "progress",
                    "message": f"Removing network "
                               f"{network.name}",
                }
                network.remove()
                yield {
                    "type": "progress",
                    "message": f"Network {network.name} removed",
                }

        yield {"type": "progress",
               "message": "Shutdown complete"}
        yield {
            "type": "result",
            "data": {"removed": removed},
        }

    @staticmethod
    def status() -> dict[str, Any]:
        """
        Get the status of digital twin containers and networks.

        :return: a dict with deployed flag, networks list, and container list
        """
        client = DockerManager._client()

        network_names = [
            n.name for n in client.networks.list()
            if n.name.startswith(DOCKER.NETWORK_PREFIX)
        ]

        containers = []
        for container in client.containers.list(all=True):
            if container.name.startswith(DOCKER.CONTAINER_PREFIX):
                host_id = container.name[len(DOCKER.CONTAINER_PREFIX):]
                try:
                    image_name = (container.image.tags
                                  or ["unknown"])[0]
                except Exception:
                    image_name = "unknown"
                containers.append({
                    "host_id": host_id,
                    "container": container.name,
                    "status": container.status,
                    "image": image_name,
                })

        return {
            "deployed": len(containers) > 0,
            "networks": network_names,
            "containers": containers,
        }

    @staticmethod
    def validate(
        specification_commands: list[dict[str, str]],
    ) -> Generator[dict[str, Any], None, None]:
        """
        Run specification commands against deployed containers.

        Yields progress and result dicts as each command completes,
        enabling real-time streaming to clients.

        :param specification_commands: list of dicts with host/command/description
        :return: a generator of progress/result dicts
        """
        client = DockerManager._client()
        total = len(specification_commands)
        for idx, spec in enumerate(specification_commands, 1):
            host_id = spec.get("host", "gateway")
            container_name = f"{DOCKER.CONTAINER_PREFIX}{host_id}"
            cmd = spec["command"]
            description = spec["description"]
            yield {
                "type": "progress",
                "message": (f"[{idx}/{total}] Running on "
                            f"{host_id}: {description}..."),
            }
            exec_id = client.api.exec_create(
                container_name,
                ["/bin/sh", "-c", cmd],
                stdin=False,
                tty=False,
            )["Id"]
            output_bytes = client.api.exec_start(exec_id)
            exit_code = client.api.exec_inspect(exec_id)["ExitCode"]
            passed = exit_code == 0
            output = output_bytes.decode(
                "utf-8", errors="replace"
            ).strip()
            status_label = "PASS" if passed else "FAIL"
            yield {
                "type": "progress",
                "message": (f"[{idx}/{total}] "
                            f"{status_label}: {description}"),
            }
            yield {
                "type": "result",
                "host": host_id,
                "description": description,
                "command": cmd,
                "passed": passed,
                "output": output,
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
