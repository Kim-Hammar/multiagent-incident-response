"""
Tool dispatch for the OrchestratorAgent.

Provides streaming generator functions that run sub-agents
(ReportManagerAgent and PlanManagerAgent) internally,
auto-approving tool calls and yielding progress events.
"""
import json
import logging
import time
from typing import Any, Callable, Generator

import httpx

from ccs_response_planner_backend.agents.stream_timeout import (
    AgentTimeoutError,
)

from ccs_response_planner_backend.agents.report_manager_agent.agent import (
    ReportManagerAgent,
)
from ccs_response_planner_backend.agents.report_manager_agent.tools import (
    STREAMING_TOOL_DISPATCH as RM_STREAMING_DISPATCH,
)
from ccs_response_planner_backend.agents.plan_manager_agent.agent import (
    PlanManagerAgent,
)
from ccs_response_planner_backend.agents.plan_manager_agent.tools import (
    STREAMING_TOOL_DISPATCH as PM_STREAMING_DISPATCH,
)
from ccs_response_planner_backend.agents.pentest_agent.agent import (
    PentestAgent,
)
from ccs_response_planner_backend.agents.pentest_agent.tools import (
    STREAMING_TOOL_DISPATCH as PT_STREAMING_DISPATCH,
)
from ccs_response_planner_backend.db.database_facade import (
    DatabaseFacade,
)

logger = logging.getLogger(__name__)

MAX_INNER_STEPS = 50

_OUTPUT_LIMIT = 2000

_FINAL_REPORT_TYPES = {
    "assessment", "report_review", "code_report",
    "review_report", "planner_report",
    "validation_report", "orchestrator_report",
    "report_manager_report", "plan_manager_report",
}

_INTERNAL_KEYS = {
    "_model_parts", "_anthropic_content",
    "_tool_use_id", "_vendor",
}


_SKIP_TYPES = {"prompt", "context_usage", "nested_event"}


def _timeout_step_stream(
    agent: Any,
    step_kwargs: dict[str, Any],
    step_start: float,
    step_num: int,
    agent_label: str,
) -> Generator[dict[str, Any], None, None]:
    """
    Iterate ``agent.step_stream`` and convert timeout
    errors into :class:`AgentTimeoutError`.

    :param agent: the agent instance to call
    :param step_kwargs: kwargs passed to step_stream
    :param step_start: monotonic timestamp of step start
    :param step_num: zero-based step index
    :param agent_label: human name for error messages
    :return: events from step_stream
    """
    model = step_kwargs.get("model_name", "unknown")
    logger.info(
        "%s step %d starting (model=%s)",
        agent_label, step_num + 1, model,
    )
    try:
        yield from agent.step_stream(**step_kwargs)
    except (
        TimeoutError, OSError,
        httpx.TimeoutException,
    ) as e:
        elapsed = round(
            time.monotonic() - step_start,
        )
        logger.error(
            "%s step %d TIMED OUT after %ds "
            "(model=%s): %s: %s",
            agent_label, step_num + 1, elapsed,
            model, type(e).__name__, e,
        )
        raise AgentTimeoutError(
            f"{agent_label} step {step_num + 1} timed "
            f"out after {elapsed}s: {e}",
            agent_name=agent_label,
            step_number=step_num + 1,
            model_name=step_kwargs.get(
                "model_name", "",
            ),
            elapsed_seconds=(
                time.monotonic() - step_start
            ),
        ) from e


def _process_collected_events(
    collected: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Process raw streaming sub-events into a compact format
    for DB persistence and history display.

    Accumulates thinking_delta/text_delta into reasoning/text,
    filters prompts/context_usage/nested_events, recursively
    processes subEvents on tool_results, strips internal keys.

    :param collected: raw events from streaming tool execution
    :return: processed events for history storage
    """
    result: list[dict[str, Any]] = []
    for ev in collected:
        ev_type = ev.get("type")
        if ev_type in _SKIP_TYPES:
            continue
        if ev_type == "thinking_delta":
            text = ev.get("text", "")
            if (
                result
                and result[-1].get("type") == "reasoning"
            ):
                result[-1]["text"] += text
            else:
                result.append(
                    {"type": "reasoning", "text": text}
                )
            continue
        if ev_type == "text_delta":
            text = ev.get("text", "")
            if (
                result
                and result[-1].get("type") == "text"
            ):
                result[-1]["text"] += text
            else:
                result.append(
                    {"type": "text", "text": text}
                )
            continue
        cleaned: dict[str, Any] = {
            k: v for k, v in ev.items()
            if k not in _INTERNAL_KEYS
        }
        if ev_type == "tool_result" and cleaned.get(
            "subEvents"
        ):
            cleaned["subEvents"] = (
                _process_collected_events(
                    cleaned["subEvents"]
                )
            )
        result.append(cleaned)
    return result


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
        if key in ("image", "attack_path_image"):
            out[key] = val
        elif isinstance(val, str) and len(val) > _OUTPUT_LIMIT:
            out[key] = (
                val[:_OUTPUT_LIMIT] + "... (truncated)"
            )
        else:
            out[key] = val
    return out


def run_report_manager_stream(
    context: dict[str, Any],
) -> Generator[dict[str, Any], None, None]:
    """
    Run the ReportManagerAgent sub-agent to completion.

    Runs the full ReportManager loop (ReportAgent +
    ReportReviewerAgent internally), streaming events back.
    The ReportManager's own streaming tools produce
    nested_event wrappers (3-level nesting).

    :param context: dict with system_description,
        security_alerts, operator_feedback, images,
        report_manager_model, report_agent_model,
        reviewer_agent_model, username, dt_config
    :return: generator yielding event dicts
    """
    agent = ReportManagerAgent()
    conversation_history: list[dict[str, Any]] = []
    validation_feedback = context.get(
        "validation_feedback", "",
    )
    step_kwargs: dict[str, Any] = {
        "system_description": context.get(
            "system_description", "",
        ),
        "security_alerts": context.get(
            "security_alerts", "",
        ),
        "operator_feedback": context.get(
            "operator_feedback", "",
        ),
        "images": context.get("images"),
        "model_name": context.get(
            "report_manager_model",
        ),
        "max_iterations": context.get(
            "report_manager_iterations", 2,
        ),
        "validation_feedback": validation_feedback,
        "compaction_model": context.get(
            "compaction_model",
        ),
        "compaction_threshold": context.get(
            "report_manager_compaction", 0.8,
        ),
        "conversation_history": conversation_history,
    }
    rm_context: dict[str, Any] = {
        **context,
        "report_agent_model": context.get(
            "report_agent_model",
        ),
        "reviewer_agent_model": context.get(
            "reviewer_agent_model",
        ),
        "dt_config": context.get("dt_config"),
        "dt_enabled": context.get("dt_enabled", True),
    }

    report_manager_report: dict[str, Any] = {}
    assessment: dict[str, Any] = {}
    attack_path_img: str | None = None

    for step_num in range(MAX_INNER_STEPS):
        yield {
            "type": "output_chunk",
            "text": (
                f"[ReportManager] Step "
                f"{step_num + 1}...\n"
            ),
        }

        pending_tool = None
        step_reasoning = ""
        step_start = time.monotonic()
        for event in _timeout_step_stream(
            agent, step_kwargs, step_start,
            step_num, "ReportManager",
        ):
            etype = event.get("type")

            if etype == "system_prompt":
                yield {
                    "type": "sub_event",
                    "event": {
                        "type": "prompt",
                        "text": event.get("text", ""),
                        "images": event.get("images", []),
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
                step_reasoning += event.get(
                    "delta", "",
                )
            elif etype == "text":
                yield {
                    "type": "sub_event",
                    "event": {
                        "type": "text_delta",
                        "text": event.get("delta", ""),
                    },
                }
                step_reasoning += event.get(
                    "delta", "",
                )
            elif etype == "report_manager_report":
                report_manager_report = event.get(
                    "report_manager_report", {},
                )
                yield {
                    "type": "sub_event",
                    "event": {"type": "report"},
                }
                yield {
                    "type": "output_chunk",
                    "text": (
                        "[ReportManager] Report "
                        "produced.\n"
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
            elif etype == "context_compaction":
                yield {
                    "type": "sub_event",
                    "event": event,
                }
            elif etype == "tool_proposal":
                pending_tool = event

        if step_reasoning:
            conversation_history.append({
                "role": "model",
                "type": "reasoning",
                "text": step_reasoning,
            })

        if report_manager_report:
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
                    f"[ReportManager] Running tool: "
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
                "_vendor": pending_tool.get(
                    "_vendor",
                ),
            })
            conversation_history.append({
                "role": "user",
                "type": "tool_approval",
                "tool_name": tool_name,
                "approved": True,
            })

            if tool_name in RM_STREAMING_DISPATCH:
                collected: list[dict[str, Any]] = []
                tool_result: dict[str, Any] = {}
                try:
                    for tool_event in (
                        agent.execute_tool_stream(
                            tool_name, tool_args,
                            context=rm_context,
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
                            done_result = tool_event.get(
                                "result",
                            )
                            if done_result is not None:
                                tool_result = (
                                    done_result
                                )
                            else:
                                tool_result = {
                                    k: v
                                    for k, v in
                                    tool_event.items()
                                    if k != "type"
                                }
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
                except (
                    TimeoutError, AgentTimeoutError,
                    OSError,
                ):
                    raise
                except Exception as e:
                    tool_result = {"error": str(e)}

                if tool_name == "run_report_agent":
                    assessment = tool_result.get(
                        "assessment", {},
                    )
                    attack_path_img = tool_result.get(
                        "attack_path_image",
                    )
                    rm_context["last_assessment"] = (
                        assessment
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
                    },
                }
                processed_sub = (
                    _process_collected_events(collected)
                )
                tool_hist_entry: dict[str, Any] = {
                    "role": "tool",
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "result": tool_result,
                }
                if processed_sub:
                    tool_hist_entry["subEvents"] = (
                        processed_sub
                    )
                conversation_history.append(
                    tool_hist_entry
                )
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
                except (
                    TimeoutError, AgentTimeoutError,
                    OSError,
                ):
                    raise
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

    if not report_manager_report:
        report_manager_report = {
            "executive_summary": (
                "ReportManager did not complete within "
                "the step limit."
            ),
            "report_summary": "",
        }

    if not assessment:
        for entry in reversed(conversation_history):
            if (
                entry.get("type") == "tool_result"
                and entry.get("tool_name")
                == "run_report_agent"
            ):
                result = entry.get("result", {})
                assessment = result.get(
                    "assessment", {},
                )
                if not attack_path_img:
                    attack_path_img = result.get(
                        "attack_path_image",
                    )
                break

    saved_assessment = dict(assessment) if assessment else {}
    if attack_path_img:
        saved_assessment["attack_path_image"] = (
            attack_path_img
        )
    filtered_history = [
        {k: v for k, v in e.items()
         if k not in _INTERNAL_KEYS}
        for e in conversation_history
        if e.get("type") not in _FINAL_REPORT_TYPES
    ]
    try:
        DatabaseFacade.save_agent_report(
            agent_type="report_manager",
            report={
                **report_manager_report,
                "final_assessment": saved_assessment,
            },
            username=context.get(
                "username", "system",
            ),
            incident_id=context.get("incident_id"),
            conversation_history=filtered_history,
        )
    except Exception as e:
        logger.warning(
            "Failed to save report_manager report: "
            "%s", e,
        )

    done_result = {
        "report_manager_report": (
            report_manager_report
        ),
        "assessment": assessment,
    }
    if attack_path_img:
        done_result["attack_path_image"] = (
            attack_path_img
        )
    yield {
        "type": "done",
        "result": done_result,
    }


def run_pentest_agent_stream(
    context: dict[str, Any],
) -> Generator[dict[str, Any], None, None]:
    """
    Run the PentestAgent sub-agent to completion.

    Extracts the attack path from the assessment in context
    and runs the PentestAgent loop, auto-approving tool calls
    (dt_exec, dt_restart) and streaming progress events.

    :param context: dict with assessment, system_description,
        dt_config, pentest_agent_model, username
    :return: generator yielding event dicts
    """
    agent = PentestAgent()
    conversation_history: list[dict[str, Any]] = []

    assessment = context.get("assessment", {})
    attack_path = ""
    if isinstance(assessment, dict):
        attack_path = assessment.get(
            "attack_vector_analysis", "",
        )
        if not attack_path:
            attack_path = json.dumps(
                assessment, indent=2, default=str,
            )

    system_description = context.get(
        "system_description", "",
    )
    dt_config = context.get("dt_config")
    step_kwargs: dict[str, Any] = {
        "system_description": system_description,
        "attack_path": attack_path,
        "model_name": context.get(
            "pentest_agent_model",
        ),
        "dt_config": dt_config,
        "compaction_model": context.get(
            "compaction_model",
        ),
        "compaction_threshold": context.get(
            "pentest_agent_compaction", 0.8,
        ),
        "conversation_history": conversation_history,
        "dt_enabled": context.get(
            "dt_enabled", True,
        ),
    }

    pentest_report: dict[str, Any] = {}

    for step_num in range(MAX_INNER_STEPS):
        yield {
            "type": "output_chunk",
            "text": (
                f"[PentestAgent] Step "
                f"{step_num + 1}...\n"
            ),
        }

        pending_tool = None
        step_reasoning = ""
        step_start = time.monotonic()
        for event in _timeout_step_stream(
            agent, step_kwargs, step_start,
            step_num, "PentestAgent",
        ):
            etype = event.get("type")

            if etype == "system_prompt":
                yield {
                    "type": "sub_event",
                    "event": {
                        "type": "prompt",
                        "text": event.get("text", ""),
                        "images": event.get(
                            "images", [],
                        ),
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
                step_reasoning += event.get(
                    "delta", "",
                )
            elif etype == "text":
                yield {
                    "type": "sub_event",
                    "event": {
                        "type": "text_delta",
                        "text": event.get("delta", ""),
                    },
                }
                step_reasoning += event.get(
                    "delta", "",
                )
            elif etype == "pentest_report":
                pentest_report = event.get(
                    "pentest_report", {},
                )
                yield {
                    "type": "sub_event",
                    "event": {"type": "report"},
                }
                yield {
                    "type": "output_chunk",
                    "text": (
                        "[PentestAgent] Report "
                        "produced.\n"
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
            elif etype == "context_compaction":
                yield {
                    "type": "sub_event",
                    "event": event,
                }
            elif etype == "tool_proposal":
                pending_tool = event

        if step_reasoning:
            conversation_history.append({
                "role": "model",
                "type": "reasoning",
                "text": step_reasoning,
            })

        if pentest_report:
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
                    f"[PentestAgent] Running tool: "
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
                "_vendor": pending_tool.get(
                    "_vendor",
                ),
            })
            conversation_history.append({
                "role": "user",
                "type": "tool_approval",
                "tool_name": tool_name,
                "approved": True,
            })

            if tool_name in PT_STREAMING_DISPATCH:
                collected: list[dict[str, Any]] = []
                tool_result: dict[str, Any] = {}
                try:
                    for tool_event in (
                        agent.execute_tool_stream(
                            tool_name, tool_args,
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
                                tool_event.get("result")
                            )
                            if done_result is not None:
                                tool_result = (
                                    done_result
                                )
                            else:
                                tool_result = {
                                    k: v
                                    for k, v in
                                    tool_event.items()
                                    if k != "type"
                                }
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
                except (
                    TimeoutError, AgentTimeoutError,
                    OSError,
                ):
                    raise
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
                    },
                }
                processed_sub = (
                    _process_collected_events(collected)
                )
                tool_hist_entry: dict[str, Any] = {
                    "role": "tool",
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "result": tool_result,
                }
                if processed_sub:
                    tool_hist_entry["subEvents"] = (
                        processed_sub
                    )
                conversation_history.append(
                    tool_hist_entry
                )
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
                except (
                    TimeoutError, AgentTimeoutError,
                    OSError,
                ):
                    raise
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

    if not pentest_report:
        pentest_report = {
            "executive_summary": (
                "PentestAgent did not complete within "
                "the step limit."
            ),
            "overall_verdict": "Attack path not feasible",
            "attack_path_steps": [],
            "hosts_compromised": [],
            "reproduction_commands": [],
            "defensive_recommendations": [],
        }

    filtered_history = [
        {k: v for k, v in e.items()
         if k not in _INTERNAL_KEYS}
        for e in conversation_history
        if e.get("type") not in _FINAL_REPORT_TYPES
    ]
    try:
        DatabaseFacade.save_agent_report(
            agent_type="pentest",
            report=pentest_report,
            username=context.get(
                "username", "system",
            ),
            incident_id=context.get("incident_id"),
            conversation_history=filtered_history,
        )
    except Exception as e:
        logger.warning(
            "Failed to save pentest report: %s", e,
        )

    yield {
        "type": "done",
        "result": {
            "pentest_report": pentest_report,
        },
    }


def run_plan_manager_stream(
    context: dict[str, Any],
) -> Generator[dict[str, Any], None, None]:
    """
    Run the PlanManagerAgent sub-agent to completion.

    Requires assessment in context (from the report
    manager's output). Builds incident_report and
    specification for the PlanManager.

    :param context: dict with assessment, system_description,
        operator_feedback, images, plan_manager_model,
        code_manager_model, code_agent_model,
        reviewer_agent_model, planner_agent_model,
        validation_agent_model, code_manager_iterations,
        rl_time_limit_minutes, dt_config, username
    :return: generator yielding event dicts
    """
    from ccs_response_planner_backend.constants.constants import (
        DIGITAL_TWIN,
    )

    raw_assessment = context.get("assessment", {})
    assessment = {
        k: v for k, v in raw_assessment.items()
        if k != "attack_path_image"
    }
    incident_report = json.dumps(
        assessment, indent=2, default=str,
    )
    dt_config = context.get("dt_config")
    if dt_config is None:
        dt_config = (
            DatabaseFacade.get_digital_twin_config()
            or DIGITAL_TWIN.DEFAULT_CONFIG
        )
    specification = json.dumps(
        dt_config.get(
            "specification_commands",
            DIGITAL_TWIN.DEFAULT_CONFIG[
                "specification_commands"
            ],
        ),
        indent=2,
    )

    agent = PlanManagerAgent()
    conversation_history: list[dict[str, Any]] = []
    step_kwargs: dict[str, Any] = {
        "system_description": context.get(
            "system_description", "",
        ),
        "incident_report": incident_report,
        "specification": specification,
        "operator_feedback": context.get(
            "operator_feedback", "",
        ),
        "model_name": context.get(
            "plan_manager_model",
        ),
        "max_iterations": context.get(
            "plan_manager_iterations", 2,
        ),
        "compaction_model": context.get(
            "compaction_model",
        ),
        "compaction_threshold": context.get(
            "plan_manager_compaction", 0.8,
        ),
        "conversation_history": conversation_history,
    }
    # Strip images and attack_path_image from the plan
    # manager context — it works with the text-based
    # incident report and specification, not the raw
    # base64 blobs (which bloat the context).
    pm_context_base = {
        k: v for k, v in context.items()
        if k not in ("images", "assessment")
    }
    pm_context_base["assessment"] = assessment
    pm_context: dict[str, Any] = {
        **pm_context_base,
        "code_manager_model": context.get(
            "code_manager_model",
        ),
        "code_agent_model": context.get(
            "code_agent_model",
        ),
        "reviewer_agent_model": context.get(
            "code_reviewer_agent_model",
        ),
        "planner_agent_model": context.get(
            "planner_agent_model",
        ),
        "validation_agent_model": context.get(
            "validation_agent_model",
        ),
        "code_manager_iterations": context.get(
            "code_manager_iterations", 2,
        ),
        "rl_time_limit_minutes": context.get(
            "rl_time_limit_minutes", 5,
        ),
        "dt_config": dt_config,
        "dt_enabled": context.get("dt_enabled", True),
        "incident_report": incident_report,
        "specification": specification,
    }

    plan_manager_report: dict[str, Any] = {}
    response_plan = ""
    planner_report: dict[str, Any] = {}
    code_report: dict[str, Any] = {}
    validation_report: dict[str, Any] = {}

    for step_num in range(MAX_INNER_STEPS):
        yield {
            "type": "output_chunk",
            "text": (
                f"[PlanManager] Step "
                f"{step_num + 1}...\n"
            ),
        }

        pending_tool = None
        step_reasoning = ""
        step_start = time.monotonic()
        for event in _timeout_step_stream(
            agent, step_kwargs, step_start,
            step_num, "PlanManager",
        ):
            etype = event.get("type")

            if etype == "system_prompt":
                yield {
                    "type": "sub_event",
                    "event": {
                        "type": "prompt",
                        "text": event.get("text", ""),
                        "images": event.get("images", []),
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
                step_reasoning += event.get(
                    "delta", "",
                )
            elif etype == "text":
                yield {
                    "type": "sub_event",
                    "event": {
                        "type": "text_delta",
                        "text": event.get("delta", ""),
                    },
                }
                step_reasoning += event.get(
                    "delta", "",
                )
            elif etype == "plan_manager_report":
                plan_manager_report = event.get(
                    "plan_manager_report", {},
                )
                yield {
                    "type": "sub_event",
                    "event": {"type": "report"},
                }
                yield {
                    "type": "output_chunk",
                    "text": (
                        "[PlanManager] Report "
                        "produced.\n"
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
            elif etype == "context_compaction":
                yield {
                    "type": "sub_event",
                    "event": event,
                }
            elif etype == "tool_proposal":
                pending_tool = event

        if step_reasoning:
            conversation_history.append({
                "role": "model",
                "type": "reasoning",
                "text": step_reasoning,
            })

        if plan_manager_report:
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
                    f"[PlanManager] Running tool: "
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
                "_vendor": pending_tool.get(
                    "_vendor",
                ),
            })
            conversation_history.append({
                "role": "user",
                "type": "tool_approval",
                "tool_name": tool_name,
                "approved": True,
            })

            if tool_name in PM_STREAMING_DISPATCH:
                collected: list[dict[str, Any]] = []
                tool_result: dict[str, Any] = {}
                try:
                    for tool_event in (
                        agent.execute_tool_stream(
                            tool_name, tool_args,
                            context=pm_context,
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
                            done_result = tool_event.get(
                                "result",
                            )
                            if done_result is not None:
                                tool_result = (
                                    done_result
                                )
                            else:
                                tool_result = {
                                    k: v
                                    for k, v in
                                    tool_event.items()
                                    if k != "type"
                                }
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
                except (
                    TimeoutError, AgentTimeoutError,
                    OSError,
                ):
                    raise
                except Exception as e:
                    tool_result = {"error": str(e)}

                if tool_name == "run_code_manager":
                    code_report = tool_result.get(
                        "code_report", {},
                    )
                    pm_context["code_report"] = (
                        code_report
                    )
                elif tool_name == "run_planner_agent":
                    planner = tool_result.get(
                        "planner_report", {},
                    )
                    response_plan = planner.get(
                        "response_plan",
                        tool_result.get(
                            "response_plan", "",
                        ),
                    )
                    planner_report = planner
                    pm_context["planner_report"] = (
                        planner
                    )
                    pm_context["response_plan"] = (
                        response_plan
                    )
                elif tool_name == (
                    "run_validation_agent"
                ):
                    validation_report = (
                        tool_result.get(
                            "validation_report", {},
                        )
                    )
                    pm_context["validation_report"] = (
                        validation_report
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
                    },
                }
                processed_sub = (
                    _process_collected_events(collected)
                )
                tool_hist_entry: dict[str, Any] = {
                    "role": "tool",
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "result": tool_result,
                }
                if processed_sub:
                    tool_hist_entry["subEvents"] = (
                        processed_sub
                    )
                conversation_history.append(
                    tool_hist_entry
                )
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
                except (
                    TimeoutError, AgentTimeoutError,
                    OSError,
                ):
                    raise
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

    if not plan_manager_report:
        plan_manager_report = {
            "executive_summary": (
                "PlanManager did not complete within "
                "the step limit."
            ),
            "iterations": 0,
            "final_verdict": "major_issues",
            "code_manager_summary": "",
            "planner_agent_summary": "",
            "validation_summary": "",
        }

    if not response_plan:
        for entry in reversed(conversation_history):
            if (
                entry.get("type") == "tool_result"
                and entry.get("tool_name")
                == "run_planner_agent"
            ):
                result = entry.get("result", {})
                pr = result.get("planner_report", {})
                response_plan = pr.get(
                    "response_plan",
                    result.get("response_plan", ""),
                )
                break

    if not code_report:
        for entry in reversed(conversation_history):
            if (
                entry.get("type") == "tool_result"
                and entry.get("tool_name")
                == "run_code_manager"
            ):
                code_report = entry.get(
                    "result", {},
                ).get("code_report", {})
                break

    if not validation_report:
        for entry in reversed(conversation_history):
            if (
                entry.get("type") == "tool_result"
                and entry.get("tool_name")
                == "run_validation_agent"
            ):
                validation_report = entry.get(
                    "result", {},
                ).get("validation_report", {})
                break

    filtered_history = [
        {k: v for k, v in e.items()
         if k not in _INTERNAL_KEYS}
        for e in conversation_history
        if e.get("type") not in _FINAL_REPORT_TYPES
    ]
    try:
        DatabaseFacade.save_agent_report(
            agent_type="plan_manager",
            report=plan_manager_report,
            username=context.get(
                "username", "system",
            ),
            incident_id=context.get("incident_id"),
            conversation_history=filtered_history,
        )
    except Exception as e:
        logger.warning(
            "Failed to save plan_manager report: "
            "%s", e,
        )

    yield {
        "type": "done",
        "result": {
            "plan_manager_report": (
                plan_manager_report
            ),
            "code_report": code_report,
            "planner_report": planner_report,
            "validation_report": validation_report,
            "response_plan": response_plan,
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
    "run_report_manager": (
        run_report_manager_stream
    ),
    "run_pentest_agent": (
        run_pentest_agent_stream
    ),
    "run_plan_manager": run_plan_manager_stream,
}
