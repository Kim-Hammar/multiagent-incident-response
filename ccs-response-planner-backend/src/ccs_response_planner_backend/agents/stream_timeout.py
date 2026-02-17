"""
Idle-timeout wrapper for streaming iterators.

Wraps any blocking iterator with a timeout so that if no item
arrives within the specified duration, a ``TimeoutError`` is raised.
"""
import queue
import threading
from typing import Iterator, TypeVar

T = TypeVar("T")

DEFAULT_IDLE_TIMEOUT = 300.0  # 5 minutes


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
            raise TimeoutError(
                f"LLM stream idle for {timeout}s — "
                f"no data received"
            )
        if is_error:
            raise value  # type: ignore[misc]
        if value is sentinel:
            return
        yield value  # type: ignore[misc]
