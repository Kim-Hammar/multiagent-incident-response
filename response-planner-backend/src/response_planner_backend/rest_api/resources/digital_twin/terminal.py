"""
WebSocket terminal handler for interactive container sessions.
"""
import json
import socket
import threading
from typing import Any

from flask import request
from flask_sock import Sock

from response_planner_backend.constants.constants import DOCKER
from response_planner_backend.db.database_facade import DatabaseFacade
from response_planner_backend.docker_manager.docker_manager import (
    DockerManager,
)


def register_terminal_ws(sock: Sock) -> None:
    """
    Register the WebSocket terminal route on the app.

    :param sock: the flask-sock instance
    """

    @sock.route("/api/digital-twin/terminal/<container_name>")
    def terminal(ws: Any, container_name: str) -> None:
        """
        Handle a WebSocket terminal session for a container.

        Authenticates via query param, opens a Docker exec TTY,
        and pipes data between the WebSocket and the raw Docker socket.

        :param ws: the WebSocket connection
        :param container_name: the Docker container name
        """
        token = request.args.get("token", "")
        if not token:
            ws.close(1008, "Missing token")
            return
        session = DatabaseFacade.get_session_token_by_token(token)
        if session is None:
            ws.close(1008, "Invalid token")
            return

        if not container_name.startswith(DOCKER.CONTAINER_PREFIX):
            ws.close(1008, "Invalid container name")
            return

        try:
            raw_sock, exec_id = DockerManager.exec_create(container_name)
        except Exception as e:
            ws.close(1011, str(e))
            return

        raw_sock.settimeout(1.0)
        stop_event = threading.Event()

        def reader() -> None:
            """
            Read from Docker socket and forward to WebSocket.
            """
            try:
                while not stop_event.is_set():
                    try:
                        data = raw_sock.recv(4096)
                    except socket.timeout:
                        continue
                    except OSError:
                        break
                    if not data:
                        break
                    try:
                        ws.send(data)
                    except Exception:
                        break
            except Exception:
                pass

        read_thread = threading.Thread(target=reader, daemon=True)
        read_thread.start()

        try:
            while True:
                message = ws.receive()
                if message is None:
                    break
                if isinstance(message, str):
                    try:
                        parsed = json.loads(message)
                        if parsed.get("type") == "resize":
                            DockerManager.exec_resize(
                                exec_id,
                                parsed.get("rows", 24),
                                parsed.get("cols", 80),
                            )
                            continue
                    except (json.JSONDecodeError, ValueError):
                        pass
                    raw_sock.sendall(message.encode("utf-8"))
                else:
                    raw_sock.sendall(message)
        except Exception:
            pass
        finally:
            stop_event.set()
            try:
                raw_sock.close()
            except Exception:
                pass
            read_thread.join(timeout=2)
