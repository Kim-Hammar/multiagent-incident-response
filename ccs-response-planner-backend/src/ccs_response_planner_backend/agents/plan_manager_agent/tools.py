"""
Tool dispatch for the PlanManagerAgent.

Provides streaming generator functions that run sub-agents
(CodeManagerAgent, RlAgent, ValidationAgent) internally,
auto-approving tool calls and yielding progress events.
"""
import json
import logging
from typing import Any, Callable, Generator

from ccs_response_planner_backend.agents.code_manager_agent.agent import (
    CodeManagerAgent,
)
from ccs_response_planner_backend.agents.code_manager_agent.tools import (
    STREAMING_TOOL_DISPATCH as CM_STREAMING_DISPATCH,
)
from ccs_response_planner_backend.agents.rl_agent.agent import RlAgent
from ccs_response_planner_backend.agents.rl_agent.tools import (
    STREAMING_TOOL_DISPATCH as RL_STREAMING_DISPATCH,
    TOOL_DISPATCH as RL_TOOL_DISPATCH,
)
from ccs_response_planner_backend.agents.validation_agent.agent import (
    ValidationAgent,
)
from ccs_response_planner_backend.agents.validation_agent.tools import (
    STREAMING_TOOL_DISPATCH as VAL_STREAMING_DISPATCH,
    TOOL_DISPATCH as VAL_TOOL_DISPATCH,
)
from ccs_response_planner_backend.db.database_facade import (
    DatabaseFacade,
)

logger = logging.getLogger(__name__)

MAX_INNER_STEPS = 50

_OUTPUT_LIMIT = 2000


def _truncate_result(
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    Return a copy of the tool result with long string values
    truncated for the sub_event payload.

    :param result: the original tool result dict
    :return: a truncated copy of the result
    """
    out: dict[str, Any] = {}
    for key, val in result.items():
        if key == "image":
            out[key] = val
        elif isinstance(val, str) and len(val) > _OUTPUT_LIMIT:
            out[key] = (
                val[:_OUTPUT_LIMIT] + "... (truncated)"
            )
        else:
            out[key] = val
    return out


def _write_env_to_sandbox(env_code: str) -> None:
    """
    Write the MDP env code to /workspace/_env.py in the sandbox.

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


def _run_sub_agent_loop(
    agent: Any,
    step_kwargs: dict[str, Any],
    agent_streaming_dispatch: dict[str, Any],
    agent_tool_dispatch: dict[str, Any],
    agent_label: str,
    report_event_type: str,
    context: dict[str, Any] | None = None,
    max_steps: int = MAX_INNER_STEPS,
) -> Generator[dict[str, Any], None, None]:
    """
    Run a sub-agent's full multi-step loop, auto-approving
    all tool calls. Yields sub_event wrappers and output_chunk
    events.

    :param agent: the agent instance
    :param step_kwargs: kwargs for agent.step_stream()
    :param agent_streaming_dispatch: streaming tool dispatch
    :param agent_tool_dispatch: non-streaming tool dispatch
    :param agent_label: label for log messages
    :param report_event_type: event type for the final report
    :param context: optional context dict for streaming tools
    :param max_steps: maximum number of agent turns
    :return: generator of event dicts
    """
    conversation_history: list[dict[str, Any]] = []
    step_kwargs["conversation_history"] = (
        conversation_history
    )
    final_report = None

    for step_num in range(max_steps):
        yield {
            "type": "output_chunk",
            "text": (
                f"[{agent_label}] Step "
                f"{step_num + 1}...\n"
            ),
        }

        pending_tool = None
        for event in agent.step_stream(**step_kwargs):
            etype = event.get("type")

            if etype == "system_prompt":
                yield {
                    "type": "sub_event",
                    "event": {
                        "type": "prompt",
                        "text": event.get("text", ""),
                    },
                }
            elif etype == "thinking":
                yield {
                    "type": "sub_event",
                    "event": {
                        "type": "thinking_delta",
                        "text": event.get("delta", ""),
                    },
                }
            elif etype == "text":
                yield {
                    "type": "sub_event",
                    "event": {
                        "type": "text_delta",
                        "text": event.get("delta", ""),
                    },
                }
            elif etype == report_event_type:
                report_key = report_event_type
                final_report = event.get(
                    report_key, {},
                )
                conversation_history.append({
                    "role": "model",
                    "type": report_event_type,
                    report_key: final_report,
                })
                yield {
                    "type": "sub_event",
                    "event": {"type": "report"},
                }
                yield {
                    "type": "output_chunk",
                    "text": (
                        f"[{agent_label}] Report "
                        f"produced.\n"
                    ),
                }
            elif etype == "context_usage":
                yield {
                    "type": "sub_event",
                    "event": {
                        "type": "context_usage",
                        "prompt_tokens": event.get(
                            "prompt_tokens", 0,
                        ),
                        "candidates_tokens": event.get(
                            "candidates_tokens", 0,
                        ),
                        "total_tokens": event.get(
                            "total_tokens", 0,
                        ),
                        "context_limit": event.get(
                            "context_limit", 0,
                        ),
                    },
                }
            elif etype == "tool_proposal":
                pending_tool = event

        if final_report is not None:
            break

        if pending_tool:
            tool_name = pending_tool.get(
                "tool_name", "",
            )
            tool_args = pending_tool.get(
                "tool_args", {},
            )
            yield {
                "type": "sub_event",
                "event": {
                    "type": "tool_call",
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                },
            }
            yield {
                "type": "output_chunk",
                "text": (
                    f"[{agent_label}] Running tool: "
                    f"{tool_name}...\n"
                ),
            }
            conversation_history.append({
                "role": "model",
                "type": "tool_proposal",
                "tool_name": tool_name,
                "tool_args": tool_args,
                "rationale": pending_tool.get(
                    "rationale", "",
                ),
                "_model_parts": pending_tool.get(
                    "_model_parts",
                ),
                "_anthropic_content": pending_tool.get(
                    "_anthropic_content",
                ),
                "_tool_use_id": pending_tool.get(
                    "_tool_use_id",
                ),
                "_vendor": pending_tool.get("_vendor"),
            })
            conversation_history.append({
                "role": "user",
                "type": "tool_approval",
                "tool_name": tool_name,
                "approved": True,
            })

            if tool_name in agent_streaming_dispatch:
                collected: list[dict[str, Any]] = []
                tool_result: dict[str, Any] = {}
                try:
                    ctx = context if context else {}
                    for tool_event in (
                        agent.execute_tool_stream(
                            tool_name, tool_args,
                            context=ctx,
                        )
                    ):
                        te_type = tool_event.get("type")
                        if te_type == "sub_event":
                            inner = tool_event["event"]
                            yield {
                                "type": "sub_event",
                                "event": {
                                    "type": "nested_event",
                                    "event": inner,
                                },
                            }
                            collected.append(inner)
                        elif te_type == "output_chunk":
                            yield tool_event
                        elif te_type == "done":
                            done_result = (
                                tool_event.get(
                                    "result", {},
                                )
                            )
                            if done_result:
                                tool_result = done_result
                            if tool_event.get("error"):
                                tool_result["error"] = (
                                    tool_event["error"]
                                )
                            if tool_event.get("stderr"):
                                tool_result["stderr"] = (
                                    tool_event["stderr"]
                                )
                        elif te_type == "error":
                            tool_result["error"] = (
                                tool_event.get(
                                    "message", "error",
                                )
                            )
                            collected.append(tool_event)
                        else:
                            yield {
                                "type": "sub_event",
                                "event": {
                                    "type": "nested_event",
                                    "event": tool_event,
                                },
                            }
                except Exception as e:
                    tool_result = {"error": str(e)}
                sub_result = _truncate_result(
                    tool_result,
                )
                yield {
                    "type": "sub_event",
                    "event": {
                        "type": "tool_result",
                        "tool_name": tool_name,
                        "result": sub_result,
                        "subEvents": collected,
                    },
                }
                conversation_history.append({
                    "role": "tool",
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "result": tool_result,
                })
            else:
                try:
                    result_obj = agent.execute_tool(
                        tool_name, tool_args,
                    )
                    tool_result = result_obj.get(
                        "result",
                        result_obj.get("error", {}),
                    )
                    if result_obj.get("error"):
                        tool_result = {
                            "error": result_obj["error"],
                        }
                except Exception as e:
                    tool_result = {"error": str(e)}
                conversation_history.append({
                    "role": "tool",
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "result": tool_result,
                })
                sub_result = _truncate_result(
                    tool_result
                    if isinstance(tool_result, dict)
                    else {"result": str(tool_result)},
                )
                output = ""
                if isinstance(tool_result, dict):
                    output = tool_result.get(
                        "output",
                        tool_result.get("error", ""),
                    )
                yield {
                    "type": "sub_event",
                    "event": {
                        "type": "tool_result",
                        "tool_name": tool_name,
                        "result": sub_result,
                    },
                }
                yield {
                    "type": "output_chunk",
                    "text": (
                        f"[{agent_label}] {tool_name} "
                        f"result: "
                        f"{str(output)[:500]}\n"
                    ),
                }


def run_code_manager_stream(
    context: dict[str, Any],
    validation_feedback: str = "",
) -> Generator[dict[str, Any], None, None]:
    """
    Run the CodeManagerAgent sub-agent to completion.

    Runs the full CodeManager loop (CodeAgent + CodeReviewerAgent
    internally), streaming events back. The CodeManager's own
    streaming tools produce nested_event wrappers (3-level nesting).

    :param context: dict with system_description, incident_report,
        specification, operator_feedback, images, username
    :param validation_feedback: feedback from validation to revise
    :return: generator yielding event dicts
    """
    agent = CodeManagerAgent()
    step_kwargs: dict[str, Any] = {
        "system_description": context.get(
            "system_description", "",
        ),
        "incident_report": context.get(
            "incident_report", "",
        ),
        "specification": context.get(
            "specification", "",
        ),
        "operator_feedback": context.get(
            "operator_feedback", "",
        ),
        "images": context.get("images"),
        "validation_feedback": validation_feedback,
        "conversation_history": [],
        "model_name": context.get(
            "code_manager_model",
        ),
        "max_iterations": context.get(
            "code_manager_iterations", 3,
        ),
    }
    cm_context = {
        **context,
        "last_code_report": {},
        "review_count": 0,
        "code_agent_model": context.get(
            "code_agent_model",
        ),
        "reviewer_agent_model": context.get(
            "reviewer_agent_model",
        ),
        "dt_config": context.get("dt_config"),
    }

    code_report: dict[str, Any] = {}
    orchestrator_report: dict[str, Any] = {}
    conversation_history: list[dict[str, Any]] = []
    step_kwargs["conversation_history"] = (
        conversation_history
    )

    for step_num in range(MAX_INNER_STEPS):
        yield {
            "type": "output_chunk",
            "text": (
                f"[CodeManager] Step "
                f"{step_num + 1}...\n"
            ),
        }

        pending_tool = None
        for event in agent.step_stream(**step_kwargs):
            etype = event.get("type")

            if etype == "system_prompt":
                yield {
                    "type": "sub_event",
                    "event": {
                        "type": "prompt",
                        "text": event.get("text", ""),
                    },
                }
            elif etype == "thinking":
                yield {
                    "type": "sub_event",
                    "event": {
                        "type": "thinking_delta",
                        "text": event.get("delta", ""),
                    },
                }
            elif etype == "text":
                yield {
                    "type": "sub_event",
                    "event": {
                        "type": "text_delta",
                        "text": event.get("delta", ""),
                    },
                }
            elif etype == "orchestrator_report":
                orchestrator_report = event.get(
                    "orchestrator_report", {},
                )
                yield {
                    "type": "sub_event",
                    "event": {"type": "report"},
                }
                yield {
                    "type": "output_chunk",
                    "text": (
                        "[CodeManager] Orchestrator "
                        "report produced.\n"
                    ),
                }
            elif etype == "context_usage":
                yield {
                    "type": "sub_event",
                    "event": {
                        "type": "context_usage",
                        "prompt_tokens": event.get(
                            "prompt_tokens", 0,
                        ),
                        "candidates_tokens": event.get(
                            "candidates_tokens", 0,
                        ),
                        "total_tokens": event.get(
                            "total_tokens", 0,
                        ),
                        "context_limit": event.get(
                            "context_limit", 0,
                        ),
                    },
                }
            elif etype == "tool_proposal":
                pending_tool = event

        if orchestrator_report:
            break

        if pending_tool:
            tool_name = pending_tool.get(
                "tool_name", "",
            )
            tool_args = pending_tool.get(
                "tool_args", {},
            )
            yield {
                "type": "sub_event",
                "event": {
                    "type": "tool_call",
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                },
            }
            yield {
                "type": "output_chunk",
                "text": (
                    f"[CodeManager] Running tool: "
                    f"{tool_name}...\n"
                ),
            }
            conversation_history.append({
                "role": "model",
                "type": "tool_proposal",
                "tool_name": tool_name,
                "tool_args": tool_args,
                "rationale": pending_tool.get(
                    "rationale", "",
                ),
                "_model_parts": pending_tool.get(
                    "_model_parts",
                ),
                "_anthropic_content": pending_tool.get(
                    "_anthropic_content",
                ),
                "_tool_use_id": pending_tool.get(
                    "_tool_use_id",
                ),
                "_vendor": pending_tool.get("_vendor"),
            })
            conversation_history.append({
                "role": "user",
                "type": "tool_approval",
                "tool_name": tool_name,
                "approved": True,
            })

            if tool_name in CM_STREAMING_DISPATCH:
                collected: list[dict[str, Any]] = []
                tool_result: dict[str, Any] = {}
                if tool_name == "run_code_reviewer_agent":
                    cm_context["review_count"] = (
                        cm_context.get("review_count", 0)
                        + 1
                    )
                    cm_context["last_code_report"] = (
                        code_report
                    )
                try:
                    for tool_event in (
                        agent.execute_tool_stream(
                            tool_name, tool_args,
                            context=cm_context,
                        )
                    ):
                        te_type = tool_event.get("type")
                        if te_type == "sub_event":
                            inner = tool_event["event"]
                            yield {
                                "type": "sub_event",
                                "event": {
                                    "type": (
                                        "nested_event"
                                    ),
                                    "event": inner,
                                },
                            }
                            collected.append(inner)
                        elif te_type == "output_chunk":
                            yield tool_event
                        elif te_type == "done":
                            done_result = (
                                tool_event.get(
                                    "result", {},
                                )
                            )
                            if done_result:
                                tool_result = (
                                    done_result
                                )
                            if tool_event.get("error"):
                                tool_result["error"] = (
                                    tool_event["error"]
                                )
                            if tool_event.get("stderr"):
                                tool_result["stderr"] = (
                                    tool_event["stderr"]
                                )
                        elif te_type == "error":
                            tool_result["error"] = (
                                tool_event.get(
                                    "message",
                                    "error",
                                )
                            )
                            collected.append(
                                tool_event,
                            )
                except Exception as e:
                    tool_result = {"error": str(e)}

                if tool_name == "run_code_agent":
                    code_report = tool_result.get(
                        "code_report", {},
                    )

                sub_result = _truncate_result(
                    tool_result,
                )
                yield {
                    "type": "sub_event",
                    "event": {
                        "type": "tool_result",
                        "tool_name": tool_name,
                        "result": sub_result,
                        "subEvents": collected,
                    },
                }
                conversation_history.append({
                    "role": "tool",
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "result": tool_result,
                })
            else:
                try:
                    result_obj = agent.execute_tool(
                        tool_name, tool_args,
                    )
                    tool_result = result_obj.get(
                        "result", {},
                    )
                    if result_obj.get("error"):
                        tool_result = {
                            "error": result_obj["error"],
                        }
                except Exception as e:
                    tool_result = {"error": str(e)}
                conversation_history.append({
                    "role": "tool",
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "result": tool_result,
                })
                sub_result = _truncate_result(
                    tool_result,
                )
                yield {
                    "type": "sub_event",
                    "event": {
                        "type": "tool_result",
                        "tool_name": tool_name,
                        "result": sub_result,
                    },
                }

    if not orchestrator_report:
        orchestrator_report = {
            "executive_summary": (
                "CodeManager did not complete within "
                "the step limit."
            ),
            "iterations": 0,
            "final_verdict": "major_issues",
            "code_report_summary": "",
            "review_report_summary": "",
        }

    try:
        DatabaseFacade.save_agent_report(
            agent_type="code_manager",
            report={
                **orchestrator_report,
                "final_code_report": code_report,
            },
            username=context.get("username", "system"),
        )
    except Exception as e:
        logger.warning(
            "Failed to save code_manager report: %s", e,
        )

    yield {
        "type": "done",
        "result": {
            "code_report": code_report,
            "orchestrator_report": orchestrator_report,
        },
    }


def run_rl_agent_stream(
    context: dict[str, Any],
) -> Generator[dict[str, Any], None, None]:
    """
    Run the RlAgent sub-agent to completion.

    Requires code_report in context. Handles env code
    setup, then runs the RL agent loop.

    :param context: dict with code_report, and the
        standard incident context fields
    :return: generator yielding event dicts
    """
    code_report = context.get("code_report", {})
    env_code = code_report.get("generated_code", "")
    if env_code:
        try:
            _write_env_to_sandbox(env_code)
            yield {
                "type": "output_chunk",
                "text": (
                    "[RlAgent] Env code written to "
                    "sandbox.\n"
                ),
            }
        except Exception as e:
            logger.warning(
                "Failed to write env to sandbox: %s",
                e, exc_info=True,
            )
            yield {
                "type": "output_chunk",
                "text": (
                    f"[RlAgent] Warning: failed to write "
                    f"env code: {e}\n"
                ),
            }

    agent = RlAgent()
    step_kwargs: dict[str, Any] = {
        "system_description": context.get(
            "system_description", "",
        ),
        "incident_report": context.get(
            "incident_report", "",
        ),
        "specification": context.get(
            "specification", "",
        ),
        "operator_feedback": context.get(
            "operator_feedback", "",
        ),
        "code_report": code_report,
        "images": context.get("images"),
        "conversation_history": [],
        "model_name": context.get(
            "rl_agent_model",
        ),
        "time_limit_minutes": context.get(
            "rl_time_limit_minutes", 5,
        ),
        "prev_planner_report": context.get(
            "planner_report",
        ),
        "prev_validation_report": context.get(
            "validation_report",
        ),
    }

    planner_report: dict[str, Any] | None = None
    response_plan = ""

    for ev in _run_sub_agent_loop(
        agent=agent,
        step_kwargs=step_kwargs,
        agent_streaming_dispatch=RL_STREAMING_DISPATCH,
        agent_tool_dispatch=RL_TOOL_DISPATCH,
        agent_label="RlAgent",
        report_event_type="planner_report",
        context=context,
    ):
        yield ev

    conv = step_kwargs.get("conversation_history", [])
    for entry in reversed(conv):
        if entry.get("type") == "planner_report":
            planner_report = entry.get(
                "planner_report", {},
            )
            break

    for entry in reversed(conv):
        etype = entry.get("type")
        if etype == "planner_report":
            pr = entry.get("planner_report", {})
            planner_report = pr
            response_plan = pr.get(
                "response_plan", "",
            )
            break

    if planner_report is None:
        planner_report = {
            "executive_summary": (
                "RlAgent did not produce a report "
                "within the step limit."
            ),
            "response_plan": "",
        }

    try:
        DatabaseFacade.save_agent_report(
            agent_type="rl",
            report=planner_report,
            username=context.get("username", "system"),
        )
    except Exception as e:
        logger.warning(
            "Failed to save rl report: %s", e,
        )

    yield {
        "type": "done",
        "result": {
            "planner_report": planner_report,
            "response_plan": response_plan,
        },
    }


def run_validation_agent_stream(
    context: dict[str, Any],
) -> Generator[dict[str, Any], None, None]:
    """
    Run the ValidationAgent sub-agent to completion.

    Requires planner_report, code_report, and response_plan
    in context.

    :param context: dict with planner_report, code_report,
        response_plan, and the standard incident context
    :return: generator yielding event dicts
    """
    from ccs_response_planner_backend.docker_manager.docker_manager import (
        DockerManager,
    )
    from ccs_response_planner_backend.constants.constants import (
        DIGITAL_TWIN,
    )

    yield {
        "type": "output_chunk",
        "text": (
            "[ValidationAgent] Redeploying digital "
            "twin for fresh state...\n"
        ),
    }
    config = DatabaseFacade.get_digital_twin_config()
    if config is None:
        config = DIGITAL_TWIN.DEFAULT_CONFIG
    for item in DockerManager.stop():
        msg = item.get("message", "")
        if item.get("type") == "progress" and msg:
            logger.info("DT redeploy (stop): %s", msg)
    for item in DockerManager.deploy(config):
        msg = item.get("message", "")
        if item.get("type") == "progress" and msg:
            logger.info("DT redeploy (deploy): %s", msg)
    yield {
        "type": "output_chunk",
        "text": (
            "[ValidationAgent] Digital twin ready.\n"
        ),
    }

    planner_report = context.get(
        "planner_report", {},
    )
    code_report = context.get("code_report", {})
    response_plan = context.get("response_plan", "")
    specification = context.get("specification", "")
    if not specification:
        specification = json.dumps(
            DIGITAL_TWIN.DEFAULT_CONFIG[
                "specification_commands"
            ],
            indent=2,
        )

    agent = ValidationAgent()
    step_kwargs: dict[str, Any] = {
        "system_description": context.get(
            "system_description", "",
        ),
        "incident_report": context.get(
            "incident_report", "",
        ),
        "response_plan": response_plan,
        "specification": specification,
        "planner_report": planner_report,
        "code_report": code_report,
        "images": context.get("images"),
        "has_policy": True,
        "conversation_history": [],
        "model_name": context.get(
            "validation_agent_model",
        ),
        "dt_config": context.get("dt_config"),
        "validation_feedback": context.get(
            "validation_report",
        ),
    }

    for ev in _run_sub_agent_loop(
        agent=agent,
        step_kwargs=step_kwargs,
        agent_streaming_dispatch=VAL_STREAMING_DISPATCH,
        agent_tool_dispatch=VAL_TOOL_DISPATCH,
        agent_label="ValidationAgent",
        report_event_type="validation_report",
        context=context,
        max_steps=150,
    ):
        yield ev

    conv = step_kwargs.get("conversation_history", [])
    validation_report: dict[str, Any] | None = None
    for entry in reversed(conv):
        if entry.get("type") == "validation_report":
            validation_report = entry.get(
                "validation_report", {},
            )
            break

    if validation_report is None:
        validation_report = {
            "executive_summary": (
                "ValidationAgent did not produce a "
                "report within the step limit."
            ),
            "overall_verdict": "major_issues",
        }

    try:
        DatabaseFacade.save_agent_report(
            agent_type="validation",
            report=validation_report,
            username=context.get("username", "system"),
        )
    except Exception as e:
        logger.warning(
            "Failed to save validation report: %s", e,
        )

    yield {
        "type": "done",
        "result": {
            "validation_report": validation_report,
        },
    }


TOOL_DISPATCH: dict[
    str, Callable[..., dict[str, Any]]
] = {}

STREAMING_TOOL_DISPATCH: dict[
    str,
    Callable[
        ...,
        Generator[dict[str, Any], None, None],
    ],
] = {
    "run_code_manager": run_code_manager_stream,
    "run_rl_agent": run_rl_agent_stream,
    "run_validation_agent": (
        run_validation_agent_stream
    ),
}
