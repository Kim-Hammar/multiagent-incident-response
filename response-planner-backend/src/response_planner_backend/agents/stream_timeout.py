"""
Idle-timeout wrapper for streaming iterators.

Wraps any blocking iterator with a timeout so that if no item
arrives within the specified duration, a ``TimeoutError`` is raised.
"""
import logging
import queue
import threading
from typing import Iterator, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

DEFAULT_IDLE_TIMEOUT = 400.0


class AgentTimeoutError(TimeoutError):
    """
    Timeout with structured metadata about which agent/step failed.

    :param message: human-readable error description
    :param agent_name: name of the agent that timed out
    :param step_number: which step was running when the timeout hit
    :param model_name: LLM model in use
    :param elapsed_seconds: wall-clock seconds elapsed
    """

    def __init__(
        self,
        message: str,
        *,
        agent_name: str = "",
        step_number: int = 0,
        model_name: str = "",
        elapsed_seconds: float = 0.0,
    ) -> None:
        super().__init__(message)
        self.agent_name = agent_name
        self.step_number = step_number
        self.model_name = model_name
        self.elapsed_seconds = elapsed_seconds

    def to_error_detail(self) -> dict[str, object]:
        """
        Return a JSON-safe dict for the frontend error card.

        :return: dict with error metadata
        """
        return {
            "message": str(self),
            "error_type": "AgentTimeoutError",
            "agent_name": self.agent_name,
            "step_number": self.step_number,
            "model_name": self.model_name,
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "last_status": (
                f"Step {self.step_number} of "
                f"{self.agent_name}"
            ),
        }


def iter_with_idle_timeout(
    stream: Iterator[T],
    timeout: float = DEFAULT_IDLE_TIMEOUT,
) -> Iterator[T]:
    """
    Yield items from *stream*, raising ``TimeoutError`` if no
    item arrives within *timeout* seconds.

    A producer thread pulls items from the (potentially blocking)
    *stream* and puts them into a bounded queue.  The caller
    consumes from the queue with a timeout, so the main thread
    is never stuck waiting on a hung API.

    :param stream: any iterable / iterator (e.g. an LLM stream)
    :param timeout: seconds to wait for each item before raising
    :return: an iterator that yields items from *stream*
    """
    q: queue.Queue[tuple[bool, object]] = queue.Queue(
        maxsize=64,
    )
    sentinel = object()

    def _producer() -> None:
        try:
            for item in stream:
                q.put((False, item))
            q.put((False, sentinel))
        except Exception as exc:
            logger.error(
                "LLM stream producer error: %s: %s",
                type(exc).__name__, exc,
            )
            q.put((True, exc))

    t = threading.Thread(
        target=_producer, daemon=True,
        name="stream-timeout-producer",
    )
    t.start()

    while True:
        try:
            is_error, value = q.get(timeout=timeout)
        except queue.Empty:
            logger.error(
                "LLM stream idle timeout after %ss "
                "— no data received from model",
                timeout,
            )
            raise TimeoutError(
                f"LLM stream idle for {timeout}s — "
                f"no data received"
            )
        if is_error:
            raise value  # type: ignore[misc]
        if value is sentinel:
            return
        yield value  # type: ignore[misc]
