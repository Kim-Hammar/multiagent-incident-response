"""
Thread-safe singleton for running agent generators in background threads.

Jobs accumulate events in memory so they can be polled by the frontend
even after a tab close/reopen.
"""
import json
import logging
import threading
import time
import uuid
from typing import Any, Callable, Generator, Optional

logger = logging.getLogger(__name__)

# Cap each events response at ~100 KB of raw JSON so
# even slow connections can download a page quickly.
_MAX_RESPONSE_BYTES = 100_000


class _Job:
    """
    Internal state for a single background job.
    """

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.event_sizes: list[int] = []
        self.done: bool = False
        self.error: Optional[dict[str, object]] = None
        self.cancelled: bool = False
        self.lock: threading.Lock = threading.Lock()
        self.last_event_time: float = time.time()
        self.start_time: float = time.time()
        self.last_status: str = "Starting..."


_STATUS_MAP: dict[str, str] = {
    "system_prompt": "Initializing agent",
    "thinking": "Model is reasoning",
    "text": "Model is generating text",
    "tool_input_started": "Generating tool input",
    "tool_input_delta": "Generating tool input",
    "tool_proposal": "Preparing tool call",
    "tool_result": "Processing tool result",
    "context_compaction": "Compacting context",
    "dt_progress": "Deploying digital twin",
    "dt_progress_detail": "Deploying digital twin",
    "sandbox_progress": "Starting Python sandbox",
    "output_chunk": "Executing command",
    "sub_event": "Running sub-agent",
    "assessment": "Producing report",
    "report": "Producing report",
    "validation_report": "Producing report",
    "code_report": "Producing report",
    "report_review": "Producing report",
    "planner_report": "Producing report",
    "host_analysis": "Producing report",
    "action_validation": "Producing report",
    "error": "Error occurred",
}


def _status_from_event(event: dict[str, Any]) -> str | None:
    """
    Derive a short human-readable status from an event dict.

    Returns ``None`` when the event type should not update the
    status (e.g. ``context_usage``).

    :param event: a job event dict
    :return: a status string or None
    """
    etype = event.get("type", "")
    label = _STATUS_MAP.get(etype)
    if label is None:
        return None
    if etype == "tool_proposal":
        name = event.get("tool_name", "")
        if name:
            return f"Preparing tool call: {name}"
    if etype in (
        "dt_progress", "dt_progress_detail",
        "sandbox_progress",
    ):
        msg = event.get("message", "")
        if msg:
            return str(msg)
    return label


class JobManager:
    """
    Thread-safe singleton that runs generator functions in
    background daemon threads, accumulating their yielded events.
    """

    _instance: Optional["JobManager"] = None
    _init_lock: threading.Lock = threading.Lock()
    _jobs: dict[str, _Job]
    _lock: threading.Lock

    def __new__(cls) -> "JobManager":
        """
        Return the singleton instance, creating it if needed.

        :return: the singleton JobManager instance
        """
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._jobs = {}
                    inst._lock = threading.Lock()
                    cls._instance = inst
        return cls._instance

    def start_job(
        self,
        job_id: str,
        generator_fn: Callable[[], Generator[
            dict[str, Any], None, None
        ]],
        on_complete: Optional[Callable[
            [list[dict[str, Any]]], None
        ]] = None,
    ) -> str:
        """
        Start a background job running a generator function.

        If a job with the same ID exists and is done, it is replaced.
        If a job with the same ID is still running, it is cancelled
        first.

        A heartbeat daemon thread runs alongside the job thread,
        injecting ``heartbeat`` events every 10 s when idle.

        :param job_id: unique key for this job
        :param generator_fn: callable returning a generator of events
        :param on_complete: optional callback invoked with all events
                            when the generator finishes
        :return: the job_id
        """
        with self._lock:
            existing = self._jobs.get(job_id)
            if existing is not None:
                if not existing.done:
                    existing.cancelled = True
            job = _Job()
            self._jobs[job_id] = job

        def _run() -> None:
            try:
                gen = generator_fn()
                _evt_count = 0
                for event in gen:
                    if job.cancelled:
                        logger.info(
                            "Job %s cancelled", job_id,
                        )
                        break
                    with job.lock:
                        event.setdefault(
                            "ts", int(time.time() * 1000),
                        )
                        job.events.append(event)
                        try:
                            size = len(json.dumps(
                                event, default=str,
                            ))
                        except Exception:
                            size = 1000
                        job.event_sizes.append(size)
                        job.last_event_time = time.time()
                        status = _status_from_event(event)
                        if status is not None:
                            job.last_status = status
                    # Periodically yield the GIL so Flask
                    # request threads can serve poll requests
                    # even during rapid event streaming.
                    _evt_count += 1
                    if _evt_count % 50 == 0:
                        time.sleep(0)
            except Exception as exc:
                logger.error(
                    "Job %s error: %s",
                    job_id, exc, exc_info=True,
                )
                elapsed = round(
                    time.time() - job.start_time, 1,
                )
                exc_type = type(exc).__name__
                with job.lock:
                    job.error = {
                        "message": str(exc),
                        "error_type": exc_type,
                        "last_status": job.last_status,
                        "elapsed_seconds": elapsed,
                    }
            finally:
                job.done = True
                if on_complete is not None and not job.cancelled:
                    try:
                        with job.lock:
                            events_copy = list(job.events)
                        on_complete(events_copy)
                    except Exception:
                        logger.error(
                            "Job %s on_complete error",
                            job_id, exc_info=True,
                        )

        def _heartbeat() -> None:
            while not job.done and not job.cancelled:
                time.sleep(10)
                idle = time.time() - job.last_event_time
                if idle >= 10:
                    with job.lock:
                        hb = {
                            "type": "heartbeat",
                            "timestamp": int(
                                time.time() * 1000,
                            ),
                            "status": job.last_status,
                        }
                        job.events.append(hb)
                        job.event_sizes.append(
                            len(json.dumps(hb)),
                        )

        t = threading.Thread(
            target=_run, daemon=True,
            name=f"job-{job_id}",
        )
        t.start()

        hb = threading.Thread(
            target=_heartbeat, daemon=True,
            name=f"heartbeat-{job_id}",
        )
        hb.start()

        return job_id

    def get_events(
        self,
        job_id: str,
        after: int = 0,
        limit: int = 0,
    ) -> dict[str, Any]:
        """
        Return events accumulated since index ``after``.

        When *limit* is positive, at most *limit* events are
        returned.  ``done`` is only ``True`` when the job has
        finished **and** all events have been delivered, so the
        caller naturally paginates by polling until ``done``.

        :param job_id: the job key
        :param after: index to start returning events from
        :param limit: max number of events to return (0 = all)
        :return: dict with events, done, error, next_index,
                 last_event_time
        """
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            return {
                "events": [],
                "done": True,
                "error": {
                    "message": "Job not found",
                    "error_type": "JobNotFound",
                    "last_status": "",
                    "elapsed_seconds": 0,
                },
                "next_index": 0,
                "last_event_time": 0,
            }
        with job.lock:
            all_remaining = job.events[after:]
            all_sizes = job.event_sizes[after:]
            if limit > 0:
                all_remaining = all_remaining[:limit]
                all_sizes = all_sizes[:limit]
            # Apply byte-size cap — always include at
            # least 1 event to guarantee progress.
            cumulative = 0
            cut = len(all_remaining)
            for i, size in enumerate(all_sizes):
                cumulative += size
                if (
                    cumulative > _MAX_RESPONSE_BYTES
                    and i > 0
                ):
                    cut = i
                    break
            new_events = all_remaining[:cut]
            next_index = after + len(new_events)
            total_events = len(job.events)
            all_delivered = next_index >= total_events
            is_done = job.done and all_delivered

            # Log when transitioning to done, or when
            # the job is done but not yet all-delivered
            # (to help debug stuck polls).
            if job.done and not all_delivered:
                logger.info(
                    "get_events: job=%s done but "
                    "NOT all_delivered: after=%d, "
                    "returned=%d, total=%d, "
                    "next_index=%d, cut=%d",
                    job_id, after, len(new_events),
                    total_events, next_index, cut,
                )

            return {
                "events": new_events,
                "done": is_done,
                "error": (
                    job.error if is_done else None
                ),
                "next_index": next_index,
                "last_event_time": int(
                    job.last_event_time * 1000,
                ),
            }

    def has_running_jobs(
        self,
        exclude: str | None = None,
    ) -> bool:
        """
        Check whether any job is currently running.

        :param exclude: optional job_id to exclude from the check
        :return: True if at least one other job is running
        """
        with self._lock:
            for jid, job in self._jobs.items():
                if jid == exclude:
                    continue
                if not job.done:
                    return True
        return False

    def cancel_job(self, job_id: str) -> bool:
        """
        Set the cancelled flag on a running job.

        :param job_id: the job key
        :return: True if the job was found and cancelled
        """
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            return False
        job.cancelled = True
        return True

    def is_running(self, job_id: str) -> bool:
        """
        Check whether a job exists and has not finished.

        :param job_id: the job key
        :return: True if the job is still running
        """
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            return False
        return not job.done

    def get_status(
        self, job_id: str,
    ) -> dict[str, Any]:
        """
        Return a summary of the job's current state.

        :param job_id: the job key
        :return: dict with running, done, event_count
        """
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            return {
                "running": False,
                "done": True,
                "event_count": 0,
            }
        with job.lock:
            return {
                "running": not job.done,
                "done": job.done,
                "event_count": len(job.events),
            }

    def list_jobs(self) -> list[dict[str, Any]]:
        """
        Return a summary of every tracked job.

        :return: list of dicts with job_id, done, cancelled, error,
                 event_count, start_time, last_event_time, last_status
        """
        result: list[dict[str, Any]] = []
        with self._lock:
            job_ids = list(self._jobs.keys())
        for jid in job_ids:
            with self._lock:
                job = self._jobs.get(jid)
            if job is None:
                continue
            with job.lock:
                result.append({
                    "job_id": jid,
                    "done": job.done,
                    "cancelled": job.cancelled,
                    "error": job.error,
                    "event_count": len(job.events),
                    "start_time": int(
                        job.start_time * 1000,
                    ),
                    "last_event_time": int(
                        job.last_event_time * 1000,
                    ),
                    "last_status": job.last_status,
                })
        return result

    def cleanup(self, job_id: str) -> None:
        """
        Remove a completed job from memory.

        :param job_id: the job key
        """
        with self._lock:
            self._jobs.pop(job_id, None)

    @staticmethod
    def generate_job_id() -> str:
        """
        Generate a unique job ID.

        :return: a UUID4 string
        """
        return str(uuid.uuid4())


job_manager = JobManager()
