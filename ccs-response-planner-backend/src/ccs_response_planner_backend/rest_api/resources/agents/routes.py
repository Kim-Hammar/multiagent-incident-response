"""
Routes and sub-resources for the /agents resource.
"""
import json
import logging
from typing import Any, Generator

from flask import Blueprint, Response, g, jsonify, request

from ccs_response_planner_backend.agents.information_agent.agent import (
    InformationAgent,
)
from ccs_response_planner_backend.agents.information_agent.prompt import (
    SYSTEM_PROMPT_TEMPLATE,
)
from ccs_response_planner_backend.agents.information_agent.tools import (
    STREAMING_TOOL_DISPATCH as INFO_STREAMING_DISPATCH,
    TOOL_DISPATCH,
)
from ccs_response_planner_backend.agents.penetration_test_agent.agent import (
    PenetrationTestAgent,
)
from ccs_response_planner_backend.agents.penetration_test_agent.prompt import (
    SYSTEM_PROMPT_TEMPLATE as PENTEST_PROMPT_TEMPLATE,
)
from ccs_response_planner_backend.agents.penetration_test_agent.tools import (
    STREAMING_TOOL_DISPATCH as PENTEST_STREAMING_DISPATCH,
    TOOL_DISPATCH as PENTEST_TOOL_DISPATCH,
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
from ccs_response_planner_backend.agents.rl_agent.agent import (
    RlAgent,
)
from ccs_response_planner_backend.agents.rl_agent.prompt import (
    SYSTEM_PROMPT_TEMPLATE as RL_PROMPT_TEMPLATE,
)
from ccs_response_planner_backend.agents.rl_agent.tools import (
    STREAMING_TOOL_DISPATCH as RL_STREAMING_DISPATCH,
    TOOL_DISPATCH as RL_TOOL_DISPATCH,
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
from ccs_response_planner_backend.agents.dp_agent.agent import (
    DpAgent,
)
from ccs_response_planner_backend.agents.dp_agent.prompt import (
    SYSTEM_PROMPT_TEMPLATE as DP_PROMPT_TEMPLATE,
)
from ccs_response_planner_backend.agents.dp_agent.tools import (
    STREAMING_TOOL_DISPATCH as DP_STREAMING_DISPATCH,
    TOOL_DISPATCH as DP_TOOL_DISPATCH,
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

_DT_TOOLS = {"dt_exec", "pentest_exec", "generate_attack_image"}

agents_bp = Blueprint(
    API.AGENTS_RESOURCE, __name__,
    url_prefix=f"{API.PREFIX}/{API.AGENTS_RESOURCE}",
)


def _redeploy_dt() -> Generator[dict[str, str], None, None]:
    """
    Stop and redeploy the digital twin for a fresh state.

    Yields ``dt_progress`` event dicts that can be streamed to
    the frontend as NDJSON.

    :return: a generator of progress event dicts
    """
    config = DatabaseFacade.get_digital_twin_config()
    if config is None:
        config = DIGITAL_TWIN.DEFAULT_CONFIG
    yield {
        "type": "dt_progress",
        "message": "Stopping digital twin...",
    }
    for item in DockerManager.stop():
        msg = item.get("message", "")
        if item.get("type") == "progress" and msg:
            logger.info("DT redeploy (stop): %s", msg)
    yield {
        "type": "dt_progress",
        "message": "Deploying fresh digital twin...",
    }
    for item in DockerManager.deploy(config):
        msg = item.get("message", "")
        if item.get("type") == "progress" and msg:
            logger.info("DT redeploy (deploy): %s", msg)
    yield {
        "type": "dt_progress",
        "message": "Digital twin ready",
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
    from ccs_response_planner_backend.agents.rl_agent.tools import (
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


@agents_bp.route("/information/step", methods=["POST"])
@token_required
def agents_information_step() -> Response | tuple[Response, int]:
    """
    Advance the InformationAgent loop by one step (NDJSON stream).

    :return: an NDJSON streaming Response, or a (JSON, status) tuple
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

    def generate() -> Generator[str, None, None]:
        """
        Yield NDJSON lines from the agent stream.

        :return: a generator of newline-delimited JSON strings
        """
        try:
            if not conversation_history:
                for ev in _redeploy_dt():
                    yield json.dumps(ev) + "\n"
            agent = InformationAgent()
            for event in agent.step_stream(
                system_description=system_description,
                security_alerts=security_alerts,
                operator_feedback=operator_feedback,
                conversation_history=conversation_history,
                images=images,
                model_name=model_name,
            ):
                yield json.dumps(event) + "\n"
        except Exception as e:
            yield json.dumps({
                "type": "error", "message": str(e),
            }) + "\n"

    return Response(generate(), mimetype="application/x-ndjson")


@agents_bp.route("/information/prompt", methods=["POST"])
@token_required
def agents_information_prompt() -> tuple[Response, int]:
    """
    Render the InformationAgent system prompt from the given context.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
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
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route("/information/tool", methods=["POST"])
@token_required
def agents_information_tool() -> Response | tuple[Response, int]:
    """
    Execute an approved tool call for the InformationAgent.

    For ``dt_exec``, streams NDJSON output events.
    For other tools, returns a single JSON response.

    :return: a streaming Response or (JSON, status) tuple
    """
    body = request.get_json(silent=True) or {}
    tool_name = body.get("tool_name", "")
    tool_args = body.get("tool_args", {})
    incident_id = body.get("incident_id")
    if not tool_name:
        return jsonify({"error": "tool_name is required"}), 400
    if tool_name in _DT_TOOLS and incident_id is not None:
        tool_args["incident_id"] = incident_id

    if tool_name in INFO_STREAMING_DISPATCH:
        def generate() -> Generator[str, None, None]:
            """
            Yield NDJSON lines from the streaming tool.

            :return: a generator of newline-delimited JSON strings
            """
            try:
                agent = InformationAgent()
                for event in agent.execute_tool_stream(
                    tool_name, tool_args,
                ):
                    yield json.dumps(event) + "\n"
            except Exception as e:
                yield json.dumps({
                    "type": "error", "message": str(e),
                }) + "\n"

        return Response(
            generate(), mimetype="application/x-ndjson",
        )

    if tool_name not in TOOL_DISPATCH:
        return jsonify({
            "error": f"Unknown tool: {tool_name}",
        }), 400
    try:
        agent = InformationAgent()
        result = agent.execute_tool(tool_name, tool_args)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@agents_bp.route("/pentest/step", methods=["POST"])
@token_required
def agents_pentest_step() -> Response | tuple[Response, int]:
    """
    Advance the PenetrationTestAgent loop by one step (NDJSON stream).

    :return: an NDJSON streaming Response, or a (JSON, status) tuple
    """
    body = request.get_json(silent=True) or {}
    system_description = body.get("system_description", "")
    conversation_history = body.get("conversation_history", [])
    images = body.get("images", [])
    model_name = body.get("model_name") or None
    if not isinstance(images, list):
        images = []
    if not system_description:
        return jsonify({
            "error": "system_description is required",
        }), 400

    def generate() -> Generator[str, None, None]:
        """
        Yield NDJSON lines from the agent stream.

        :return: a generator of newline-delimited JSON strings
        """
        try:
            if not conversation_history:
                for ev in _redeploy_dt():
                    yield json.dumps(ev) + "\n"
            agent = PenetrationTestAgent()
            for event in agent.step_stream(
                system_description=system_description,
                conversation_history=conversation_history,
                images=images,
                model_name=model_name,
            ):
                yield json.dumps(event) + "\n"
        except Exception as e:
            yield json.dumps({
                "type": "error", "message": str(e),
            }) + "\n"

    return Response(generate(), mimetype="application/x-ndjson")


@agents_bp.route("/pentest/prompt", methods=["POST"])
@token_required
def agents_pentest_prompt() -> tuple[Response, int]:
    """
    Render the PenetrationTestAgent system prompt from the given context.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    prompt = PENTEST_PROMPT_TEMPLATE.format(
        system_description=body.get(
            "system_description", "",
        ) or "N/A",
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route("/pentest/tool", methods=["POST"])
@token_required
def agents_pentest_tool() -> Response | tuple[Response, int]:
    """
    Execute an approved tool call for the PenetrationTestAgent.

    For ``pentest_exec``, streams NDJSON output events.
    For other tools, returns a single JSON response.

    :return: a streaming Response or (JSON, status) tuple
    """
    body = request.get_json(silent=True) or {}
    tool_name = body.get("tool_name", "")
    tool_args = body.get("tool_args", {})
    incident_id = body.get("incident_id")
    if not tool_name:
        return jsonify({"error": "tool_name is required"}), 400
    if tool_name in _DT_TOOLS and incident_id is not None:
        tool_args["incident_id"] = incident_id

    if tool_name in PENTEST_STREAMING_DISPATCH:
        def generate() -> Generator[str, None, None]:
            """
            Yield NDJSON lines from the streaming tool.

            :return: a generator of newline-delimited JSON strings
            """
            try:
                agent = PenetrationTestAgent()
                for event in agent.execute_tool_stream(
                    tool_name, tool_args,
                ):
                    yield json.dumps(event) + "\n"
            except Exception as e:
                yield json.dumps({
                    "type": "error", "message": str(e),
                }) + "\n"

        return Response(
            generate(), mimetype="application/x-ndjson",
        )

    if tool_name not in PENTEST_TOOL_DISPATCH:
        return jsonify({
            "error": f"Unknown tool: {tool_name}",
        }), 400
    try:
        agent = PenetrationTestAgent()
        result = agent.execute_tool(tool_name, tool_args)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@agents_bp.route("/validation/step", methods=["POST"])
@token_required
def agents_validation_step() -> Response | tuple[Response, int]:
    """
    Advance the ValidationAgent loop by one step (NDJSON stream).

    :return: an NDJSON streaming Response, or a (JSON, status) tuple
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

    def generate() -> Generator[str, None, None]:
        """
        Yield NDJSON lines from the agent stream.

        :return: a generator of newline-delimited JSON strings
        """
        try:
            if not conversation_history:
                for ev in _redeploy_dt():
                    yield json.dumps(ev) + "\n"

            has_policy = False
            if not conversation_history and planner_report_id:
                try:
                    policy_bytes = (
                        DatabaseFacade.get_policy_data(
                            planner_report_id,
                        )
                    )
                    if policy_bytes:
                        yield json.dumps({
                            "type": "dt_progress",
                            "message": (
                                "Loading RL policy "
                                "into sandbox..."
                            ),
                        }) + "\n"
                        _install_policy_in_sandbox(
                            policy_bytes,
                            code_report or {},
                        )
                        has_policy = True
                        yield json.dumps({
                            "type": "policy_loaded",
                            "message": "Policy loaded",
                        }) + "\n"
                except Exception as e:
                    logger.warning(
                        "Failed to load policy: %s",
                        e, exc_info=True,
                    )
                    yield json.dumps({
                        "type": "error",
                        "message": (
                            f"Failed to load policy: {e}"
                        ),
                    }) + "\n"

            agent = ValidationAgent()
            for event in agent.step_stream(
                system_description=system_description,
                incident_report=incident_report,
                response_plan=response_plan,
                specification=specification,
                planner_report=planner_report or {},
                code_report=code_report or {},
                conversation_history=conversation_history,
                images=images,
                model_name=model_name,
                has_policy=has_policy,
            ):
                yield json.dumps(event) + "\n"
        except Exception as e:
            yield json.dumps({
                "type": "error", "message": str(e),
            }) + "\n"

    return Response(generate(), mimetype="application/x-ndjson")


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
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route("/validation/tool", methods=["POST"])
@token_required
def agents_validation_tool() -> Response | tuple[Response, int]:
    """
    Execute an approved tool call for the ValidationAgent.

    For ``dt_exec``, streams NDJSON output events.
    For other tools, returns a single JSON response.

    :return: a streaming Response or (JSON, status) tuple
    """
    body = request.get_json(silent=True) or {}
    tool_name = body.get("tool_name", "")
    tool_args = body.get("tool_args", {})
    incident_id = body.get("incident_id")
    if not tool_name:
        return jsonify({"error": "tool_name is required"}), 400
    if tool_name in _DT_TOOLS and incident_id is not None:
        tool_args["incident_id"] = incident_id

    if tool_name in VALIDATION_STREAMING_DISPATCH:
        def generate() -> Generator[str, None, None]:
            """
            Yield NDJSON lines from the streaming tool.

            :return: a generator of newline-delimited JSON strings
            """
            try:
                agent = ValidationAgent()
                for event in agent.execute_tool_stream(
                    tool_name, tool_args,
                ):
                    yield json.dumps(event) + "\n"
            except Exception as e:
                yield json.dumps({
                    "type": "error", "message": str(e),
                }) + "\n"

        return Response(
            generate(), mimetype="application/x-ndjson",
        )

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
def agents_code_step() -> Response | tuple[Response, int]:
    """
    Advance the CodeAgent loop by one step (NDJSON stream).

    :return: an NDJSON streaming Response, or a (JSON, status) tuple
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

    def generate() -> Generator[str, None, None]:
        """
        Yield NDJSON lines from the agent stream.

        :return: a generator of newline-delimited JSON strings
        """
        try:
            if not conversation_history:
                for ev in _redeploy_dt():
                    yield json.dumps(ev) + "\n"
            agent = CodeAgent()
            for event in agent.step_stream(
                system_description=system_description,
                incident_report=incident_report,
                specification=specification,
                operator_feedback=operator_feedback,
                conversation_history=conversation_history,
                images=images,
                model_name=model_name,
            ):
                yield json.dumps(event) + "\n"
        except Exception as e:
            yield json.dumps({
                "type": "error", "message": str(e),
            }) + "\n"

    return Response(generate(), mimetype="application/x-ndjson")


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
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route("/code/tool", methods=["POST"])
@token_required
def agents_code_tool() -> Response | tuple[Response, int]:
    """
    Execute an approved tool call for the CodeAgent.

    For ``dt_exec``, streams NDJSON output events.
    For other tools, returns a single JSON response.

    :return: a streaming Response or (JSON, status) tuple
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
        def generate() -> Generator[str, None, None]:
            """
            Yield NDJSON lines from the streaming tool.

            :return: a generator of newline-delimited JSON strings
            """
            try:
                agent = CodeAgent()
                for event in agent.execute_tool_stream(
                    tool_name, tool_args,
                ):
                    yield json.dumps(event) + "\n"
            except Exception as e:
                yield json.dumps({
                    "type": "error", "message": str(e),
                }) + "\n"

        return Response(
            generate(), mimetype="application/x-ndjson",
        )

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
def agents_code_review_step() -> Response | tuple[Response, int]:
    """
    Advance the CodeReviewerAgent loop by one step (NDJSON stream).

    :return: an NDJSON streaming Response, or a (JSON, status) tuple
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

    def generate() -> Generator[str, None, None]:
        """
        Yield NDJSON lines from the agent stream.

        :return: a generator of newline-delimited JSON strings
        """
        try:
            if not conversation_history:
                for ev in _redeploy_dt():
                    yield json.dumps(ev) + "\n"
            agent = CodeReviewerAgent()
            for event in agent.step_stream(
                system_description=system_description,
                incident_report=incident_report,
                specification=specification,
                operator_feedback=operator_feedback,
                code_report=code_report,
                conversation_history=conversation_history,
                images=images,
                model_name=model_name,
            ):
                yield json.dumps(event) + "\n"
        except Exception as e:
            yield json.dumps({
                "type": "error", "message": str(e),
            }) + "\n"

    return Response(generate(), mimetype="application/x-ndjson")


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
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route("/code-review/tool", methods=["POST"])
@token_required
def agents_code_review_tool() -> Response | tuple[Response, int]:
    """
    Execute an approved tool call for the CodeReviewerAgent.

    For ``dt_exec``, streams NDJSON output events.
    For other tools, returns a single JSON response.

    :return: a streaming Response or (JSON, status) tuple
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
        def generate() -> Generator[str, None, None]:
            """
            Yield NDJSON lines from the streaming tool.

            :return: a generator of newline-delimited JSON strings
            """
            try:
                agent = CodeReviewerAgent()
                for event in agent.execute_tool_stream(
                    tool_name, tool_args,
                ):
                    yield json.dumps(event) + "\n"
            except Exception as e:
                yield json.dumps({
                    "type": "error", "message": str(e),
                }) + "\n"

        return Response(
            generate(), mimetype="application/x-ndjson",
        )

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


@agents_bp.route("/code-manager/step", methods=["POST"])
@token_required
def agents_code_manager_step() -> (
    Response | tuple[Response, int]
):
    """
    Advance the CodeManagerAgent loop by one step (NDJSON).

    :return: an NDJSON streaming Response, or (JSON, status)
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
    max_iterations = body.get("max_iterations", 3)
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

    def generate() -> Generator[str, None, None]:
        """
        Yield NDJSON lines from the agent stream.

        :return: generator of newline-delimited JSON strings
        """
        try:
            if not conversation_history:
                for ev in _redeploy_dt():
                    yield json.dumps(ev) + "\n"
            agent = CodeManagerAgent()
            for event in agent.step_stream(
                system_description=system_description,
                incident_report=incident_report,
                specification=specification,
                operator_feedback=operator_feedback,
                conversation_history=conversation_history,
                images=images,
                model_name=model_name,
                max_iterations=max_iterations,
            ):
                yield json.dumps(event) + "\n"
        except Exception as e:
            yield json.dumps({
                "type": "error", "message": str(e),
            }) + "\n"

    return Response(
        generate(), mimetype="application/x-ndjson",
    )


@agents_bp.route("/code-manager/prompt", methods=["POST"])
@token_required
def agents_code_manager_prompt() -> tuple[Response, int]:
    """
    Render the CodeManagerAgent system prompt.

    :return: a tuple of (JSON response, HTTP status code)
    """
    body = request.get_json(silent=True) or {}
    specification = body.get("specification", "")
    max_iterations = body.get("max_iterations", 3)
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

        def generate() -> Generator[str, None, None]:
            """
            Yield NDJSON lines from the streaming tool.

            :return: generator of newline-delimited JSON
            """
            try:
                agent = CodeManagerAgent()
                for event in agent.execute_tool_stream(
                    tool_name, tool_args,
                    context=context,
                ):
                    yield json.dumps(event) + "\n"
            except Exception as e:
                yield json.dumps({
                    "type": "error",
                    "message": str(e),
                }) + "\n"

        return Response(
            generate(),
            mimetype="application/x-ndjson",
        )

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


@agents_bp.route("/rl/step", methods=["POST"])
@token_required
def agents_rl_step() -> Response | tuple[Response, int]:
    """
    Advance the RlAgent loop by one step (NDJSON stream).

    :return: an NDJSON streaming Response, or a (JSON, status) tuple
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

    def generate() -> Generator[str, None, None]:
        """
        Yield NDJSON lines from the agent stream.

        :return: a generator of newline-delimited JSON strings
        """
        try:
            if not conversation_history:
                env_code = (code_report or {}).get(
                    "generated_code", "",
                )
                if env_code:
                    try:
                        _write_env_to_sandbox(env_code)
                        yield json.dumps({
                            "type": "dt_progress",
                            "message": (
                                "Env code written to "
                                "sandbox"
                            ),
                        }) + "\n"
                    except Exception as e:
                        logger.warning(
                            "Failed to pre-write env: %s",
                            e, exc_info=True,
                        )
                        yield json.dumps({
                            "type": "error",
                            "message": (
                                "Failed to write env code "
                                f"to sandbox: {e}"
                            ),
                        }) + "\n"
                        return
            agent = RlAgent()
            for event in agent.step_stream(
                system_description=system_description,
                incident_report=incident_report,
                specification=specification,
                operator_feedback=operator_feedback,
                code_report=code_report,
                conversation_history=conversation_history,
                images=images,
                model_name=model_name,
                time_limit_minutes=time_limit_minutes,
            ):
                yield json.dumps(event) + "\n"
        except Exception as e:
            yield json.dumps({
                "type": "error", "message": str(e),
            }) + "\n"

    return Response(generate(), mimetype="application/x-ndjson")


@agents_bp.route("/rl/prompt", methods=["POST"])
@token_required
def agents_rl_prompt() -> tuple[Response, int]:
    """
    Render the RlAgent system prompt from the given context.

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
        RlAgent._format_code_report(
            code_report or {},
        )
    )
    time_limit = body.get("time_limit_minutes", 5)
    prompt = RL_PROMPT_TEMPLATE.format(
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
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route("/rl/tool", methods=["POST"])
@token_required
def agents_rl_tool() -> Response | tuple[Response, int]:
    """
    Execute an approved tool call for the RlAgent.

    For ``rl_train``, streams NDJSON progress events.
    For other tools, returns a single JSON response.

    :return: a streaming Response or (JSON, status) tuple
    """
    body = request.get_json(silent=True) or {}
    tool_name = body.get("tool_name", "")
    tool_args = body.get("tool_args", {})
    if not tool_name:
        return jsonify({"error": "tool_name is required"}), 400

    if tool_name in RL_STREAMING_DISPATCH:
        def generate() -> Generator[str, None, None]:
            """
            Yield NDJSON lines from the streaming tool.

            :return: a generator of newline-delimited JSON strings
            """
            try:
                agent = RlAgent()
                for event in agent.execute_tool_stream(
                    tool_name, tool_args,
                ):
                    yield json.dumps(event) + "\n"
            except Exception as e:
                yield json.dumps({
                    "type": "error", "message": str(e),
                }) + "\n"

        return Response(
            generate(), mimetype="application/x-ndjson",
        )

    if tool_name not in RL_TOOL_DISPATCH:
        return jsonify({
            "error": f"Unknown tool: {tool_name}",
        }), 400
    try:
        agent = RlAgent()
        result = agent.execute_tool(tool_name, tool_args)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@agents_bp.route("/dp/step", methods=["POST"])
@token_required
def agents_dp_step() -> Response | tuple[Response, int]:
    """
    Advance the DpAgent loop by one step (NDJSON stream).

    :return: an NDJSON streaming Response, or a (JSON, status) tuple
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

    def generate() -> Generator[str, None, None]:
        """
        Yield NDJSON lines from the agent stream.

        :return: a generator of newline-delimited JSON strings
        """
        try:
            agent = DpAgent()
            for event in agent.step_stream(
                system_description=system_description,
                incident_report=incident_report,
                specification=specification,
                operator_feedback=operator_feedback,
                code_report=code_report,
                conversation_history=conversation_history,
                images=images,
                model_name=model_name,
                time_limit_minutes=time_limit_minutes,
            ):
                yield json.dumps(event) + "\n"
        except Exception as e:
            yield json.dumps({
                "type": "error", "message": str(e),
            }) + "\n"

    return Response(generate(), mimetype="application/x-ndjson")


@agents_bp.route("/dp/prompt", methods=["POST"])
@token_required
def agents_dp_prompt() -> tuple[Response, int]:
    """
    Render the DpAgent system prompt from the given context.

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
        DpAgent._format_code_report(
            code_report or {},
        )
    )
    time_limit = body.get("time_limit_minutes", 5)
    prompt = DP_PROMPT_TEMPLATE.format(
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
    )
    return jsonify({"prompt": prompt}), 200


@agents_bp.route("/dp/tool", methods=["POST"])
@token_required
def agents_dp_tool() -> Response | tuple[Response, int]:
    """
    Execute an approved tool call for the DpAgent.

    For ``dp_solve``, streams NDJSON progress events.
    For other tools, returns a single JSON response.

    :return: a streaming Response or (JSON, status) tuple
    """
    body = request.get_json(silent=True) or {}
    tool_name = body.get("tool_name", "")
    tool_args = body.get("tool_args", {})
    if not tool_name:
        return jsonify({"error": "tool_name is required"}), 400

    if tool_name in DP_STREAMING_DISPATCH:
        def generate() -> Generator[str, None, None]:
            """
            Yield NDJSON lines from the streaming tool.

            :return: a generator of newline-delimited JSON strings
            """
            try:
                agent = DpAgent()
                for event in agent.execute_tool_stream(
                    tool_name, tool_args,
                ):
                    yield json.dumps(event) + "\n"
            except Exception as e:
                yield json.dumps({
                    "type": "error", "message": str(e),
                }) + "\n"

        return Response(
            generate(), mimetype="application/x-ndjson",
        )

    if tool_name not in DP_TOOL_DISPATCH:
        return jsonify({
            "error": f"Unknown tool: {tool_name}",
        }), 400
    try:
        agent = DpAgent()
        result = agent.execute_tool(tool_name, tool_args)
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
    policy_data = None
    if agent_type == "rl":
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
