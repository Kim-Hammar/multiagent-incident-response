"""
Routes and sub-resources for the /agents resource.
"""
import json
import logging
import math
import uuid
from typing import Any, Generator

from flask import Blueprint, Response, g, jsonify, request

from ccs_response_planner_backend.rest_api.job_manager import (
    job_manager,
)

from ccs_response_planner_backend.agents.report_agent.agent import (
    ReportAgent,
)
from ccs_response_planner_backend.agents.report_agent.prompt import (
    SYSTEM_PROMPT_TEMPLATE,
)
from ccs_response_planner_backend.agents.report_agent.tools import (
    STREAMING_TOOL_DISPATCH as INFO_STREAMING_DISPATCH,
    TOOL_DISPATCH,
)
from ccs_response_planner_backend.agents.validation_agent.agent import (
    ValidationAgent,
)
from ccs_response_planner_backend.agents.validation_agent.prompt import (
    build_system_prompt as build_validation_prompt,
)
from ccs_response_planner_backend.agents.validation_agent.tools import (
    STREAMING_TOOL_DISPATCH as VALIDATION_STREAMING_DISPATCH,
    TOOL_DISPATCH as VALIDATION_TOOL_DISPATCH,
)
from ccs_response_planner_backend.agents.code_agent.agent import (
    CodeAgent,
)
from ccs_response_planner_backend.agents.code_agent.prompt import (
    SYSTEM_PROMPT_TEMPLATE as CODE_PROMPT_TEMPLATE,
)
from ccs_response_planner_backend.agents.code_agent.tools import (
    STREAMING_TOOL_DISPATCH as CODE_STREAMING_DISPATCH,
    TOOL_DISPATCH as CODE_TOOL_DISPATCH,
)
from ccs_response_planner_backend.agents.code_reviewer_agent.agent import (
    CodeReviewerAgent,
)
from ccs_response_planner_backend.agents.code_reviewer_agent.prompt import (
    SYSTEM_PROMPT_TEMPLATE as CODE_REVIEW_PROMPT_TEMPLATE,
)
from ccs_response_planner_backend.agents.code_reviewer_agent.tools import (
    STREAMING_TOOL_DISPATCH as CODE_REVIEW_STREAMING_DISPATCH,
    TOOL_DISPATCH as CODE_REVIEW_TOOL_DISPATCH,
)
from ccs_response_planner_backend.agents.planner_agent.agent import (
    PlannerAgent,
)
from ccs_response_planner_backend.agents.planner_agent.prompt import (
    SYSTEM_PROMPT_TEMPLATE as PLANNER_PROMPT_TEMPLATE,
)
from ccs_response_planner_backend.agents.planner_agent.tools import (
    STREAMING_TOOL_DISPATCH as PLANNER_STREAMING_DISPATCH,
    TOOL_DISPATCH as PLANNER_TOOL_DISPATCH,
)
from ccs_response_planner_backend.agents.code_manager_agent.agent import (
    CodeManagerAgent,
)
from ccs_response_planner_backend.agents.code_manager_agent.prompt import (
    SYSTEM_PROMPT_TEMPLATE as CODE_MANAGER_PROMPT_TEMPLATE,
)
from ccs_response_planner_backend.agents.code_manager_agent.tools import (
    STREAMING_TOOL_DISPATCH as CODE_MANAGER_STREAMING_DISPATCH,
    TOOL_DISPATCH as CODE_MANAGER_TOOL_DISPATCH,
)
from ccs_response_planner_backend.agents.plan_manager_agent.agent import (
    PlanManagerAgent,
)
from ccs_response_planner_backend.agents.plan_manager_agent.prompt import (
    SYSTEM_PROMPT_TEMPLATE as PLAN_MANAGER_PROMPT_TEMPLATE,
)
from ccs_response_planner_backend.agents.plan_manager_agent.tools import (
    STREAMING_TOOL_DISPATCH as PLAN_MANAGER_STREAMING_DISPATCH,
    TOOL_DISPATCH as PLAN_MANAGER_TOOL_DISPATCH,
    run_code_agent_direct_stream,
)
from ccs_response_planner_backend.agents.report_reviewer_agent.agent import (
    ReportReviewerAgent,
)
from ccs_response_planner_backend.agents.report_reviewer_agent.prompt import (
    SYSTEM_PROMPT_TEMPLATE as REPORT_REVIEW_PROMPT_TEMPLATE,
)
from ccs_response_planner_backend.agents.report_reviewer_agent.tools import (
    STREAMING_TOOL_DISPATCH as REPORT_REVIEW_STREAMING_DISPATCH,
    TOOL_DISPATCH as REPORT_REVIEW_TOOL_DISPATCH,
)
from ccs_response_planner_backend.agents.report_manager_agent.agent import (
    ReportManagerAgent,
)
from ccs_response_planner_backend.agents.report_manager_agent.prompt import (
    SYSTEM_PROMPT_TEMPLATE as REPORT_MANAGER_PROMPT_TEMPLATE,
)
from ccs_response_planner_backend.agents.report_manager_agent.tools import (
    STREAMING_TOOL_DISPATCH as REPORT_MANAGER_STREAMING_DISPATCH,
    TOOL_DISPATCH as REPORT_MANAGER_TOOL_DISPATCH,
)
from ccs_response_planner_backend.agents.orchestrator_agent.agent import (
    OrchestratorAgent,
)
from ccs_response_planner_backend.agents.orchestrator_agent.prompt import (
    build_system_prompt as build_orchestrator_prompt,
)
from ccs_response_planner_backend.agents.orchestrator_agent.tools import (
    STREAMING_TOOL_DISPATCH as ORCHESTRATOR_STREAMING_DISPATCH,
    TOOL_DISPATCH as ORCHESTRATOR_TOOL_DISPATCH,
    run_report_agent_direct_stream,
)
from ccs_response_planner_backend.agents.pentest_agent.agent import (
    PentestAgent,
)
from ccs_response_planner_backend.agents.pentest_agent.prompt import (
    build_system_prompt as build_pentest_prompt,
)
from ccs_response_planner_backend.agents.pentest_agent.tools import (
    STREAMING_TOOL_DISPATCH as PENTEST_STREAMING_DISPATCH,
)
from ccs_response_planner_backend.agents.host_analyzer_agent.agent import (
    HostAnalyzerAgent,
)
from ccs_response_planner_backend.agents.host_analyzer_agent.prompt import (
    build_system_prompt as build_host_analyzer_prompt,
)
from ccs_response_planner_backend.agents.host_analyzer_agent.tools import (
    STREAMING_TOOL_DISPATCH as HOST_ANALYZER_STREAMING_DISPATCH,
)
from ccs_response_planner_backend.agents.action_validator_agent.agent import (
    ActionValidatorAgent,
)
from ccs_response_planner_backend.agents.action_validator_agent.prompt import (
    build_system_prompt as build_action_validator_prompt,
)
from ccs_response_planner_backend.agents.action_validator_agent.tools import (
    STREAMING_TOOL_DISPATCH as ACTION_VALIDATOR_STREAMING_DISPATCH,
)
from ccs_response_planner_backend.agents.dt_prompt_utils import (
    format_attacker_info,
    format_container_list,
    format_container_list_with_attacker,
    format_container_table,
    format_network_connectivity,
)
from ccs_response_planner_backend.constants.constants import (
    API, DIGITAL_TWIN, DOCKER,
)
from ccs_response_planner_backend.db.database_facade import DatabaseFacade
from ccs_response_planner_backend.docker_manager.docker_manager import (
    DockerManager,
)
from ccs_response_planner_backend.rest_api.util.auth import token_required

logger = logging.getLogger(__name__)

_DT_TOOLS = {"dt_exec", "generate_attack_image"}


def _make_error_event(exc: Exception) -> dict[str, Any]:
    """
    Build a structured error event with optional detail.

    :param exc: the exception that occurred
    :return: an error event dict
    """
    event: dict[str, Any] = {
        "type": "error", "message": str(exc),
    }
    if hasattr(exc, "to_error_detail"):
        event["errorDetail"] = exc.to_error_detail()
    else:
        event["errorDetail"] = {
            "message": str(exc),
            "error_type": type(exc).__name__,
        }
    return event


agents_bp = Blueprint(
    API.AGENTS_RESOURCE, __name__,
    url_prefix=f"{API.PREFIX}/{API.AGENTS_RESOURCE}",
)


def _sanitize_for_json(obj: Any) -> Any:
    """
    Recursively replace ``NaN`` and ``Infinity`` floats
    with ``None`` so the result is valid JSON for
    ``JSON.parse`` in the browser.

    :param obj: any JSON-compatible value
    :return: sanitised copy
    """
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    return obj


def _redeploy_dt(
    job_id: str | None = None,
) -> Generator[dict[str, str], None, None]:
    """
    Stop and redeploy the digital twin for a fresh state.

    When *job_id* is given and other jobs are still running,
    the current digital twin is reused (if deployed) or
    deployed without stopping first, so a concurrent agent's
    DT is not torn down mid-execution.

    Yields ``dt_progress`` event dicts that can be streamed to
    the frontend as NDJSON.

    :param job_id: optional job id of the calling job
    :return: a generator of progress event dicts
    """
    config = DatabaseFacade.get_digital_twin_config()
    if config is None:
        config = DIGITAL_TWIN.DEFAULT_CONFIG

    if job_id and job_manager.has_running_jobs(
        exclude=job_id,
    ):
        status = DockerManager.status(config=config)
        if status.get("deployed"):
            yield {
                "type": "dt_progress",
                "phase": "ready",
                "message": "Reusing current digital twin",
            }
            return
        # DT not deployed — deploy without stopping
        yield {
            "type": "dt_progress",
            "phase": "deploy",
            "message": "Deploying digital twin...",
        }
        for item in DockerManager.deploy(config):
            msg = item.get("message", "")
            if item.get("type") == "progress" and msg:
                logger.info(
                    "DT deploy (reuse): %s", msg,
                )
                yield {
                    "type": "dt_progress_detail",
                    "phase": "deploy",
                    "message": msg,
                }
        yield {
            "type": "dt_progress",
            "phase": "ready",
            "message": "Digital twin ready",
        }
        return

    # No other jobs running — normal stop + redeploy
    yield {
        "type": "dt_progress",
        "phase": "stop",
        "message": "Stopping digital twin...",
    }
    for item in DockerManager.stop():
        msg = item.get("message", "")
        if item.get("type") == "progress" and msg:
            logger.info("DT redeploy (stop): %s", msg)
            yield {
                "type": "dt_progress_detail",
                "phase": "stop",
                "message": msg,
            }
    yield {
        "type": "dt_progress",
        "phase": "deploy",
        "message": "Deploying fresh digital twin...",
    }
    for item in DockerManager.deploy(config):
        msg = item.get("message", "")
        if item.get("type") == "progress" and msg:
            logger.info("DT redeploy (deploy): %s", msg)
            yield {
                "type": "dt_progress_detail",
                "phase": "deploy",
                "message": msg,
            }
    yield {
        "type": "dt_progress",
        "phase": "ready",
        "message": "Digital twin ready",
    }


def _start_sandbox() -> Generator[
    dict[str, str], None, None
]:
    """
    Ensure the Python sandbox container is running.

    Yields ``sandbox_progress`` event dicts that can be streamed
    to the frontend as NDJSON.

    :return: a generator of progress event dicts
    """
    import docker as docker_lib
    from ccs_response_planner_backend.agents.planner_agent.tools import (
        _ensure_python_sandbox,
    )
    yield {
        "type": "sandbox_progress",
        "phase": "start",
        "message": "Starting Python sandbox...",
    }
    client = docker_lib.from_env()
    _ensure_python_sandbox(client)
    yield {
        "type": "sandbox_progress",
        "phase": "ready",
        "message": "Python sandbox ready",
    }


def _read_policy_from_sandbox() -> bytes | None:
    """
    Read /workspace/_policy.zip from the Python sandbox.

    :return: the policy bytes or None if the file does not exist
    """
    import base64
    import docker
    client = docker.from_env()
    try:
        ct = client.containers.get(
            DOCKER.PYTHON_SANDBOX_CONTAINER,
        )
    except Exception:
        return None
    exec_id = client.api.exec_create(
        ct.id,
        ["/bin/sh", "-c",
         "cat /workspace/_policy.zip | base64"],
        stdout=True, stderr=True,
    )["Id"]
    output = client.api.exec_start(exec_id)
    exit_code = client.api.exec_inspect(exec_id)[
        "ExitCode"
    ]
    if exit_code != 0:
        return None
    return base64.b64decode(output)


def _write_env_to_sandbox(env_code: str) -> None:
    """
    Write the MDP env code to /workspace/_env.py in the sandbox.

    Uses base64 encoding to avoid any quoting issues.

    :param env_code: the Python source code for the environment
    """
    import docker as docker_lib
    from ccs_response_planner_backend.agents.planner_agent.tools import (
        _ensure_python_sandbox,
        _write_code_to_sandbox,
    )
    client = docker_lib.from_env()
    ct = _ensure_python_sandbox(client)
    _write_code_to_sandbox(client, ct, env_code, "_env.py")


def _install_policy_in_sandbox(
    policy_bytes: bytes,
    code_report: dict[str, str],
) -> None:
    """
    Write RL policy .zip and env code into the Python sandbox.

    :param policy_bytes: the trained policy zip bytes
    :param code_report: the code report dict with generated_code
    """
    import base64
    import docker
    client = docker.from_env()

    try:
        ct = client.containers.get(
            DOCKER.PYTHON_SANDBOX_CONTAINER,
        )
        if ct.status != "running":
            ct.start()
    except docker.errors.NotFound:
        ct = client.containers.run(
            DOCKER.PYTHON_SANDBOX_IMAGE,
            name=DOCKER.PYTHON_SANDBOX_CONTAINER,
            detach=True,
        )

    env_code = code_report.get("generated_code", "")
    if env_code:
        encoded = base64.b64encode(
            env_code.encode("utf-8"),
        ).decode("ascii")
        write_cmd = (
            f"python3 -c \"import base64; "
            f"open('/workspace/_env.py','wb')"
            f".write(base64.b64decode('{encoded}'))\""
        )
        client.api.exec_start(
            client.api.exec_create(
                ct.id, ["/bin/sh", "-c", write_cmd],
                stdout=True, stderr=True,
            )["Id"],
        )

    policy_b64 = base64.b64encode(
        policy_bytes,
    ).decode("ascii")
    write_cmd = (
        f"python3 -c \"import base64; "
        f"open('/workspace/_policy.zip','wb')"
        f".write(base64.b64decode('{policy_b64}'))\""
    )
    client.api.exec_start(
        client.api.exec_create(
            ct.id, ["/bin/sh", "-c", write_cmd],
            stdout=True, stderr=True,
        )["Id"],
    )


def _save_step_result(
    session_id: int,
    username: str,
    events: list[dict[str, Any]],
) -> None:
    """
    Auto-save orchestrator step results to the session.

    Called when a background job finishes. Builds
    conversation history entries from accumulated events
    and persists them to PostgreSQL.

    :param session_id: the planning session id
    :param username: the session owner
    :param events: list of events from the job
    """
    try:
        accumulated_text = ""
        final_entry: dict[str, Any] | None = None
        context_usage: dict[str, Any] | None = None
        pending_proposal: Any = None

        for ev in events:
            ev_type = ev.get("type", "")
            if ev_type in ("text", "thinking"):
                accumulated_text += (
                    ev.get("delta", "")
                    or ev.get("full_text", "")
                )
            elif ev_type == "tool_proposal":
                final_entry = ev
                pending_proposal = ev
            elif ev_type in (
                "orchestrator_agent_report",
                "assessment", "code_report",
                "validation_report", "report",
                "review_report", "planner_report",
                "report_manager_report",
                "orchestrator_report",
                "plan_manager_report",
                "report_review",
                "pentest_report",
                "host_analysis",
                "action_validation",
            ):
                final_entry = ev
            elif ev_type == "context_usage":
                context_usage = ev
            elif ev_type == "error":
                final_entry = ev

        session = (
            DatabaseFacade.get_planning_session(
                session_id, username,
            )
        )
        if not session:
            return

        history = list(
            session.get("conversation_history") or []
        )
        # Remove any leftover streaming entry
        history = [
            e for e in history
            if e.get("type") != "streaming"
        ]

        # Check if already present anywhere in history
        already_saved = any(
            e.get("type") == final_entry.get("type")
            and e.get("tool_name") == final_entry.get(
                "tool_name",
            )
            for e in history
        ) if final_entry else False
        if not already_saved:
            if accumulated_text:
                history.append({
                    "role": "model",
                    "type": "reasoning",
                    "text": accumulated_text,
                })
            if final_entry:
                history.append({
                    "role": "model",
                    **final_entry,
                })

        update_kwargs: dict[str, Any] = {
            "conversation_history": history,
            "ui_state": {
                "running": False,
                "executingTool": None,
            },
        }
        if context_usage:
            update_kwargs["context_usage"] = (
                context_usage
            )
        if pending_proposal:
            update_kwargs["pending_proposal"] = (
                pending_proposal
            )
        else:
            update_kwargs["pending_proposal"] = False

        DatabaseFacade.update_planning_session(
            session_id, username, **update_kwargs,
        )
    except Exception:
        logger.error(
            "Failed to auto-save step result for "
            "session %s", session_id, exc_info=True,
        )


def _save_tool_result(
    session_id: int,
    username: str,
    events: list[dict[str, Any]],
    tool_name: str,
) -> None:
    """
    Auto-save tool execution results to the session.

    Called when a background tool job finishes.

    :param session_id: the planning session id
    :param username: the session owner
    :param events: list of events from the job
    :param tool_name: name of the tool that was executed
    """
    try:
        done_event: dict[str, Any] | None = None
        for ev in events:
            if ev.get("type") == "done":
                done_event = ev

        session = (
            DatabaseFacade.get_planning_session(
                session_id, username,
            )
        )
        if not session:
            return

        history = list(
            session.get("conversation_history") or []
        )

        if done_event:
            already_saved = any(
                e.get("type") == "tool_result"
                and e.get("tool_name") == tool_name
                for e in history
            )
            if not already_saved:
                result = done_event.get("result", {})
                if not result:
                    result = {
                        k: done_event.get(k)
                        for k in (
                            "container", "command",
                            "exit_code", "output",
                        )
                        if done_event.get(k) is not None
                    }
                history.append({
                    "role": "tool",
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "result": result,
                })

        DatabaseFacade.update_planning_session(
            session_id, username,
            conversation_history=history,
            pending_proposal=False,
            ui_state={
                "running": False,
                "executingTool": None,
            },
        )
    except Exception:
        logger.error(
            "Failed to auto-save tool result for "
            "session %s", session_id, exc_info=True,
        )


@agents_bp.route("/jobs", methods=["GET"])
@token_required
def list_jobs() -> tuple[Response, int]:
    """
    List all tracked background jobs with summary info.

    :return: a tuple of (JSON array response, HTTP status code)
    """
    return jsonify(job_manager.list_jobs()), 200


@agents_bp.route(
    "/jobs/<job_id>", methods=["DELETE"],
)
@token_required
def delete_job(
    job_id: str,
) -> tuple[Response, int]:
    """
    Remove a job from memory.

    :param job_id: the job identifier
    :return: a tuple of (JSON response, HTTP status code)
    """
    job_manager.cleanup(job_id)
    return jsonify({"success": True}), 200


@agents_bp.route(
    "/jobs/<job_id>/events", methods=["GET"],
)
@token_required
def job_events(
    job_id: str,
) -> tuple[Response, int]:
    """
    Poll for events from a background job.

    Sanitises the response JSON to replace ``NaN`` and
    ``Infinity`` floats with ``null`` — Python's
    ``json.dumps`` emits them but JavaScript's
    ``JSON.parse`` rejects them.

    :param job_id: the job identifier
    :return: a tuple of (JSON response, HTTP status code)
    """
    after = request.args.get("after", 0, type=int)
    limit = request.args.get("limit", 0, type=int)
    data = job_manager.get_events(
        job_id, after=after, limit=limit,
    )
    if data.get("done"):
        logger.info(
            "job_events: job=%s done=True, "
            "events=%d, after=%d, next=%d",
            job_id, len(data.get("events", [])),
            after, data.get("next_index", 0),
        )
    body = json.dumps(
        _sanitize_for_json(data), default=str,
    )
    return Response(body, mimetype="application/json"), 200


@agents_bp.route(
    "/jobs/<job_id>/cancel", methods=["POST"],
)
@token_required
def job_cancel(
    job_id: str,
) -> tuple[Response, int]:
    """
    Cancel a running background job.

    :param job_id: the job identifier
    :return: a tuple of (JSON response, HTTP status code)
    """
    job_manager.cancel_job(job_id)
    return jsonify({"success": True}), 200


@agents_bp.route(
    "/jobs/<job_id>/status", methods=["GET"],
)
@token_required
def job_status(
    job_id: str,
) -> tuple[Response, int]:
    """
    Get the status of a background job.

    :param job_id: the job identifier
    :return: a tuple of (JSON response, HTTP status code)
    """
    data = job_manager.get_status(job_id)
    return jsonify(data), 200


@agents_bp.route("/report/step", methods=["POST"])
@token_required
def agents_report_step() -> tuple[Response, int]:
    """
    Start a ReportAgent step as a background job.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    system_description = body.get("system_description", "")
    security_alerts = body.get("security_alerts", "")
    operator_feedback = body.get("operator_feedback", "")
    conversation_history = body.get("conversation_history", [])
    images = body.get("images", [])
    model_name = body.get("model_name") or None
    if not isinstance(images, list):
        images = []
    if not system_description and not security_alerts:
        return jsonify({
            "error": (
                "system_description or security_alerts "
                "is required"
            ),
        }), 400
    session_id = body.get("session_id")
    username = g.username
    job_id = (
        str(session_id) if session_id
        else body.get("job_id") or str(uuid.uuid4())
    )
    last_prompt_tokens = body.get(
        "last_prompt_tokens", 0,
    )
    compaction_model = body.get(
        "compaction_model",
    ) or None
    compaction_threshold = body.get(
        "compaction_threshold", 0.8,
    )

    def on_complete(
        events: list[dict[str, Any]],
    ) -> None:
        """
        Auto-save step results to the planning session.

        :param events: the accumulated job events
        """
        if not session_id:
            return
        _save_step_result(
            session_id, username, events,
        )

    def run() -> Generator[
        dict[str, Any], None, None
    ]:
        """
        Run the ReportAgent step in background.

        :return: a generator of event dicts
        """
        try:
            dt_enabled = body.get(
                "dt_enabled", True,
            )
            info_tools_enabled = body.get(
                "info_tools_enabled", True,
            )
            if (
                not conversation_history
                and dt_enabled
            ):
                yield from _redeploy_dt(job_id)
                yield from _start_sandbox()
            dt_config = (
                DatabaseFacade.get_digital_twin_config()
                or DIGITAL_TWIN.DEFAULT_CONFIG
            )
            agent = ReportAgent()
            agent._last_prompt_tokens = (
                last_prompt_tokens
            )
            yield from agent.step_stream(
                system_description=system_description,
                security_alerts=security_alerts,
                operator_feedback=operator_feedback,
                conversation_history=conversation_history,
                images=images,
                model_name=model_name,
                dt_config=dt_config,
                compaction_model=compaction_model,
                compaction_threshold=compaction_threshold,
                dt_enabled=dt_enabled,
                info_tools_enabled=info_tools_enabled,
            )
        except Exception as e:
            yield _make_error_event(e)

    job_manager.start_job(
        job_id, run, on_complete=on_complete,
    )
    return jsonify({"job_id": job_id}), 202


@agents_bp.route("/report/prompt", methods=["POST"])
@token_required
def agents_report_prompt() -> tuple[Response, int]:
    """
    Render the ReportAgent system prompt from the given context.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    dt_config = (
        DatabaseFacade.get_digital_twin_config()
        or DIGITAL_TWIN.DEFAULT_CONFIG
    )
    prompt = SYSTEM_PROMPT_TEMPLATE.format(
        system_description=body.get(
            "system_description", "",
        ) or "N/A",
        security_alerts=body.get(
            "security_alerts", "",
        ) or "N/A",
        operator_feedback=body.get(
            "operator_feedback", "",
        ) or "N/A",
        dt_container_list=format_container_list(
            dt_config,
        ),
        dt_container_table=format_container_table(
            dt_config,
        ),
        dt_network_connectivity=(
            format_network_connectivity(dt_config)
        ),
        revision_notice="",
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route("/report/tool", methods=["POST"])
@token_required
def agents_report_tool() -> tuple[Response, int]:
    """
    Execute an approved tool call for the ReportAgent.

    Streaming tools run as background jobs; other tools
    return a single JSON response.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    tool_name = body.get("tool_name", "")
    tool_args = body.get("tool_args", {})
    incident_id = body.get("incident_id")
    if not tool_name:
        return jsonify({"error": "tool_name is required"}), 400
    if tool_name in _DT_TOOLS and incident_id is not None:
        tool_args["incident_id"] = incident_id

    if tool_name == "run_host_analyzers":
        tool_args["context"] = {
            "system_description": body.get(
                "system_description", "",
            ),
            "security_alerts": body.get(
                "security_alerts", "",
            ),
            "operator_feedback": body.get(
                "operator_feedback", "",
            ),
            "images": body.get("images"),
            "dt_config": body.get("dt_config"),
            "incident_id": incident_id,
            "username": g.username,
            "host_analyzer_model": body.get(
                "host_analyzer_model",
            ),
        }

    if tool_name in INFO_STREAMING_DISPATCH:
        session_id = body.get("session_id")
        username = g.username
        job_id = (
            str(session_id) if session_id
            else body.get("job_id")
            or str(uuid.uuid4())
        )

        def on_complete(
            events: list[dict[str, Any]],
        ) -> None:
            """
            Auto-save tool results to session.

            :param events: the accumulated job events
            """
            if not session_id:
                return
            _save_tool_result(
                session_id, username,
                events, tool_name,
            )

        def run() -> Generator[
            dict[str, Any], None, None
        ]:
            """
            Run the streaming tool in background.

            :return: a generator of event dicts
            """
            try:
                agent = ReportAgent()
                yield from agent.execute_tool_stream(
                    tool_name, tool_args,
                )
            except Exception as e:
                yield {
                    "type": "error",
                    "message": str(e),
                }

        job_manager.start_job(
            job_id, run, on_complete=on_complete,
        )
        return jsonify({"job_id": job_id}), 202

    if tool_name not in TOOL_DISPATCH:
        return jsonify({
            "error": f"Unknown tool: {tool_name}",
        }), 400
    try:
        agent = ReportAgent()
        result = agent.execute_tool(tool_name, tool_args)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@agents_bp.route("/validation/step", methods=["POST"])
@token_required
def agents_validation_step() -> tuple[Response, int]:
    """
    Start a ValidationAgent step as a background job.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    system_description = body.get("system_description", "")
    incident_report = body.get("incident_report", "")
    response_plan = body.get("response_plan", "")
    specification = body.get("specification", "")
    conversation_history = body.get("conversation_history", [])
    images = body.get("images", [])
    model_name = body.get("model_name") or None
    planner_report = body.get("planner_report")
    code_report = body.get("code_report")
    planner_report_id = body.get("planner_report_id")
    if isinstance(planner_report, str):
        try:
            planner_report = json.loads(planner_report)
        except (json.JSONDecodeError, ValueError):
            planner_report = {}
    if isinstance(code_report, str):
        try:
            code_report = json.loads(code_report)
        except (json.JSONDecodeError, ValueError):
            code_report = {}
    if not isinstance(images, list):
        images = []
    if not system_description and not incident_report:
        return jsonify({
            "error": (
                "system_description or incident_report "
                "is required"
            ),
        }), 400
    if not specification:
        specification = json.dumps(
            DIGITAL_TWIN.DEFAULT_CONFIG[
                "specification_commands"
            ],
            indent=2,
        )
    session_id = body.get("session_id")
    username = g.username
    job_id = (
        str(session_id) if session_id
        else body.get("job_id") or str(uuid.uuid4())
    )
    last_prompt_tokens = body.get(
        "last_prompt_tokens", 0,
    )
    compaction_model = body.get(
        "compaction_model",
    ) or None
    compaction_threshold = body.get(
        "compaction_threshold", 0.8,
    )

    def on_complete(
        events: list[dict[str, Any]],
    ) -> None:
        """
        Auto-save step results to the planning session.

        :param events: the accumulated job events
        """
        if not session_id:
            return
        _save_step_result(
            session_id, username, events,
        )

    def run() -> Generator[
        dict[str, Any], None, None
    ]:
        """
        Run the ValidationAgent step in background.

        :return: a generator of event dicts
        """
        try:
            dt_enabled = body.get(
                "dt_enabled", True,
            )
            if (
                not conversation_history
                and dt_enabled
            ):
                yield from _redeploy_dt(job_id)
                yield from _start_sandbox()

            has_policy = False
            if (
                not conversation_history
                and planner_report_id
            ):
                try:
                    policy_bytes = (
                        DatabaseFacade.get_policy_data(
                            planner_report_id,
                        )
                    )
                    if policy_bytes:
                        yield {
                            "type": "dt_progress",
                            "message": (
                                "Loading RL policy "
                                "into sandbox..."
                            ),
                        }
                        _install_policy_in_sandbox(
                            policy_bytes,
                            code_report or {},
                        )
                        has_policy = True
                        yield {
                            "type": "policy_loaded",
                            "message": "Policy loaded",
                        }
                except Exception as e:
                    logger.warning(
                        "Failed to load policy: %s",
                        e, exc_info=True,
                    )
                    yield {
                        "type": "error",
                        "message": (
                            "Failed to load policy: "
                            f"{e}"
                        ),
                    }

            dt_config = (
                DatabaseFacade.get_digital_twin_config()
                or DIGITAL_TWIN.DEFAULT_CONFIG
            )
            agent = ValidationAgent()
            agent._last_prompt_tokens = (
                last_prompt_tokens
            )
            yield from agent.step_stream(
                system_description=system_description,
                incident_report=incident_report,
                response_plan=response_plan,
                specification=specification,
                planner_report=planner_report or {},
                code_report=code_report or {},
                conversation_history=(
                    conversation_history
                ),
                images=images,
                model_name=model_name,
                has_policy=has_policy,
                dt_config=dt_config,
                compaction_model=compaction_model,
                compaction_threshold=(
                    compaction_threshold
                ),
                dt_enabled=dt_enabled,
            )
        except Exception as e:
            yield _make_error_event(e)

    job_manager.start_job(
        job_id, run, on_complete=on_complete,
    )
    return jsonify({"job_id": job_id}), 202


@agents_bp.route("/validation/prompt", methods=["POST"])
@token_required
def agents_validation_prompt() -> tuple[Response, int]:
    """
    Render the ValidationAgent system prompt from the given context.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    specification = body.get("specification", "")
    if not specification:
        specification = json.dumps(
            DIGITAL_TWIN.DEFAULT_CONFIG[
                "specification_commands"
            ],
            indent=2,
        )
    planner_report = body.get("planner_report")
    code_report = body.get("code_report")
    if isinstance(planner_report, str):
        try:
            planner_report = json.loads(planner_report)
        except (json.JSONDecodeError, ValueError):
            planner_report = {}
    if isinstance(code_report, str):
        try:
            code_report = json.loads(code_report)
        except (json.JSONDecodeError, ValueError):
            code_report = {}
    dt_config = (
        DatabaseFacade.get_digital_twin_config()
        or DIGITAL_TWIN.DEFAULT_CONFIG
    )
    prompt = build_validation_prompt(
        has_policy=False,
        system_description=body.get(
            "system_description", "",
        ) or "N/A",
        incident_report=body.get(
            "incident_report", "",
        ) or "N/A",
        response_plan=body.get(
            "response_plan", "",
        ) or "N/A",
        specification=specification or "N/A",
        planner_report_formatted=(
            ValidationAgent._format_planner_report(
                planner_report or {},
            )
        ),
        code_report_formatted=(
            ValidationAgent._format_code_report(
                code_report or {},
            )
        ),
        validation_feedback="",
        dt_container_list=format_container_list(
            dt_config,
        ),
        dt_container_table=format_container_table(
            dt_config,
        ),
        dt_network_connectivity=(
            format_network_connectivity(dt_config)
        ),
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route("/validation/tool", methods=["POST"])
@token_required
def agents_validation_tool() -> tuple[Response, int]:
    """
    Execute an approved tool call for ValidationAgent.

    Streaming tools run as background jobs; other tools
    return a single JSON response.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    tool_name = body.get("tool_name", "")
    tool_args = body.get("tool_args", {})
    incident_id = body.get("incident_id")
    if not tool_name:
        return jsonify({"error": "tool_name is required"}), 400
    if tool_name in _DT_TOOLS and incident_id is not None:
        tool_args["incident_id"] = incident_id

    if tool_name == "run_action_validators":
        tool_args["context"] = {
            "system_description": body.get(
                "system_description", "",
            ),
            "operator_feedback": body.get(
                "operator_feedback", "",
            ),
            "images": body.get("images"),
            "dt_config": (
                DatabaseFacade.get_digital_twin_config()
                or DIGITAL_TWIN.DEFAULT_CONFIG
            ),
            "incident_id": incident_id,
            "action_validator_model": body.get(
                "action_validator_model",
            ),
        }

    if tool_name in VALIDATION_STREAMING_DISPATCH:
        session_id = body.get("session_id")
        username = g.username
        job_id = (
            str(session_id) if session_id
            else body.get("job_id")
            or str(uuid.uuid4())
        )

        def on_complete(
            events: list[dict[str, Any]],
        ) -> None:
            """
            Auto-save tool results to session.

            :param events: the accumulated job events
            """
            if not session_id:
                return
            _save_tool_result(
                session_id, username,
                events, tool_name,
            )

        def run() -> Generator[
            dict[str, Any], None, None
        ]:
            """
            Run the streaming tool in background.

            :return: a generator of event dicts
            """
            try:
                agent = ValidationAgent()
                yield from agent.execute_tool_stream(
                    tool_name, tool_args,
                )
            except Exception as e:
                yield {
                    "type": "error",
                    "message": str(e),
                }

        job_manager.start_job(
            job_id, run, on_complete=on_complete,
        )
        return jsonify({"job_id": job_id}), 202

    if tool_name not in VALIDATION_TOOL_DISPATCH:
        return jsonify({
            "error": f"Unknown tool: {tool_name}",
        }), 400
    try:
        agent = ValidationAgent()
        result = agent.execute_tool(tool_name, tool_args)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@agents_bp.route("/code/step", methods=["POST"])
@token_required
def agents_code_step() -> tuple[Response, int]:
    """
    Start a CodeAgent step as a background job.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    system_description = body.get("system_description", "")
    incident_report = body.get("incident_report", "")
    specification = body.get("specification", "")
    operator_feedback = body.get("operator_feedback", "")
    conversation_history = body.get("conversation_history", [])
    images = body.get("images", [])
    model_name = body.get("model_name") or None
    if not isinstance(images, list):
        images = []
    if not system_description and not incident_report:
        return jsonify({
            "error": (
                "system_description or incident_report "
                "is required"
            ),
        }), 400
    if not specification:
        specification = json.dumps(
            DIGITAL_TWIN.DEFAULT_CONFIG[
                "specification_commands"
            ],
            indent=2,
        )
    session_id = body.get("session_id")
    username = g.username
    job_id = (
        str(session_id) if session_id
        else body.get("job_id") or str(uuid.uuid4())
    )
    last_prompt_tokens = body.get(
        "last_prompt_tokens", 0,
    )
    compaction_model = body.get(
        "compaction_model",
    ) or None
    compaction_threshold = body.get(
        "compaction_threshold", 0.8,
    )

    def on_complete(
        events: list[dict[str, Any]],
    ) -> None:
        """
        Auto-save step results to the planning session.

        :param events: the accumulated job events
        """
        if not session_id:
            return
        _save_step_result(
            session_id, username, events,
        )

    def run() -> Generator[
        dict[str, Any], None, None
    ]:
        """
        Run the CodeAgent step in background.

        :return: a generator of event dicts
        """
        try:
            dt_enabled = body.get(
                "dt_enabled", True,
            )
            if (
                not conversation_history
                and dt_enabled
            ):
                yield from _redeploy_dt(job_id)
                yield from _start_sandbox()
            dt_config = (
                DatabaseFacade.get_digital_twin_config()
                or DIGITAL_TWIN.DEFAULT_CONFIG
            )
            agent = CodeAgent()
            agent._last_prompt_tokens = (
                last_prompt_tokens
            )
            yield from agent.step_stream(
                system_description=system_description,
                incident_report=incident_report,
                specification=specification,
                operator_feedback=operator_feedback,
                conversation_history=conversation_history,
                images=images,
                model_name=model_name,
                dt_config=dt_config,
                compaction_model=compaction_model,
                compaction_threshold=compaction_threshold,
                dt_enabled=dt_enabled,
            )
        except Exception as e:
            yield _make_error_event(e)

    job_manager.start_job(
        job_id, run, on_complete=on_complete,
    )
    return jsonify({"job_id": job_id}), 202


@agents_bp.route("/code/prompt", methods=["POST"])
@token_required
def agents_code_prompt() -> tuple[Response, int]:
    """
    Render the CodeAgent system prompt from the given context.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    specification = body.get("specification", "")
    if not specification:
        specification = json.dumps(
            DIGITAL_TWIN.DEFAULT_CONFIG[
                "specification_commands"
            ],
            indent=2,
        )
    dt_config = (
        DatabaseFacade.get_digital_twin_config()
        or DIGITAL_TWIN.DEFAULT_CONFIG
    )
    prompt = CODE_PROMPT_TEMPLATE.format(
        system_description=body.get(
            "system_description", "",
        ) or "N/A",
        incident_report=body.get(
            "incident_report", "",
        ) or "N/A",
        specification=specification or "N/A",
        operator_feedback=body.get(
            "operator_feedback", "",
        ) or "N/A",
        dt_container_list=format_container_list(
            dt_config,
        ),
        revision_notice="",
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route("/code/tool", methods=["POST"])
@token_required
def agents_code_tool() -> tuple[Response, int]:
    """
    Execute an approved tool call for the CodeAgent.

    Streaming tools run as background jobs; other tools
    return a single JSON response.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    tool_name = body.get("tool_name", "")
    tool_args = body.get("tool_args", {})
    incident_id = body.get("incident_id")
    if not tool_name:
        return jsonify({"error": "tool_name is required"}), 400
    if tool_name in _DT_TOOLS and incident_id is not None:
        tool_args["incident_id"] = incident_id

    if tool_name in CODE_STREAMING_DISPATCH:
        session_id = body.get("session_id")
        username = g.username
        job_id = (
            str(session_id) if session_id
            else body.get("job_id")
            or str(uuid.uuid4())
        )

        def on_complete(
            events: list[dict[str, Any]],
        ) -> None:
            """
            Auto-save tool results to session.

            :param events: the accumulated job events
            """
            if not session_id:
                return
            _save_tool_result(
                session_id, username,
                events, tool_name,
            )

        def run() -> Generator[
            dict[str, Any], None, None
        ]:
            """
            Run the streaming tool in background.

            :return: a generator of event dicts
            """
            try:
                agent = CodeAgent()
                yield from agent.execute_tool_stream(
                    tool_name, tool_args,
                )
            except Exception as e:
                yield {
                    "type": "error",
                    "message": str(e),
                }

        job_manager.start_job(
            job_id, run, on_complete=on_complete,
        )
        return jsonify({"job_id": job_id}), 202

    if tool_name not in CODE_TOOL_DISPATCH:
        return jsonify({
            "error": f"Unknown tool: {tool_name}",
        }), 400
    try:
        agent = CodeAgent()
        result = agent.execute_tool(tool_name, tool_args)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@agents_bp.route("/code-review/step", methods=["POST"])
@token_required
def agents_code_review_step() -> tuple[Response, int]:
    """
    Start a CodeReviewerAgent step as a background job.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    system_description = body.get("system_description", "")
    incident_report = body.get("incident_report", "")
    specification = body.get("specification", "")
    operator_feedback = body.get("operator_feedback", "")
    code_report = body.get("code_report")
    conversation_history = body.get("conversation_history", [])
    images = body.get("images", [])
    model_name = body.get("model_name") or None
    if not isinstance(images, list):
        images = []
    if not code_report:
        return jsonify({
            "error": "code_report is required",
        }), 400
    if isinstance(code_report, str):
        try:
            code_report = json.loads(code_report)
        except (json.JSONDecodeError, ValueError):
            return jsonify({
                "error": "code_report must be valid JSON",
            }), 400
    if not specification:
        specification = json.dumps(
            DIGITAL_TWIN.DEFAULT_CONFIG[
                "specification_commands"
            ],
            indent=2,
        )
    session_id = body.get("session_id")
    username = g.username
    job_id = (
        str(session_id) if session_id
        else body.get("job_id") or str(uuid.uuid4())
    )
    last_prompt_tokens = body.get(
        "last_prompt_tokens", 0,
    )
    compaction_model = body.get(
        "compaction_model",
    ) or None
    compaction_threshold = body.get(
        "compaction_threshold", 0.8,
    )

    def on_complete(
        events: list[dict[str, Any]],
    ) -> None:
        """
        Auto-save step results to the planning session.

        :param events: the accumulated job events
        """
        if not session_id:
            return
        _save_step_result(
            session_id, username, events,
        )

    def run() -> Generator[
        dict[str, Any], None, None
    ]:
        """
        Run the CodeReviewerAgent step in background.

        :return: a generator of event dicts
        """
        try:
            dt_enabled = body.get(
                "dt_enabled", True,
            )
            if (
                not conversation_history
                and dt_enabled
            ):
                yield from _redeploy_dt(job_id)
                yield from _start_sandbox()
            dt_config = (
                DatabaseFacade.get_digital_twin_config()
                or DIGITAL_TWIN.DEFAULT_CONFIG
            )
            agent = CodeReviewerAgent()
            agent._last_prompt_tokens = (
                last_prompt_tokens
            )
            yield from agent.step_stream(
                system_description=system_description,
                incident_report=incident_report,
                specification=specification,
                operator_feedback=operator_feedback,
                code_report=code_report,
                conversation_history=conversation_history,
                images=images,
                model_name=model_name,
                dt_config=dt_config,
                compaction_model=compaction_model,
                compaction_threshold=compaction_threshold,
                dt_enabled=dt_enabled,
            )
        except Exception as e:
            yield _make_error_event(e)

    job_manager.start_job(
        job_id, run, on_complete=on_complete,
    )
    return jsonify({"job_id": job_id}), 202


@agents_bp.route("/code-review/prompt", methods=["POST"])
@token_required
def agents_code_review_prompt() -> tuple[Response, int]:
    """
    Render the CodeReviewerAgent system prompt from the given context.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    specification = body.get("specification", "")
    if not specification:
        specification = json.dumps(
            DIGITAL_TWIN.DEFAULT_CONFIG[
                "specification_commands"
            ],
            indent=2,
        )
    code_report = body.get("code_report")
    if isinstance(code_report, str):
        try:
            code_report = json.loads(code_report)
        except (json.JSONDecodeError, ValueError):
            code_report = {}
    formatted_report = (
        CodeReviewerAgent._format_code_report(
            code_report or {},
        )
    )
    dt_config = (
        DatabaseFacade.get_digital_twin_config()
        or DIGITAL_TWIN.DEFAULT_CONFIG
    )
    prompt = CODE_REVIEW_PROMPT_TEMPLATE.format(
        system_description=body.get(
            "system_description", "",
        ) or "N/A",
        incident_report=body.get(
            "incident_report", "",
        ) or "N/A",
        specification=specification or "N/A",
        operator_feedback=body.get(
            "operator_feedback", "",
        ) or "N/A",
        code_report_formatted=formatted_report,
        dt_container_list=format_container_list(
            dt_config,
        ),
        review_iteration_note="",
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route("/code-review/tool", methods=["POST"])
@token_required
def agents_code_review_tool() -> tuple[Response, int]:
    """
    Execute an approved tool call for CodeReviewerAgent.

    Streaming tools run as background jobs; other tools
    return a single JSON response.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    tool_name = body.get("tool_name", "")
    tool_args = body.get("tool_args", {})
    incident_id = body.get("incident_id")
    if not tool_name:
        return jsonify({"error": "tool_name is required"}), 400
    if tool_name in _DT_TOOLS and incident_id is not None:
        tool_args["incident_id"] = incident_id

    if tool_name in CODE_REVIEW_STREAMING_DISPATCH:
        session_id = body.get("session_id")
        username = g.username
        job_id = (
            str(session_id) if session_id
            else body.get("job_id")
            or str(uuid.uuid4())
        )

        def on_complete(
            events: list[dict[str, Any]],
        ) -> None:
            """
            Auto-save tool results to session.

            :param events: the accumulated job events
            """
            if not session_id:
                return
            _save_tool_result(
                session_id, username,
                events, tool_name,
            )

        def run() -> Generator[
            dict[str, Any], None, None
        ]:
            """
            Run the streaming tool in background.

            :return: a generator of event dicts
            """
            try:
                agent = CodeReviewerAgent()
                yield from agent.execute_tool_stream(
                    tool_name, tool_args,
                )
            except Exception as e:
                yield {
                    "type": "error",
                    "message": str(e),
                }

        job_manager.start_job(
            job_id, run, on_complete=on_complete,
        )
        return jsonify({"job_id": job_id}), 202

    if tool_name not in CODE_REVIEW_TOOL_DISPATCH:
        return jsonify({
            "error": f"Unknown tool: {tool_name}",
        }), 400
    try:
        agent = CodeReviewerAgent()
        result = agent.execute_tool(tool_name, tool_args)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@agents_bp.route(
    "/report-review/step", methods=["POST"],
)
@token_required
def agents_report_review_step() -> (
    tuple[Response, int]
):
    """
    Start a ReportReviewerAgent step as a background job.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    system_description = body.get(
        "system_description", "",
    )
    security_alerts = body.get("security_alerts", "")
    operator_feedback = body.get(
        "operator_feedback", "",
    )
    incident_report = body.get("incident_report")
    conversation_history = body.get(
        "conversation_history", [],
    )
    images = body.get("images", [])
    model_name = body.get("model_name") or None
    if not isinstance(images, list):
        images = []
    if not incident_report:
        return jsonify({
            "error": "incident_report is required",
        }), 400
    if isinstance(incident_report, str):
        try:
            incident_report = json.loads(
                incident_report,
            )
        except (json.JSONDecodeError, ValueError):
            return jsonify({
                "error": (
                    "incident_report must be valid JSON"
                ),
            }), 400
    session_id = body.get("session_id")
    username = g.username
    job_id = (
        str(session_id) if session_id
        else body.get("job_id") or str(uuid.uuid4())
    )
    last_prompt_tokens = body.get(
        "last_prompt_tokens", 0,
    )
    compaction_model = body.get(
        "compaction_model",
    ) or None
    compaction_threshold = body.get(
        "compaction_threshold", 0.8,
    )

    def on_complete(
        events: list[dict[str, Any]],
    ) -> None:
        """
        Auto-save step results to the planning session.

        :param events: the accumulated job events
        """
        if not session_id:
            return
        _save_step_result(
            session_id, username, events,
        )

    def run() -> Generator[
        dict[str, Any], None, None
    ]:
        """
        Run the ReportReviewerAgent step in background.

        :return: a generator of event dicts
        """
        try:
            dt_enabled = body.get(
                "dt_enabled", True,
            )
            info_tools_enabled = body.get(
                "info_tools_enabled", True,
            )
            if (
                not conversation_history
                and dt_enabled
            ):
                yield from _redeploy_dt(job_id)
            dt_config = (
                DatabaseFacade.get_digital_twin_config()
                or DIGITAL_TWIN.DEFAULT_CONFIG
            )
            agent = ReportReviewerAgent()
            agent._last_prompt_tokens = (
                last_prompt_tokens
            )
            yield from agent.step_stream(
                system_description=(
                    system_description
                ),
                security_alerts=security_alerts,
                operator_feedback=(
                    operator_feedback
                ),
                incident_report=incident_report,
                conversation_history=(
                    conversation_history
                ),
                images=images,
                model_name=model_name,
                dt_config=dt_config,
                compaction_model=compaction_model,
                compaction_threshold=(
                    compaction_threshold
                ),
                dt_enabled=dt_enabled,
                info_tools_enabled=(
                    info_tools_enabled
                ),
            )
        except Exception as e:
            yield {
                "type": "error",
                "message": str(e),
            }

    job_manager.start_job(
        job_id, run, on_complete=on_complete,
    )
    return jsonify({"job_id": job_id}), 202


@agents_bp.route(
    "/report-review/prompt", methods=["POST"],
)
@token_required
def agents_report_review_prompt() -> (
    tuple[Response, int]
):
    """
    Render the ReportReviewerAgent system prompt.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    incident_report = body.get("incident_report")
    if isinstance(incident_report, str):
        try:
            incident_report = json.loads(
                incident_report,
            )
        except (json.JSONDecodeError, ValueError):
            incident_report = {}
    formatted_report = (
        ReportReviewerAgent._format_incident_report(
            incident_report or {},
        )
    )
    dt_config = (
        DatabaseFacade.get_digital_twin_config()
        or DIGITAL_TWIN.DEFAULT_CONFIG
    )
    prompt = REPORT_REVIEW_PROMPT_TEMPLATE.format(
        system_description=body.get(
            "system_description", "",
        ) or "N/A",
        security_alerts=body.get(
            "security_alerts", "",
        ) or "N/A",
        operator_feedback=body.get(
            "operator_feedback", "",
        ) or "N/A",
        incident_report_formatted=formatted_report,
        dt_container_list=format_container_list(
            dt_config,
        ),
        dt_container_table=format_container_table(
            dt_config,
        ),
        dt_network_connectivity=(
            format_network_connectivity(dt_config)
        ),
        review_iteration_note="",
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route(
    "/report-review/tool", methods=["POST"],
)
@token_required
def agents_report_review_tool() -> (
    tuple[Response, int]
):
    """
    Execute an approved tool call for ReportReviewerAgent.

    Streaming tools run as background jobs; other tools
    return a single JSON response.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    tool_name = body.get("tool_name", "")
    tool_args = body.get("tool_args", {})
    incident_id = body.get("incident_id")
    if not tool_name:
        return jsonify({
            "error": "tool_name is required",
        }), 400
    if tool_name in _DT_TOOLS and (
        incident_id is not None
    ):
        tool_args["incident_id"] = incident_id

    if tool_name in REPORT_REVIEW_STREAMING_DISPATCH:
        session_id = body.get("session_id")
        username = g.username
        job_id = (
            str(session_id) if session_id
            else body.get("job_id")
            or str(uuid.uuid4())
        )

        def on_complete(
            events: list[dict[str, Any]],
        ) -> None:
            """
            Auto-save tool results to session.

            :param events: the accumulated job events
            """
            if not session_id:
                return
            _save_tool_result(
                session_id, username,
                events, tool_name,
            )

        def run() -> Generator[
            dict[str, Any], None, None
        ]:
            """
            Run the streaming tool in background.

            :return: a generator of event dicts
            """
            try:
                agent = ReportReviewerAgent()
                yield from (
                    agent.execute_tool_stream(
                        tool_name, tool_args,
                    )
                )
            except Exception as e:
                yield {
                    "type": "error",
                    "message": str(e),
                }

        job_manager.start_job(
            job_id, run, on_complete=on_complete,
        )
        return jsonify({"job_id": job_id}), 202

    if tool_name not in REPORT_REVIEW_TOOL_DISPATCH:
        return jsonify({
            "error": f"Unknown tool: {tool_name}",
        }), 400
    try:
        agent = ReportReviewerAgent()
        result = agent.execute_tool(
            tool_name, tool_args,
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@agents_bp.route(
    "/report-manager/step", methods=["POST"],
)
@token_required
def agents_report_manager_step() -> (
    tuple[Response, int]
):
    """
    Start a ReportManagerAgent step as a background job.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    system_description = body.get(
        "system_description", "",
    )
    security_alerts = body.get("security_alerts", "")
    operator_feedback = body.get(
        "operator_feedback", "",
    )
    conversation_history = body.get(
        "conversation_history", [],
    )
    images = body.get("images", [])
    model_name = body.get("model_name") or None
    max_iterations = body.get("max_iterations", 2)
    if not isinstance(images, list):
        images = []
    if not system_description and not security_alerts:
        return jsonify({
            "error": (
                "system_description or "
                "security_alerts is required"
            ),
        }), 400
    session_id = body.get("session_id")
    username = g.username
    job_id = (
        str(session_id) if session_id
        else body.get("job_id") or str(uuid.uuid4())
    )
    last_prompt_tokens = body.get(
        "last_prompt_tokens", 0,
    )
    compaction_model = body.get(
        "compaction_model",
    ) or None
    compaction_threshold = body.get(
        "compaction_threshold", 0.8,
    )

    def on_complete(
        events: list[dict[str, Any]],
    ) -> None:
        """
        Auto-save step results to the planning session.

        :param events: the accumulated job events
        """
        if not session_id:
            return
        _save_step_result(
            session_id, username, events,
        )

    def run() -> Generator[
        dict[str, Any], None, None
    ]:
        """
        Run the ReportManagerAgent step in background.

        :return: a generator of event dicts
        """
        try:
            if not conversation_history:
                yield from _redeploy_dt(job_id)
            agent = ReportManagerAgent()
            agent._last_prompt_tokens = (
                last_prompt_tokens
            )
            yield from agent.step_stream(
                system_description=system_description,
                security_alerts=security_alerts,
                operator_feedback=operator_feedback,
                conversation_history=(
                    conversation_history
                ),
                images=images,
                model_name=model_name,
                max_iterations=max_iterations,
                compaction_model=compaction_model,
                compaction_threshold=(
                    compaction_threshold
                ),
            )
        except Exception as e:
            yield {
                "type": "error",
                "message": str(e),
            }

    job_manager.start_job(
        job_id, run, on_complete=on_complete,
    )
    return jsonify({"job_id": job_id}), 202


@agents_bp.route(
    "/report-manager/prompt", methods=["POST"],
)
@token_required
def agents_report_manager_prompt() -> (
    tuple[Response, int]
):
    """
    Render the ReportManagerAgent system prompt.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    max_iterations = body.get("max_iterations", 2)
    prompt = REPORT_MANAGER_PROMPT_TEMPLATE.format(
        system_description=body.get(
            "system_description", "",
        ) or "N/A",
        security_alerts=body.get(
            "security_alerts", "",
        ) or "N/A",
        operator_feedback=body.get(
            "operator_feedback", "",
        ) or "N/A",
        max_iterations=max_iterations,
        validation_feedback="N/A",
        revision_notice="",
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route(
    "/report-manager/tool", methods=["POST"],
)
@token_required
def agents_report_manager_tool() -> (
    Response | tuple[Response, int]
):
    """
    Execute an approved tool call for ReportManagerAgent.

    Sub-agent tools (run_report_agent,
    run_report_reviewer_agent) are streaming and require
    system context from the request body.

    :return: a streaming Response or (JSON, status) tuple
    """
    body = request.get_json(silent=True) or {}
    tool_name = body.get("tool_name", "")
    tool_args = body.get("tool_args", {})
    incident_id = body.get("incident_id")
    if not tool_name:
        return jsonify({
            "error": "tool_name is required",
        }), 400
    if tool_name in _DT_TOOLS and (
        incident_id is not None
    ):
        tool_args["incident_id"] = incident_id

    if tool_name in REPORT_MANAGER_STREAMING_DISPATCH:
        context: dict[str, Any] = {
            "system_description": body.get(
                "system_description", "",
            ),
            "security_alerts": body.get(
                "security_alerts", "",
            ),
            "operator_feedback": body.get(
                "operator_feedback", "",
            ),
            "images": body.get("images"),
            "report_agent_model": body.get(
                "report_agent_model",
            ),
            "reviewer_agent_model": body.get(
                "reviewer_agent_model",
            ),
            "username": g.username,
            "incident_id": incident_id,
            "dt_config": (
                DatabaseFacade.get_digital_twin_config()
                or DIGITAL_TWIN.DEFAULT_CONFIG
            ),
            "compaction_model": body.get(
                "compaction_model",
            ),
            "compaction_threshold": body.get(
                "compaction_threshold", 0.8,
            ),
            "info_tools_enabled": body.get(
                "info_tools_enabled", True,
            ),
        }
        if tool_name == (
            "run_report_reviewer_agent"
        ):
            last_assessment: dict[str, Any] = (
                body.get("last_assessment") or {}
            )
            if not last_assessment:
                conv_history = body.get(
                    "conversation_history", [],
                )
                for entry in reversed(conv_history):
                    if (
                        entry.get("type")
                        == "tool_result"
                        and entry.get("tool_name")
                        == "run_report_agent"
                    ):
                        result = entry.get(
                            "result", {},
                        )
                        last_assessment = (
                            result.get(
                                "assessment", {},
                            )
                        )
                        break
            if not last_assessment:
                logger.warning(
                    "No assessment found for "
                    "reviewer; body keys=%s, "
                    "conv_history len=%d, "
                    "conv_history types=%s",
                    list(body.keys()),
                    len(
                        body.get(
                            "conversation_history",
                            [],
                        )
                    ),
                    [
                        (
                            e.get("type"),
                            e.get("tool_name"),
                        )
                        for e in body.get(
                            "conversation_history",
                            [],
                        )
                    ],
                )
            context["last_assessment"] = (
                last_assessment
            )

        session_id = body.get("session_id")
        username = g.username
        job_id = (
            str(session_id) if session_id
            else body.get("job_id")
            or str(uuid.uuid4())
        )

        def on_complete(
            events: list[dict[str, Any]],
        ) -> None:
            """
            Auto-save tool results to session.

            :param events: the accumulated job events
            """
            if not session_id:
                return
            _save_tool_result(
                session_id, username,
                events, tool_name,
            )

        def run() -> Generator[
            dict[str, Any], None, None
        ]:
            """
            Run the streaming tool in background.

            :return: a generator of event dicts
            """
            try:
                agent = ReportManagerAgent()
                yield from (
                    agent.execute_tool_stream(
                        tool_name, tool_args,
                        context=context,
                    )
                )
            except Exception as e:
                yield {
                    "type": "error",
                    "message": str(e),
                }

        job_manager.start_job(
            job_id, run, on_complete=on_complete,
        )
        return jsonify({"job_id": job_id}), 202

    if tool_name not in REPORT_MANAGER_TOOL_DISPATCH:
        return jsonify({
            "error": f"Unknown tool: {tool_name}",
        }), 400
    try:
        agent = ReportManagerAgent()
        result = agent.execute_tool(
            tool_name, tool_args,
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@agents_bp.route("/code-manager/step", methods=["POST"])
@token_required
def agents_code_manager_step() -> (
    tuple[Response, int]
):
    """
    Start a CodeManagerAgent step as a background job.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    system_description = body.get(
        "system_description", "",
    )
    incident_report = body.get("incident_report", "")
    specification = body.get("specification", "")
    operator_feedback = body.get("operator_feedback", "")
    conversation_history = body.get(
        "conversation_history", [],
    )
    images = body.get("images", [])
    model_name = body.get("model_name") or None
    max_iterations = body.get("max_iterations", 2)
    if not isinstance(images, list):
        images = []
    if not system_description and not incident_report:
        return jsonify({
            "error": (
                "system_description or incident_report "
                "is required"
            ),
        }), 400
    if not specification:
        specification = json.dumps(
            DIGITAL_TWIN.DEFAULT_CONFIG[
                "specification_commands"
            ],
            indent=2,
        )
    session_id = body.get("session_id")
    username = g.username
    job_id = (
        str(session_id) if session_id
        else body.get("job_id") or str(uuid.uuid4())
    )
    last_prompt_tokens = body.get(
        "last_prompt_tokens", 0,
    )
    compaction_model = body.get(
        "compaction_model",
    ) or None
    compaction_threshold = body.get(
        "compaction_threshold", 0.8,
    )
    code_reviewer_enabled = body.get(
        "code_reviewer_enabled", True,
    )

    def on_complete(
        events: list[dict[str, Any]],
    ) -> None:
        """
        Auto-save step results to the planning session.

        :param events: the accumulated job events
        """
        if not session_id:
            return
        _save_step_result(
            session_id, username, events,
        )

    def run() -> Generator[
        dict[str, Any], None, None
    ]:
        """
        Run the CodeManagerAgent step in background.

        :return: a generator of event dicts
        """
        try:
            if not conversation_history:
                yield from _redeploy_dt(job_id)
            agent = CodeManagerAgent()
            agent._last_prompt_tokens = (
                last_prompt_tokens
            )
            yield from agent.step_stream(
                system_description=system_description,
                incident_report=incident_report,
                specification=specification,
                operator_feedback=operator_feedback,
                conversation_history=(
                    conversation_history
                ),
                images=images,
                model_name=model_name,
                max_iterations=max_iterations,
                compaction_model=compaction_model,
                compaction_threshold=(
                    compaction_threshold
                ),
                code_reviewer_enabled=(
                    code_reviewer_enabled
                ),
            )
        except Exception as e:
            yield _make_error_event(e)

    job_manager.start_job(
        job_id, run, on_complete=on_complete,
    )
    return jsonify({"job_id": job_id}), 202


@agents_bp.route("/code-manager/prompt", methods=["POST"])
@token_required
def agents_code_manager_prompt() -> tuple[Response, int]:
    """
    Render the CodeManagerAgent system prompt.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    specification = body.get("specification", "")
    max_iterations = body.get("max_iterations", 2)
    if not specification:
        specification = json.dumps(
            DIGITAL_TWIN.DEFAULT_CONFIG[
                "specification_commands"
            ],
            indent=2,
        )
    prompt = CODE_MANAGER_PROMPT_TEMPLATE.format(
        system_description=body.get(
            "system_description", "",
        ) or "N/A",
        incident_report=body.get(
            "incident_report", "",
        ) or "N/A",
        specification=specification or "N/A",
        operator_feedback=body.get(
            "operator_feedback", "",
        ) or "N/A",
        max_iterations=max_iterations,
        validation_feedback="N/A",
        revision_notice="",
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route("/code-manager/tool", methods=["POST"])
@token_required
def agents_code_manager_tool() -> (
    Response | tuple[Response, int]
):
    """
    Execute an approved tool call for CodeManagerAgent.

    Sub-agent tools (run_code_agent, run_code_reviewer_agent)
    are streaming and require system context from the request
    body. For other tools, returns a single JSON response.

    :return: a streaming Response or (JSON, status) tuple
    """
    body = request.get_json(silent=True) or {}
    tool_name = body.get("tool_name", "")
    tool_args = body.get("tool_args", {})
    incident_id = body.get("incident_id")
    if not tool_name:
        return jsonify({
            "error": "tool_name is required",
        }), 400
    if tool_name in _DT_TOOLS and incident_id is not None:
        tool_args["incident_id"] = incident_id

    if tool_name in CODE_MANAGER_STREAMING_DISPATCH:
        context = {
            "system_description": body.get(
                "system_description", "",
            ),
            "incident_report": body.get(
                "incident_report", "",
            ),
            "specification": body.get(
                "specification", "",
            ),
            "operator_feedback": body.get(
                "operator_feedback", "",
            ),
            "images": body.get("images"),
            "code_agent_model": body.get(
                "code_agent_model",
            ),
            "reviewer_agent_model": body.get(
                "reviewer_agent_model",
            ),
            "username": g.username,
            "incident_id": incident_id,
            "dt_config": (
                DatabaseFacade.get_digital_twin_config()
                or DIGITAL_TWIN.DEFAULT_CONFIG
            ),
            "compaction_model": body.get(
                "compaction_model",
            ),
            "compaction_threshold": body.get(
                "compaction_threshold", 0.8,
            ),
            "code_reviewer_enabled": body.get(
                "code_reviewer_enabled", True,
            ),
        }
        if tool_name == "run_code_reviewer_agent":
            conv_history = body.get(
                "conversation_history", [],
            )
            last_code_report: dict[str, Any] = {}
            for entry in reversed(conv_history):
                if (
                    entry.get("type") == "tool_result"
                    and entry.get("tool_name")
                    == "run_code_agent"
                ):
                    result = entry.get("result", {})
                    last_code_report = result.get(
                        "code_report", {},
                    )
                    break
            context["last_code_report"] = last_code_report

        session_id = body.get("session_id")
        username = g.username
        job_id = (
            str(session_id) if session_id
            else body.get("job_id")
            or str(uuid.uuid4())
        )

        def on_complete(
            events: list[dict[str, Any]],
        ) -> None:
            """
            Auto-save tool results to session.

            :param events: the accumulated job events
            """
            if not session_id:
                return
            _save_tool_result(
                session_id, username,
                events, tool_name,
            )

        def run() -> Generator[
            dict[str, Any], None, None
        ]:
            """
            Run the streaming tool in background.

            :return: a generator of event dicts
            """
            try:
                agent = CodeManagerAgent()
                yield from agent.execute_tool_stream(
                    tool_name, tool_args,
                    context=context,
                )
            except Exception as e:
                yield {
                    "type": "error",
                    "message": str(e),
                }

        job_manager.start_job(
            job_id, run, on_complete=on_complete,
        )
        return jsonify({"job_id": job_id}), 202

    if tool_name not in CODE_MANAGER_TOOL_DISPATCH:
        return jsonify({
            "error": f"Unknown tool: {tool_name}",
        }), 400
    try:
        agent = CodeManagerAgent()
        result = agent.execute_tool(tool_name, tool_args)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@agents_bp.route("/planner/step", methods=["POST"])
@token_required
def agents_planner_step() -> tuple[Response, int]:
    """
    Start a PlannerAgent step as a background job.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    system_description = body.get("system_description", "")
    incident_report = body.get("incident_report", "")
    specification = body.get("specification", "")
    operator_feedback = body.get("operator_feedback", "")
    code_report = body.get("code_report")
    conversation_history = body.get("conversation_history", [])
    images = body.get("images", [])
    model_name = body.get("model_name") or None
    time_limit_minutes = body.get("time_limit_minutes", 5)
    if not isinstance(images, list):
        images = []
    if not code_report:
        return jsonify({
            "error": "code_report is required",
        }), 400
    if isinstance(code_report, str):
        try:
            code_report = json.loads(code_report)
        except (json.JSONDecodeError, ValueError):
            return jsonify({
                "error": "code_report must be valid JSON",
            }), 400
    if not specification:
        specification = json.dumps(
            DIGITAL_TWIN.DEFAULT_CONFIG[
                "specification_commands"
            ],
            indent=2,
        )
    session_id = body.get("session_id")
    username = g.username
    job_id = (
        str(session_id) if session_id
        else body.get("job_id") or str(uuid.uuid4())
    )
    last_prompt_tokens = body.get(
        "last_prompt_tokens", 0,
    )
    compaction_model = body.get(
        "compaction_model",
    ) or None
    compaction_threshold = body.get(
        "compaction_threshold", 0.8,
    )

    def on_complete(
        events: list[dict[str, Any]],
    ) -> None:
        """
        Auto-save step results to the planning session.

        :param events: the accumulated job events
        """
        if not session_id:
            return
        _save_step_result(
            session_id, username, events,
        )

    def run() -> Generator[
        dict[str, Any], None, None
    ]:
        """
        Run the PlannerAgent step in background.

        :return: a generator of event dicts
        """
        try:
            if not conversation_history:
                yield from _start_sandbox()
                env_code = (code_report or {}).get(
                    "generated_code", "",
                )
                if env_code:
                    try:
                        _write_env_to_sandbox(env_code)
                        yield {
                            "type": "dt_progress",
                            "phase": "ready",
                            "message": (
                                "Env code written to "
                                "sandbox"
                            ),
                        }
                    except Exception as e:
                        logger.warning(
                            "Failed to pre-write env: "
                            "%s", e, exc_info=True,
                        )
                        yield {
                            "type": "error",
                            "message": (
                                "Failed to write env "
                                "code to sandbox: "
                                f"{e}"
                            ),
                        }
                        return
            agent = PlannerAgent()
            agent._last_prompt_tokens = (
                last_prompt_tokens
            )
            yield from agent.step_stream(
                system_description=system_description,
                incident_report=incident_report,
                specification=specification,
                operator_feedback=operator_feedback,
                code_report=code_report,
                conversation_history=conversation_history,
                images=images,
                model_name=model_name,
                time_limit_minutes=time_limit_minutes,
                compaction_model=compaction_model,
                compaction_threshold=compaction_threshold,
            )
        except Exception as e:
            yield _make_error_event(e)

    job_manager.start_job(
        job_id, run, on_complete=on_complete,
    )
    return jsonify({"job_id": job_id}), 202


@agents_bp.route("/planner/prompt", methods=["POST"])
@token_required
def agents_planner_prompt() -> tuple[Response, int]:
    """
    Render the PlannerAgent system prompt from the given context.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    specification = body.get("specification", "")
    if not specification:
        specification = json.dumps(
            DIGITAL_TWIN.DEFAULT_CONFIG[
                "specification_commands"
            ],
            indent=2,
        )
    code_report = body.get("code_report")
    if isinstance(code_report, str):
        try:
            code_report = json.loads(code_report)
        except (json.JSONDecodeError, ValueError):
            code_report = {}
    formatted_report = (
        PlannerAgent._format_code_report(
            code_report or {},
        )
    )
    time_limit = body.get("time_limit_minutes", 5)
    prompt = PLANNER_PROMPT_TEMPLATE.format(
        system_description=body.get(
            "system_description", "",
        ) or "N/A",
        incident_report=body.get(
            "incident_report", "",
        ) or "N/A",
        specification=specification or "N/A",
        operator_feedback=body.get(
            "operator_feedback", "",
        ) or "N/A",
        code_report_formatted=formatted_report,
        time_limit_minutes=time_limit,
        revision_context="",
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route("/planner/tool", methods=["POST"])
@token_required
def agents_planner_tool() -> tuple[Response, int]:
    """
    Execute an approved tool call for the PlannerAgent.

    Streaming tools run as background jobs; other tools
    return a single JSON response.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    tool_name = body.get("tool_name", "")
    tool_args = body.get("tool_args", {})
    if not tool_name:
        return jsonify({"error": "tool_name is required"}), 400

    if tool_name in PLANNER_STREAMING_DISPATCH:
        session_id = body.get("session_id")
        username = g.username
        job_id = (
            str(session_id) if session_id
            else body.get("job_id")
            or str(uuid.uuid4())
        )

        def on_complete(
            events: list[dict[str, Any]],
        ) -> None:
            """
            Auto-save tool results to session.

            :param events: the accumulated job events
            """
            if not session_id:
                return
            _save_tool_result(
                session_id, username,
                events, tool_name,
            )

        def run() -> Generator[
            dict[str, Any], None, None
        ]:
            """
            Run the streaming tool in background.

            :return: a generator of event dicts
            """
            try:
                agent = PlannerAgent()
                yield from agent.execute_tool_stream(
                    tool_name, tool_args,
                )
            except Exception as e:
                yield {
                    "type": "error",
                    "message": str(e),
                }

        job_manager.start_job(
            job_id, run, on_complete=on_complete,
        )
        return jsonify({"job_id": job_id}), 202

    if tool_name not in PLANNER_TOOL_DISPATCH:
        return jsonify({
            "error": f"Unknown tool: {tool_name}",
        }), 400
    try:
        agent = PlannerAgent()
        result = agent.execute_tool(tool_name, tool_args)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@agents_bp.route("/plan-manager/step", methods=["POST"])
@token_required
def agents_plan_manager_step() -> (
    tuple[Response, int]
):
    """
    Start a PlanManagerAgent step as a background job.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    system_description = body.get(
        "system_description", "",
    )
    incident_report = body.get("incident_report", "")
    specification = body.get("specification", "")
    operator_feedback = body.get("operator_feedback", "")
    conversation_history = body.get(
        "conversation_history", [],
    )
    images = body.get("images", [])
    model_name = body.get("model_name") or None
    max_iterations = body.get("max_iterations", 2)
    if not isinstance(images, list):
        images = []
    if not system_description and not incident_report:
        return jsonify({
            "error": (
                "system_description or incident_report "
                "is required"
            ),
        }), 400
    if not specification:
        specification = json.dumps(
            DIGITAL_TWIN.DEFAULT_CONFIG[
                "specification_commands"
            ],
            indent=2,
        )
    session_id = body.get("session_id")
    username = g.username
    job_id = (
        str(session_id) if session_id
        else body.get("job_id") or str(uuid.uuid4())
    )
    last_prompt_tokens = body.get(
        "last_prompt_tokens", 0,
    )
    compaction_model = body.get(
        "compaction_model",
    ) or None
    compaction_threshold = body.get(
        "compaction_threshold", 0.8,
    )
    validator_enabled = body.get(
        "validator_enabled", True,
    )
    code_model_enabled = body.get(
        "code_model_enabled", True,
    )

    def on_complete(
        events: list[dict[str, Any]],
    ) -> None:
        """
        Auto-save step results to the planning session.

        :param events: the accumulated job events
        """
        if not session_id:
            return
        _save_step_result(
            session_id, username, events,
        )

    def run() -> Generator[
        dict[str, Any], None, None
    ]:
        """
        Run the PlanManagerAgent step in background.

        :return: a generator of event dicts
        """
        try:
            if not conversation_history:
                yield from _redeploy_dt(job_id)
                yield from _start_sandbox()
            agent = PlanManagerAgent()
            agent._last_prompt_tokens = (
                last_prompt_tokens
            )
            yield from agent.step_stream(
                system_description=system_description,
                incident_report=incident_report,
                specification=specification,
                operator_feedback=operator_feedback,
                conversation_history=(
                    conversation_history
                ),
                images=images,
                model_name=model_name,
                max_iterations=max_iterations,
                compaction_model=compaction_model,
                compaction_threshold=(
                    compaction_threshold
                ),
                validator_enabled=(
                    validator_enabled
                ),
                code_model_enabled=(
                    code_model_enabled
                ),
            )
        except Exception as e:
            yield _make_error_event(e)

    job_manager.start_job(
        job_id, run, on_complete=on_complete,
    )
    return jsonify({"job_id": job_id}), 202


@agents_bp.route(
    "/plan-manager/prompt", methods=["POST"],
)
@token_required
def agents_plan_manager_prompt() -> (
    tuple[Response, int]
):
    """
    Render the PlanManagerAgent system prompt.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    specification = body.get("specification", "")
    max_iterations = body.get("max_iterations", 2)
    if not specification:
        specification = json.dumps(
            DIGITAL_TWIN.DEFAULT_CONFIG[
                "specification_commands"
            ],
            indent=2,
        )
    prompt = PLAN_MANAGER_PROMPT_TEMPLATE.format(
        system_description=body.get(
            "system_description", "",
        ) or "N/A",
        incident_report=body.get(
            "incident_report", "",
        ) or "N/A",
        specification=specification or "N/A",
        operator_feedback=body.get(
            "operator_feedback", "",
        ) or "N/A",
        max_iterations=max_iterations,
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route(
    "/plan-manager/tool", methods=["POST"],
)
@token_required
def agents_plan_manager_tool() -> (
    Response | tuple[Response, int]
):
    """
    Execute an approved tool call for PlanManagerAgent.

    Sub-agent tools (run_code_manager, run_planner_agent,
    run_validation_agent) are streaming. Builds context
    from the request body and accumulated reports in the
    conversation history.

    :return: a streaming Response or (JSON, status) tuple
    """
    body = request.get_json(silent=True) or {}
    tool_name = body.get("tool_name", "")
    tool_args = body.get("tool_args", {})
    incident_id = body.get("incident_id")
    if not tool_name:
        return jsonify({
            "error": "tool_name is required",
        }), 400

    if tool_name in PLAN_MANAGER_STREAMING_DISPATCH:
        context: dict[str, Any] = {
            "system_description": body.get(
                "system_description", "",
            ),
            "incident_report": body.get(
                "incident_report", "",
            ),
            "specification": body.get(
                "specification", "",
            ),
            "operator_feedback": body.get(
                "operator_feedback", "",
            ),
            "images": body.get("images"),
            "username": g.username,
            "incident_id": incident_id,
            "code_manager_model": body.get(
                "code_manager_model",
            ),
            "code_agent_model": body.get(
                "code_agent_model",
            ),
            "reviewer_agent_model": body.get(
                "reviewer_agent_model",
            ),
            "planner_agent_model": body.get(
                "planner_agent_model",
            ),
            "validation_agent_model": body.get(
                "validation_agent_model",
            ),
            "code_manager_iterations": body.get(
                "code_manager_iterations", 3,
            ),
            "planner_time_limit_minutes": body.get(
                "planner_time_limit_minutes", 5,
            ),
            "dt_config": (
                DatabaseFacade.get_digital_twin_config()
                or DIGITAL_TWIN.DEFAULT_CONFIG
            ),
            "compaction_model": body.get(
                "compaction_model",
            ),
            "compaction_threshold": body.get(
                "compaction_threshold", 0.8,
            ),
            "code_reviewer_enabled": body.get(
                "code_reviewer_enabled", True,
            ),
            "validator_enabled": body.get(
                "validator_enabled", True,
            ),
            "code_model_enabled": body.get(
                "code_model_enabled", True,
            ),
        }
        conv_history = body.get(
            "conversation_history", [],
        )
        for entry in reversed(conv_history):
            if (
                entry.get("type") == "tool_result"
                and entry.get("tool_name")
                == "run_code_manager"
            ):
                result = entry.get("result", {})
                context["code_report"] = result.get(
                    "code_report", {},
                )
                context["orchestrator_report"] = (
                    result.get(
                        "orchestrator_report", {},
                    )
                )
                break
        for entry in reversed(conv_history):
            if (
                entry.get("type") == "tool_result"
                and entry.get("tool_name")
                == "run_planner_agent"
            ):
                result = entry.get("result", {})
                context["planner_report"] = result.get(
                    "planner_report", {},
                )
                context["response_plan"] = result.get(
                    "response_plan", "",
                )
                break
        for entry in reversed(conv_history):
            if (
                entry.get("type") == "tool_result"
                and entry.get("tool_name")
                == "run_validation_agent"
            ):
                result = entry.get("result", {})
                context["validation_report"] = (
                    result.get(
                        "validation_report", {},
                    )
                )
                break

        session_id = body.get("session_id")
        username = g.username
        job_id = (
            str(session_id) if session_id
            else body.get("job_id")
            or str(uuid.uuid4())
        )

        def on_complete(
            events: list[dict[str, Any]],
        ) -> None:
            """
            Auto-save tool results to session.

            :param events: the accumulated job events
            """
            if not session_id:
                return
            _save_tool_result(
                session_id, username,
                events, tool_name,
            )

        def _last_tool_was_validator(
            history: list[dict[str, Any]],
        ) -> bool:
            for entry in reversed(history):
                if entry.get("type") == "tool_result":
                    return (
                        entry.get("tool_name")
                        == "run_validation_agent"
                    )
            return False

        def run() -> Generator[
            dict[str, Any], None, None
        ]:
            """
            Run the streaming tool in background.

            Redeploys the digital twin when the previous
            tool was the validator (it may have altered
            firewall rules, etc.) — unless the current
            tool is the validator itself, which redeploys
            internally.

            :return: a generator of event dicts
            """
            try:
                if (
                    tool_name != "run_validation_agent"
                    and _last_tool_was_validator(
                        conv_history,
                    )
                ):
                    yield from _redeploy_dt(job_id)
                if (
                    tool_name == "run_code_manager"
                    and not context.get(
                        "code_reviewer_enabled",
                        True,
                    )
                ):
                    yield from (
                        run_code_agent_direct_stream(
                            context=context,
                        )
                    )
                elif (
                    tool_name
                    == "run_validation_agent"
                    and not context.get(
                        "validator_enabled",
                        True,
                    )
                ):
                    yield {
                        "type": "done",
                        "result": {
                            "validation_report": {
                                "overall_verdict":
                                    "skipped",
                                "executive_summary":
                                    "Validation "
                                    "skipped by "
                                    "user",
                            },
                        },
                    }
                else:
                    agent = PlanManagerAgent()
                    yield from (
                        agent.execute_tool_stream(
                            tool_name, tool_args,
                            context=context,
                        )
                    )
            except Exception as e:
                yield {
                    "type": "error",
                    "message": str(e),
                }

        job_manager.start_job(
            job_id, run, on_complete=on_complete,
        )
        return jsonify({"job_id": job_id}), 202

    if tool_name not in PLAN_MANAGER_TOOL_DISPATCH:
        return jsonify({
            "error": f"Unknown tool: {tool_name}",
        }), 400
    try:
        agent = PlanManagerAgent()
        result = agent.execute_tool(
            tool_name, tool_args,
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@agents_bp.route(
    "/orchestrator/step", methods=["POST"],
)
@token_required
def agents_orchestrator_step() -> (
    tuple[Response, int]
):
    """
    Start an OrchestratorAgent step as a background job.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    system_description = body.get(
        "system_description", "",
    )
    security_alerts = body.get("security_alerts", "")
    operator_feedback = body.get(
        "operator_feedback", "",
    )
    conversation_history = body.get(
        "conversation_history", [],
    )
    images = body.get("images", [])
    model_name = body.get("model_name") or None
    session_id = body.get("session_id")
    username = g.username
    if not isinstance(images, list):
        images = []
    if not system_description and not security_alerts:
        return jsonify({
            "error": (
                "system_description or "
                "security_alerts is required"
            ),
        }), 400
    job_id = (
        str(session_id) if session_id
        else str(uuid.uuid4())
    )
    last_prompt_tokens = body.get(
        "last_prompt_tokens", 0,
    )
    compaction_model = body.get(
        "compaction_model",
    ) or None
    compaction_threshold = body.get(
        "compaction_threshold", 0.8,
    )

    def on_complete(
        events: list[dict[str, Any]],
    ) -> None:
        """
        Auto-save step results to the planning session.

        :param events: the accumulated job events
        """
        if not session_id:
            return
        _save_step_result(
            session_id, username, events,
        )

    def run() -> Generator[
        dict[str, Any], None, None
    ]:
        """
        Run the OrchestratorAgent step in background.

        :return: a generator of event dicts
        """
        try:
            dt_enabled = body.get(
                "dt_enabled", True,
            )
            if (
                not conversation_history
                and dt_enabled
            ):
                yield from _redeploy_dt(job_id)
                yield from _start_sandbox()
            agent = OrchestratorAgent()
            agent._last_prompt_tokens = (
                last_prompt_tokens
            )
            max_iterations = body.get(
                "orchestrator_iterations", 1,
            )
            pentest_enabled = body.get(
                "pentest_enabled", True,
            )
            yield from agent.step_stream(
                system_description=system_description,
                security_alerts=security_alerts,
                operator_feedback=operator_feedback,
                conversation_history=(
                    conversation_history
                ),
                images=images,
                model_name=model_name,
                max_iterations=max_iterations,
                compaction_model=compaction_model,
                compaction_threshold=(
                    compaction_threshold
                ),
                pentest_enabled=pentest_enabled,
            )
        except Exception as e:
            yield {
                "type": "error",
                "message": str(e),
            }

    job_manager.start_job(
        job_id, run, on_complete=on_complete,
    )
    return jsonify({"job_id": job_id}), 202


@agents_bp.route(
    "/orchestrator/prompt", methods=["POST"],
)
@token_required
def agents_orchestrator_prompt() -> (
    tuple[Response, int]
):
    """
    Render the OrchestratorAgent system prompt.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    prompt = build_orchestrator_prompt(
        system_description=body.get(
            "system_description", "",
        ),
        security_alerts=body.get(
            "security_alerts", "",
        ),
        operator_feedback=body.get(
            "operator_feedback", "",
        ),
        max_iterations=body.get(
            "orchestrator_iterations", 1,
        ),
        pentest_enabled=body.get(
            "pentest_enabled", True,
        ),
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route(
    "/orchestrator/tool", methods=["POST"],
)
@token_required
def agents_orchestrator_tool() -> (
    Response | tuple[Response, int]
):
    """
    Execute an approved tool call for OrchestratorAgent.

    Sub-agent tools (run_report_manager,
    run_plan_manager) are streaming and require
    system context from the request body.

    :return: a streaming Response or (JSON, status) tuple
    """
    body = request.get_json(silent=True) or {}
    tool_name = body.get("tool_name", "")
    tool_args = body.get("tool_args", {})
    incident_id = body.get("incident_id")
    if not tool_name:
        return jsonify({
            "error": "tool_name is required",
        }), 400

    if tool_name in ORCHESTRATOR_STREAMING_DISPATCH:
        context: dict[str, Any] = {
            "system_description": body.get(
                "system_description", "",
            ),
            "security_alerts": body.get(
                "security_alerts", "",
            ),
            "operator_feedback": body.get(
                "operator_feedback", "",
            ),
            "images": body.get("images"),
            "username": g.username,
            "incident_id": incident_id,
            "report_manager_model": body.get(
                "report_manager_model",
            ),
            "report_agent_model": body.get(
                "report_agent_model",
            ),
            "reviewer_agent_model": body.get(
                "reviewer_agent_model",
            ),
            "plan_manager_model": body.get(
                "plan_manager_model",
            ),
            "code_manager_model": body.get(
                "code_manager_model",
            ),
            "code_agent_model": body.get(
                "code_agent_model",
            ),
            "code_reviewer_agent_model": body.get(
                "code_reviewer_agent_model",
            ),
            "planner_agent_model": body.get(
                "planner_agent_model",
            ),
            "validation_agent_model": body.get(
                "validation_agent_model",
            ),
            "report_manager_iterations": body.get(
                "report_manager_iterations", 3,
            ),
            "plan_manager_iterations": body.get(
                "plan_manager_iterations", 2,
            ),
            "code_manager_iterations": body.get(
                "code_manager_iterations", 3,
            ),
            "planner_time_limit_minutes": body.get(
                "planner_time_limit_minutes", 5,
            ),
            "dt_config": (
                DatabaseFacade.get_digital_twin_config()
                or DIGITAL_TWIN.DEFAULT_CONFIG
            ),
            "compaction_model": body.get(
                "compaction_model",
            ),
            "report_manager_compaction": body.get(
                "report_manager_compaction", 0.8,
            ),
            "report_agent_compaction": body.get(
                "report_agent_compaction", 0.8,
            ),
            "report_reviewer_compaction": body.get(
                "report_reviewer_compaction", 0.8,
            ),
            "plan_manager_compaction": body.get(
                "plan_manager_compaction", 0.8,
            ),
            "code_manager_compaction": body.get(
                "code_manager_compaction", 0.8,
            ),
            "code_agent_compaction": body.get(
                "code_agent_compaction", 0.8,
            ),
            "code_reviewer_compaction": body.get(
                "code_reviewer_compaction", 0.8,
            ),
            "planner_agent_compaction": body.get(
                "planner_agent_compaction", 0.8,
            ),
            "validation_agent_compaction": body.get(
                "validation_agent_compaction", 0.8,
            ),
            "dt_enabled": body.get(
                "dt_enabled", True,
            ),
            "info_tools_enabled": body.get(
                "info_tools_enabled", True,
            ),
            "report_reviewer_enabled": body.get(
                "report_reviewer_enabled", True,
            ),
            "code_reviewer_enabled": body.get(
                "code_reviewer_enabled", True,
            ),
            "validator_enabled": body.get(
                "validator_enabled", True,
            ),
            "pentest_enabled": body.get(
                "pentest_enabled", True,
            ),
            "code_model_enabled": body.get(
                "code_model_enabled", True,
            ),
        }
        conv_history = body.get(
            "conversation_history", [],
        )
        context["pentest_agent_model"] = body.get(
            "pentest_agent_model",
        )
        context["pentest_agent_compaction"] = body.get(
            "pentest_agent_compaction", 0.8,
        )

        if tool_name == "run_report_manager":
            validation_fb = ""
            for entry in reversed(conv_history):
                if (
                    entry.get("type")
                    == "tool_result"
                    and entry.get("tool_name")
                    == "run_pentest_agent"
                ):
                    pr = entry.get(
                        "result", {},
                    ).get("pentest_report", {})
                    verdict = pr.get(
                        "overall_verdict", "",
                    )
                    summary = pr.get(
                        "executive_summary", "",
                    )
                    if verdict and verdict != (
                        "Attack path validated"
                    ):
                        validation_fb = (
                            f"Pentest verdict: "
                            f"{verdict}\n\n"
                            f"{summary}"
                        )
                    break
            if validation_fb:
                context["validation_feedback"] = (
                    validation_fb
                )

        if tool_name in (
            "run_pentest_agent",
            "run_plan_manager",
        ):
            assessment: dict[str, Any] = {}
            for entry in reversed(conv_history):
                if (
                    entry.get("type")
                    == "tool_result"
                    and entry.get("tool_name")
                    == "run_report_manager"
                ):
                    result = entry.get(
                        "result", {},
                    )
                    raw = result.get(
                        "assessment", {},
                    )
                    assessment = {
                        k: v for k, v in raw.items()
                        if k != "attack_path_image"
                    } if isinstance(raw, dict) else raw
                    break
            context["assessment"] = assessment

        session_id = body.get("session_id")
        username = g.username
        job_id = (
            str(session_id) if session_id
            else body.get("job_id")
            or str(uuid.uuid4())
        )

        def on_complete(
            events: list[dict[str, Any]],
        ) -> None:
            """
            Auto-save tool results to session.

            :param events: the accumulated job events
            """
            if not session_id:
                return
            _save_tool_result(
                session_id, username,
                events, tool_name,
            )

        def run() -> Generator[
            dict[str, Any], None, None
        ]:
            """
            Run the streaming tool in background.

            :return: a generator of event dicts
            """
            try:
                if (
                    tool_name == "run_report_manager"
                    and not context.get(
                        "report_reviewer_enabled",
                        True,
                    )
                ):
                    yield from (
                        run_report_agent_direct_stream(
                            context=context,
                        )
                    )
                else:
                    agent = OrchestratorAgent()
                    yield from (
                        agent.execute_tool_stream(
                            tool_name, tool_args,
                            context=context,
                        )
                    )
            except Exception as e:
                yield {
                    "type": "error",
                    "message": str(e),
                }

        job_manager.start_job(
            job_id, run, on_complete=on_complete,
        )
        return jsonify({"job_id": job_id}), 202

    if tool_name not in ORCHESTRATOR_TOOL_DISPATCH:
        return jsonify({
            "error": f"Unknown tool: {tool_name}",
        }), 400
    try:
        agent = OrchestratorAgent()
        result = agent.execute_tool(
            tool_name, tool_args,
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@agents_bp.route("/reports", methods=["POST"])
@token_required
def save_agent_report() -> tuple[Response, int]:
    """
    Save an agent report to the database.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    agent_type = body.get("agent_type", "")
    report = body.get("report")
    if not agent_type or report is None:
        return jsonify({
            "error": "agent_type and report are required",
        }), 400
    incident_id = body.get("incident_id")
    conversation_history = body.get("conversation_history")
    model_name = body.get("model_name") or None
    policy_data = None
    if agent_type == "planner":
        try:
            policy_data = _read_policy_from_sandbox()
        except Exception:
            logger.warning(
                "Failed to read policy from sandbox",
                exc_info=True,
            )
    saved = DatabaseFacade.save_agent_report(
        agent_type=agent_type,
        username=g.username,
        report=report,
        incident_id=incident_id,
        conversation_history=conversation_history,
        policy_data=policy_data,
        model_name=model_name,
    )
    return jsonify(saved), 201


@agents_bp.route("/reports", methods=["GET"])
@token_required
def list_agent_reports() -> tuple[Response, int]:
    """
    List agent reports, optionally filtered by agent_type query param.

    :return: a tuple of (JSON response, HTTP status code)
    """
    agent_type = request.args.get("agent_type")
    incident_id = request.args.get("incident_id", type=int)
    reports = DatabaseFacade.list_agent_reports(
        agent_type=agent_type,
        incident_id=incident_id,
    )
    return jsonify(reports), 200


@agents_bp.route("/reports/<int:report_id>", methods=["GET"])
@token_required
def get_agent_report(report_id: int) -> tuple[Response, int]:
    """
    Get a single agent report by id.

    :param report_id: the report id
    :return: a tuple of (JSON response, HTTP status code)
    """
    report = DatabaseFacade.get_agent_report(report_id)
    if report is None:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(report), 200


@agents_bp.route("/reports/<int:report_id>", methods=["DELETE"])
@token_required
def delete_agent_report(
    report_id: int,
) -> tuple[Response, int]:
    """
    Delete an agent report by id.

    :param report_id: the report id
    :return: a tuple of (JSON response, HTTP status code)
    """
    deleted = DatabaseFacade.delete_agent_report(report_id)
    if not deleted:
        return jsonify({"error": "Report not found"}), 404
    return jsonify({"deleted": True}), 200


@agents_bp.route("/reports", methods=["DELETE"])
@token_required
def delete_all_agent_reports() -> tuple[Response, int]:
    """
    Delete all agent reports for a given agent type.

    :return: a tuple of (JSON response, HTTP status code)
    """
    agent_type = request.args.get("agent_type")
    if not agent_type:
        return jsonify({"error": "agent_type is required"}), 400
    deleted_count = DatabaseFacade.delete_all_agent_reports(agent_type)
    return jsonify({"deleted_count": deleted_count}), 200


@agents_bp.route("/sessions/active", methods=["GET"])
@token_required
def get_active_session() -> tuple[Response, int]:
    """
    Get the active planning session for the current user.

    :return: a tuple of (JSON response, HTTP status code)
    """
    try:
        agent_type = request.args.get("agent_type")
        session = (
            DatabaseFacade.get_active_planning_session(
                g.username,
                agent_type=agent_type,
            )
        )
        if session is None:
            return jsonify({"session": None}), 200
        return jsonify({"session": session}), 200
    except Exception as e:
        logger.error(
            "Failed to get active session: %s", e,
        )
        return jsonify({"error": str(e)}), 500


@agents_bp.route("/sessions", methods=["POST"])
@token_required
def create_session() -> tuple[Response, int]:
    """
    Create a new planning session.

    Auto-cancels any existing active session for the user
    with the same agent_type.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    incident_inputs = body.get("incident_inputs", {})
    agent_config = body.get("agent_config", {})
    agent_type = body.get("agent_type")
    if not incident_inputs:
        return jsonify({
            "error": "incident_inputs is required",
        }), 400
    if not agent_config:
        return jsonify({
            "error": "agent_config is required",
        }), 400
    try:
        session = DatabaseFacade.create_planning_session(
            g.username, incident_inputs, agent_config,
            agent_type=agent_type,
        )
        return jsonify({"session": session}), 201
    except Exception as e:
        logger.error(
            "Failed to create session: %s", e,
        )
        return jsonify({"error": str(e)}), 500


@agents_bp.route(
    "/sessions/<int:session_id>", methods=["PUT"],
)
@token_required
def update_session(
    session_id: int,
) -> tuple[Response, int]:
    """
    Update a planning session.

    :param session_id: the session id
    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    conversation_history = body.get(
        "conversation_history",
    )
    pending_proposal = body.get("pending_proposal")
    context_usage = body.get("context_usage")
    status = body.get("status")
    ui_state = body.get("ui_state")
    if (
        "pending_proposal" in body
        and pending_proposal is None
    ):
        pending_proposal = False
    try:
        updated = DatabaseFacade.update_planning_session(
            session_id, g.username,
            conversation_history=conversation_history,
            pending_proposal=pending_proposal,
            context_usage=context_usage,
            status=status,
            ui_state=ui_state,
        )
        if not updated:
            return jsonify({
                "error": (
                    "Session not found or "
                    "not owned by user"
                ),
            }), 404
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(
            "Failed to update session %d: %s",
            session_id, e,
        )
        return jsonify({"error": str(e)}), 500


@agents_bp.route(
    "/sessions/<int:session_id>",
    methods=["DELETE"],
)
@token_required
def delete_session(
    session_id: int,
) -> tuple[Response, int]:
    """
    Delete a planning session.

    :param session_id: the session id
    :return: a tuple of (JSON response, HTTP status code)
    """
    try:
        deleted = DatabaseFacade.delete_planning_session(
            session_id, g.username,
        )
        if not deleted:
            return jsonify({
                "error": (
                    "Session not found or "
                    "not owned by user"
                ),
            }), 404
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(
            "Failed to delete session %d: %s",
            session_id, e,
        )
        return jsonify({"error": str(e)}), 500


# ── Pentest Agent ─────────────────────────────────────────────


@agents_bp.route("/pentest/step", methods=["POST"])
@token_required
def agents_pentest_step() -> tuple[Response, int]:
    """
    Start a PentestAgent step as a background job.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    system_description = body.get(
        "system_description", "",
    )
    attack_path = body.get("attack_path", "")
    conversation_history = body.get(
        "conversation_history", [],
    )
    images = body.get("images", [])
    model_name = body.get("model_name") or None
    if not isinstance(images, list):
        images = []
    if not system_description and not attack_path:
        return jsonify({
            "error": (
                "system_description and attack_path "
                "are required"
            ),
        }), 400
    session_id = body.get("session_id")
    username = g.username
    job_id = (
        str(session_id) if session_id
        else body.get("job_id") or str(uuid.uuid4())
    )
    last_prompt_tokens = body.get(
        "last_prompt_tokens", 0,
    )
    compaction_model = body.get(
        "compaction_model",
    ) or None
    compaction_threshold = body.get(
        "compaction_threshold", 0.8,
    )

    def on_complete(
        events: list[dict[str, Any]],
    ) -> None:
        """
        Auto-save step results to the planning session.

        :param events: the accumulated job events
        """
        if not session_id:
            return
        _save_step_result(
            session_id, username, events,
        )

    def run() -> Generator[
        dict[str, Any], None, None
    ]:
        """
        Run the PentestAgent step in background.

        :return: a generator of event dicts
        """
        try:
            dt_enabled = body.get(
                "dt_enabled", True,
            )
            if (
                not conversation_history
                and dt_enabled
            ):
                yield from _redeploy_dt(job_id)
                yield from _start_sandbox()

            dt_config = (
                DatabaseFacade.get_digital_twin_config()
                or DIGITAL_TWIN.DEFAULT_CONFIG
            )
            agent = PentestAgent()
            agent._last_prompt_tokens = (
                last_prompt_tokens
            )
            yield from agent.step_stream(
                system_description=system_description,
                attack_path=attack_path,
                conversation_history=(
                    conversation_history
                ),
                images=images,
                model_name=model_name,
                dt_config=dt_config,
                compaction_model=compaction_model,
                compaction_threshold=(
                    compaction_threshold
                ),
                dt_enabled=dt_enabled,
            )
        except Exception as e:
            yield _make_error_event(e)

    job_manager.start_job(
        job_id, run, on_complete=on_complete,
    )
    return jsonify({"job_id": job_id}), 202


@agents_bp.route("/pentest/prompt", methods=["POST"])
@token_required
def agents_pentest_prompt() -> tuple[Response, int]:
    """
    Render the PentestAgent system prompt from the given context.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    dt_config = (
        DatabaseFacade.get_digital_twin_config()
        or DIGITAL_TWIN.DEFAULT_CONFIG
    )
    prompt = build_pentest_prompt(
        system_description=body.get(
            "system_description", "",
        ) or "N/A",
        attack_path=body.get(
            "attack_path", "",
        ) or "N/A",
        attacker_info=format_attacker_info(
            dt_config,
        ),
        dt_container_list=(
            format_container_list_with_attacker(
                dt_config,
            )
        ),
        dt_container_table=format_container_table(
            dt_config,
        ),
        dt_network_connectivity=(
            format_network_connectivity(dt_config)
        ),
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route("/pentest/tool", methods=["POST"])
@token_required
def agents_pentest_tool() -> tuple[Response, int]:
    """
    Execute an approved tool call for PentestAgent.

    Streaming tools run as background jobs; other tools
    return a single JSON response.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    tool_name = body.get("tool_name", "")
    tool_args = body.get("tool_args", {})
    incident_id = body.get("incident_id")
    if not tool_name:
        return jsonify({
            "error": "tool_name is required",
        }), 400
    if tool_name in _DT_TOOLS and incident_id is not None:
        tool_args["incident_id"] = incident_id

    if tool_name in PENTEST_STREAMING_DISPATCH:
        session_id = body.get("session_id")
        username = g.username
        job_id = (
            str(session_id) if session_id
            else body.get("job_id")
            or str(uuid.uuid4())
        )

        def on_complete(
            events: list[dict[str, Any]],
        ) -> None:
            """
            Auto-save tool results to session.

            :param events: the accumulated job events
            """
            if not session_id:
                return
            _save_tool_result(
                session_id, username,
                events, tool_name,
            )

        def run() -> Generator[
            dict[str, Any], None, None
        ]:
            """
            Run the streaming tool in background.

            :return: a generator of event dicts
            """
            try:
                agent = PentestAgent()
                yield from agent.execute_tool_stream(
                    tool_name, tool_args,
                )
            except Exception as e:
                yield {
                    "type": "error",
                    "message": str(e),
                }

        job_manager.start_job(
            job_id, run, on_complete=on_complete,
        )
        return jsonify({"job_id": job_id}), 202

    agent = PentestAgent()
    result = agent.execute_tool(
        tool_name, tool_args,
    )
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 200


# ── Host Analyzer Agent ──────────────────────────────────────


@agents_bp.route("/host-analyzer/step", methods=["POST"])
@token_required
def agents_host_analyzer_step() -> tuple[Response, int]:
    """
    Start a HostAnalyzerAgent step as a background job.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    system_description = body.get(
        "system_description", "",
    )
    security_alerts = body.get("security_alerts", "")
    operator_feedback = body.get(
        "operator_feedback", "",
    )
    host_description = body.get(
        "host_description", "",
    )
    conversation_history = body.get(
        "conversation_history", [],
    )
    images = body.get("images", [])
    model_name = body.get("model_name") or None
    if not isinstance(images, list):
        images = []
    if (
        not system_description
        and not host_description
    ):
        return jsonify({
            "error": (
                "system_description and "
                "host_description are required"
            ),
        }), 400
    session_id = body.get("session_id")
    username = g.username
    job_id = (
        str(session_id) if session_id
        else body.get("job_id") or str(uuid.uuid4())
    )
    last_prompt_tokens = body.get(
        "last_prompt_tokens", 0,
    )
    compaction_model = body.get(
        "compaction_model",
    ) or None
    compaction_threshold = body.get(
        "compaction_threshold", 0.8,
    )

    def on_complete(
        events: list[dict[str, Any]],
    ) -> None:
        """
        Auto-save step results to the planning session.

        :param events: the accumulated job events
        """
        if not session_id:
            return
        _save_step_result(
            session_id, username, events,
        )

    def run() -> Generator[
        dict[str, Any], None, None
    ]:
        """
        Run the HostAnalyzerAgent step in background.

        :return: a generator of event dicts
        """
        try:
            dt_enabled = body.get(
                "dt_enabled", True,
            )
            info_tools_enabled = body.get(
                "info_tools_enabled", True,
            )
            if (
                not conversation_history
                and dt_enabled
            ):
                yield from _redeploy_dt(job_id)

            dt_config = (
                DatabaseFacade.get_digital_twin_config()
                or DIGITAL_TWIN.DEFAULT_CONFIG
            )
            agent = HostAnalyzerAgent()
            agent._last_prompt_tokens = (
                last_prompt_tokens
            )
            yield from agent.step_stream(
                system_description=(
                    system_description
                ),
                security_alerts=security_alerts,
                operator_feedback=operator_feedback,
                host_description=host_description,
                conversation_history=(
                    conversation_history
                ),
                images=images,
                model_name=model_name,
                dt_config=dt_config,
                compaction_model=compaction_model,
                compaction_threshold=(
                    compaction_threshold
                ),
                dt_enabled=dt_enabled,
                info_tools_enabled=(
                    info_tools_enabled
                ),
            )
        except Exception as e:
            yield _make_error_event(e)

    job_manager.start_job(
        job_id, run, on_complete=on_complete,
    )
    return jsonify({"job_id": job_id}), 202


@agents_bp.route(
    "/host-analyzer/prompt", methods=["POST"],
)
@token_required
def agents_host_analyzer_prompt() -> tuple[
    Response, int
]:
    """
    Render the HostAnalyzerAgent system prompt.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    dt_config = (
        DatabaseFacade.get_digital_twin_config()
        or DIGITAL_TWIN.DEFAULT_CONFIG
    )
    prompt = build_host_analyzer_prompt(
        system_description=body.get(
            "system_description", "",
        ) or "N/A",
        security_alerts=body.get(
            "security_alerts", "",
        ) or "N/A",
        operator_feedback=body.get(
            "operator_feedback", "",
        ) or "N/A",
        host_description=body.get(
            "host_description", "",
        ) or "N/A",
        dt_container_list=format_container_list(
            dt_config,
        ),
        dt_container_table=format_container_table(
            dt_config,
        ),
        dt_network_connectivity=(
            format_network_connectivity(dt_config)
        ),
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route(
    "/host-analyzer/tool", methods=["POST"],
)
@token_required
def agents_host_analyzer_tool() -> tuple[
    Response, int
]:
    """
    Execute an approved tool call for HostAnalyzerAgent.

    Streaming tools run as background jobs; other tools
    return a single JSON response.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    tool_name = body.get("tool_name", "")
    tool_args = body.get("tool_args", {})
    incident_id = body.get("incident_id")
    if not tool_name:
        return jsonify({
            "error": "tool_name is required",
        }), 400
    if tool_name in _DT_TOOLS and incident_id is not None:
        tool_args["incident_id"] = incident_id

    if tool_name in HOST_ANALYZER_STREAMING_DISPATCH:
        session_id = body.get("session_id")
        username = g.username
        job_id = (
            str(session_id) if session_id
            else body.get("job_id")
            or str(uuid.uuid4())
        )

        def on_complete(
            events: list[dict[str, Any]],
        ) -> None:
            """
            Auto-save tool results to session.

            :param events: the accumulated job events
            """
            if not session_id:
                return
            _save_tool_result(
                session_id, username,
                events, tool_name,
            )

        def run() -> Generator[
            dict[str, Any], None, None
        ]:
            """
            Run the streaming tool in background.

            :return: a generator of event dicts
            """
            try:
                agent = HostAnalyzerAgent()
                yield from agent.execute_tool_stream(
                    tool_name, tool_args,
                )
            except Exception as e:
                yield {
                    "type": "error",
                    "message": str(e),
                }

        job_manager.start_job(
            job_id, run, on_complete=on_complete,
        )
        return jsonify({"job_id": job_id}), 202

    agent = HostAnalyzerAgent()
    result = agent.execute_tool(
        tool_name, tool_args,
    )
    if "error" in result:
        logger.error(
            "host-analyzer tool %s failed: %s",
            tool_name, result["error"],
        )
        return jsonify(result), 400
    return jsonify(result), 200


# ── Action Validator Agent ───────────────────────────────────


@agents_bp.route(
    "/action-validator/step", methods=["POST"],
)
@token_required
def agents_action_validator_step() -> tuple[
    Response, int
]:
    """
    Start an ActionValidatorAgent step as a background job.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    system_description = body.get(
        "system_description", "",
    )
    action_to_validate = body.get(
        "action_to_validate", "",
    )
    operator_feedback = body.get(
        "operator_feedback", "",
    )
    conversation_history = body.get(
        "conversation_history", [],
    )
    images = body.get("images", [])
    model_name = body.get("model_name") or None
    if not isinstance(images, list):
        images = []
    if (
        not system_description
        and not action_to_validate
    ):
        return jsonify({
            "error": (
                "system_description or "
                "action_to_validate is required"
            ),
        }), 400
    session_id = body.get("session_id")
    username = g.username
    job_id = (
        str(session_id) if session_id
        else body.get("job_id") or str(uuid.uuid4())
    )
    last_prompt_tokens = body.get(
        "last_prompt_tokens", 0,
    )
    compaction_model = body.get(
        "compaction_model",
    ) or None
    compaction_threshold = body.get(
        "compaction_threshold", 0.8,
    )

    def on_complete(
        events: list[dict[str, Any]],
    ) -> None:
        """
        Auto-save step results to the planning session.

        :param events: the accumulated job events
        """
        if not session_id:
            return
        _save_step_result(
            session_id, username, events,
        )

    def run() -> Generator[
        dict[str, Any], None, None
    ]:
        """
        Run the ActionValidatorAgent step in background.

        :return: a generator of event dicts
        """
        try:
            dt_enabled = body.get(
                "dt_enabled", True,
            )
            if (
                not conversation_history
                and dt_enabled
            ):
                yield from _redeploy_dt(job_id)

            dt_config = (
                DatabaseFacade.get_digital_twin_config()
                or DIGITAL_TWIN.DEFAULT_CONFIG
            )
            agent = ActionValidatorAgent()
            agent._last_prompt_tokens = (
                last_prompt_tokens
            )
            yield from agent.step_stream(
                system_description=(
                    system_description
                ),
                action_to_validate=(
                    action_to_validate
                ),
                operator_feedback=operator_feedback,
                conversation_history=(
                    conversation_history
                ),
                images=images,
                model_name=model_name,
                dt_config=dt_config,
                compaction_model=compaction_model,
                compaction_threshold=(
                    compaction_threshold
                ),
                dt_enabled=dt_enabled,
            )
        except Exception as e:
            yield _make_error_event(e)

    job_manager.start_job(
        job_id, run, on_complete=on_complete,
    )
    return jsonify({"job_id": job_id}), 202


@agents_bp.route(
    "/action-validator/prompt", methods=["POST"],
)
@token_required
def agents_action_validator_prompt() -> tuple[
    Response, int
]:
    """
    Render the ActionValidatorAgent system prompt.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    dt_config = (
        DatabaseFacade.get_digital_twin_config()
        or DIGITAL_TWIN.DEFAULT_CONFIG
    )
    prompt = build_action_validator_prompt(
        system_description=body.get(
            "system_description", "",
        ) or "N/A",
        action_to_validate=body.get(
            "action_to_validate", "",
        ) or "N/A",
        operator_feedback=body.get(
            "operator_feedback", "",
        ) or "N/A",
        dt_container_list=format_container_list(
            dt_config,
        ),
        dt_container_table=format_container_table(
            dt_config,
        ),
        dt_network_connectivity=(
            format_network_connectivity(dt_config)
        ),
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route(
    "/action-validator/tool", methods=["POST"],
)
@token_required
def agents_action_validator_tool() -> tuple[
    Response, int
]:
    """
    Execute an approved tool call for ActionValidatorAgent.

    Streaming tools run as background jobs; other tools
    return a single JSON response.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    tool_name = body.get("tool_name", "")
    tool_args = body.get("tool_args", {})
    incident_id = body.get("incident_id")
    if not tool_name:
        return jsonify({
            "error": "tool_name is required",
        }), 400
    if tool_name in _DT_TOOLS and incident_id is not None:
        tool_args["incident_id"] = incident_id

    if tool_name in ACTION_VALIDATOR_STREAMING_DISPATCH:
        session_id = body.get("session_id")
        username = g.username
        job_id = (
            str(session_id) if session_id
            else body.get("job_id")
            or str(uuid.uuid4())
        )

        def on_complete(
            events: list[dict[str, Any]],
        ) -> None:
            """
            Auto-save tool results to session.

            :param events: the accumulated job events
            """
            if not session_id:
                return
            _save_tool_result(
                session_id, username,
                events, tool_name,
            )

        def run() -> Generator[
            dict[str, Any], None, None
        ]:
            """
            Run the streaming tool in background.

            :return: a generator of event dicts
            """
            try:
                agent = ActionValidatorAgent()
                yield from agent.execute_tool_stream(
                    tool_name, tool_args,
                )
            except Exception as e:
                yield {
                    "type": "error",
                    "message": str(e),
                }

        job_manager.start_job(
            job_id, run, on_complete=on_complete,
        )
        return jsonify({"job_id": job_id}), 202

    agent = ActionValidatorAgent()
    result = agent.execute_tool(
        tool_name, tool_args,
    )
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 200
