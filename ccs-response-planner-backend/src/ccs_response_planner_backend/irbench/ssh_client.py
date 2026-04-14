"""
SSH execution client for IRBench evaluation.

Wraps ``paramiko`` to provide an ``exec`` method whose return
format mirrors the existing ``dt_exec`` interface so that agent
prompts and tool handling code can treat SSH and Docker
execution interchangeably.
"""
import logging
import shlex
import socket
import threading
from typing import Any

import paramiko

from ccs_response_planner_backend.irbench.config import (
    SSHConfig,
)

logger = logging.getLogger(__name__)

# Commands that should never be executed on a remote host.
_BLOCKED_PATTERNS = [
    "rm -rf /",
    "mkfs",
    "dd if=",
    "shutdown",
    "reboot",
    "init 0",
    "init 6",
    "halt",
    "poweroff",
]


class SSHClient:
    """
    Persistent SSH connection to a single remote host.

    Provides ``exec(command)`` with timeout handling and
    automatic reconnection on transient failures.

    :param config: SSH connection parameters
    :param command_timeout: default per-command timeout in
        seconds (can be overridden per call)
    """

    def __init__(
        self,
        config: SSHConfig,
        command_timeout: int = 120,
    ) -> None:
        self._config = config
        self._default_timeout = command_timeout
        self._client: paramiko.SSHClient | None = None
        self._lock = threading.Lock()
        self._connect()

    # ── connection management ────────────────────────────

    def _connect(self) -> None:
        """
        Establish (or re-establish) the SSH connection.
        """
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(
            paramiko.AutoAddPolicy(),
        )
        connect_kwargs: dict[str, Any] = {
            "hostname": self._config.hostname,
            "port": self._config.port,
            "username": self._config.username,
            "timeout": 30,
            "banner_timeout": 30,
        }
        if self._config.key_filename:
            connect_kwargs["key_filename"] = (
                self._config.key_filename
            )
        elif self._config.password:
            connect_kwargs["password"] = (
                self._config.password
            )
        client.connect(**connect_kwargs)
        self._client = client
        logger.info(
            "SSH connected to %s@%s:%d",
            self._config.username,
            self._config.hostname,
            self._config.port,
        )

    def _ensure_connected(self) -> paramiko.SSHClient:
        """
        Return the active client, reconnecting if needed.

        :return: an active paramiko SSHClient
        """
        if self._client is None:
            self._connect()
            assert self._client is not None
            return self._client
        transport = self._client.get_transport()
        if transport is None or not transport.is_active():
            logger.info(
                "SSH transport lost; reconnecting...",
            )
            self._connect()
        assert self._client is not None
        return self._client

    def close(self) -> None:
        """
        Close the SSH connection.
        """
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    # ── command execution ────────────────────────────────

    @staticmethod
    def _is_blocked(command: str) -> bool:
        """
        Check whether a command matches a blocked pattern.

        :param command: the shell command to check
        :return: True if the command should be rejected
        """
        lower = command.lower().strip()
        for pattern in _BLOCKED_PATTERNS:
            if pattern in lower:
                return True
        return False

    def exec(
        self,
        command: str,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """
        Execute a shell command on the remote host.

        The command is wrapped with the ``timeout`` utility
        so that it is killed on the remote side if it
        exceeds the time limit.

        :param command: the shell command to run
        :param timeout: per-command timeout in seconds;
            defaults to ``self._default_timeout``
        :return: a dict with host, command, exit_code,
            and output (mirrors dt_exec format)
        """
        if self._is_blocked(command):
            return {
                "host": self._config.hostname,
                "command": command,
                "exit_code": -1,
                "output": (
                    "[BLOCKED] Command rejected by "
                    "safety filter."
                ),
            }

        effective_timeout = (
            timeout
            if timeout is not None
            else self._default_timeout
        )
        wrapped = (
            f"timeout {effective_timeout} "
            f"sh -c {shlex.quote(command)}"
        )

        for attempt in range(2):
            try:
                return self._exec_once(
                    command, wrapped, effective_timeout,
                )
            except (
                paramiko.SSHException,
                socket.error,
                EOFError,
            ) as exc:
                if attempt == 0:
                    logger.warning(
                        "SSH exec failed (%s); "
                        "reconnecting...",
                        exc,
                    )
                    with self._lock:
                        self._connect()
                else:
                    return {
                        "host": self._config.hostname,
                        "command": command,
                        "exit_code": -1,
                        "output": (
                            f"[SSH ERROR] {exc}"
                        ),
                    }
        # Unreachable, but keeps mypy happy.
        return {
            "host": self._config.hostname,
            "command": command,
            "exit_code": -1,
            "output": "[SSH ERROR] Unexpected failure",
        }

    def _exec_once(
        self,
        original_command: str,
        wrapped_command: str,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        """
        Execute a single command attempt.

        Uses a background thread + ``thread.join`` as a
        hard fallback so that a hung channel never blocks
        the main thread indefinitely.

        :param original_command: the user's original command
        :param wrapped_command: command wrapped with timeout
        :param timeout_seconds: seconds for the timeout
        :return: result dict
        """
        grace = 30
        logger.info(
            "SSH exec [timeout=%ds]: %s",
            timeout_seconds,
            original_command[:120],
        )

        result: dict[str, Any] = {}

        def _run() -> None:
            with self._lock:
                client = self._ensure_connected()
                _, stdout, stderr = client.exec_command(
                    wrapped_command,
                    timeout=timeout_seconds + grace,
                )
                result["exit_code"] = (
                    stdout.channel.recv_exit_status()
                )
                result["out"] = stdout.read().decode(
                    "utf-8", errors="replace",
                )
                result["err"] = stderr.read().decode(
                    "utf-8", errors="replace",
                )

        thread = threading.Thread(
            target=_run, daemon=True,
        )
        thread.start()
        thread.join(timeout=timeout_seconds + grace)

        if thread.is_alive():
            logger.warning(
                "SSH exec TIMED OUT after %ds: %s",
                timeout_seconds,
                original_command[:120],
            )
            # Force-close the transport so the blocked
            # thread unblocks on the dead socket.
            if self._client is not None:
                try:
                    transport = (
                        self._client.get_transport()
                    )
                    if transport:
                        transport.close()
                except Exception:
                    pass
            thread.join(timeout=5)
            self._client = None
            return {
                "host": self._config.hostname,
                "command": original_command,
                "exit_code": -1,
                "output": (
                    f"[TIMEOUT] Command killed after "
                    f"{timeout_seconds}s. Use short, "
                    f"targeted commands."
                ),
            }

        exit_code = result.get("exit_code", -1)
        out = result.get("out", "")
        err = result.get("err", "")
        output = out
        if err:
            output = f"{out}\n{err}" if out else err

        if exit_code == 124:
            output += (
                f"\n\n[TIMEOUT] Command killed after "
                f"{timeout_seconds}s. Use short, "
                f"targeted commands."
            )
            exit_code = -1

        logger.info(
            "SSH exec done [exit=%d, %d chars]: %s",
            exit_code, len(output),
            original_command[:80],
        )

        return {
            "host": self._config.hostname,
            "command": original_command,
            "exit_code": exit_code,
            "output": output,
        }
