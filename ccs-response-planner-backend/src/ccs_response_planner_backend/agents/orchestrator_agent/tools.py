"""
Tool dispatch for the OrchestratorAgent.

Provides streaming generator functions that run sub-agents
(ReportManagerAgent and PlanManagerAgent) internally,
auto-approving tool calls and yielding progress events.
"""
import json
import logging
import time
from typing import Any, Callable, Generator, Iterator

import httpx

from ccs_response_planner_backend.agents.stream_timeout import (
    AgentTimeoutError,
)

from ccs_response_planner_backend.agents.report_manager_agent.agent import (
    ReportManagerAgent,
)
from ccs_response_planner_backend.agents.report_manager_agent.tools import (
    STREAMING_TOOL_DISPATCH as RM_STREAMING_DISPATCH,
    run_report_agent_stream,
)
from ccs_response_planner_backend.agents.plan_manager_agent.agent import (
    PlanManagerAgent,
)
from ccs_response_planner_backend.agents.plan_manager_agent.tools import (
    STREAMING_TOOL_DISPATCH as PM_STREAMING_DISPATCH,
)
from ccs_response_planner_backend.agents.attack_path_verifier_agent.agent import (
    AttackPathVerifierAgent,
)
from ccs_response_planner_backend.agents.attack_path_verifier_agent.tools import (
    STREAMING_TOOL_DISPATCH as PT_STREAMING_DISPATCH,
)
from ccs_response_planner_backend.agents.execution_stats import (
    ExecutionStatsCollector,
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
    "plan_verifier_report", "orchestrator_report",
    "report_manager_report", "plan_manager_report",
}

_INTERNAL_KEYS = {
    "_model_parts", "_anthropic_content",
    "_tool_use_id", "_vendor",
}


_SKIP_TYPES = {"prompt", "context_usage"}

# Maps tool names to canonical agent names for stats.
_RM_TOOL_TO_AGENT = {
    "run_report_agent": "report_agent",
    "run_report_verifier_agent": "report_verifier_agent",
}

_PM_TOOL_TO_AGENT = {
    "run_code_manager": "code_manager",
    "run_planner_agent": "planner_agent",
    "run_plan_verifier_agent": "plan_verifier_agent",
}

_CM_TOOL_TO_AGENT = {
    "run_code_agent": "code_agent",
    "run_code_verifier_agent": "code_verifier_agent",
}

_PT_TOOL_TO_AGENT: dict[str, str] = {}


def _summarize_assessment(
    assessment: dict[str, Any],
) -> str:
    """
    Build a concise attack-path summary from an assessment dict.

    Extracts only the fields relevant for attack path verification
    (incident summary, IOCs, affected assets) so the attack path
    verifier agent's context stays small when ``attack_vector_analysis``
    is missing.

    :param assessment: the assessment dict from the report manager
    :return: a compact summary string
    """
    parts: list[str] = []
    summary = assessment.get("incident_summary", "")
    if summary:
        parts.append(f"Incident Summary:\n{summary}")
    iocs = assessment.get(
        "indicators_of_compromise", [],
    )
    if isinstance(iocs, list) and iocs:
        lines: list[str] = []
        for ioc in iocs:
            if isinstance(ioc, dict):
                ioc_type = ioc.get("type", "")
                value = ioc.get("value", "")
                ctx = ioc.get("context", "")
                lines.append(
                    f"  - {ioc_type}: {value}"
                    + (f" ({ctx})" if ctx else "")
                )
        if lines:
            parts.append(
                "Indicators of Compromise:\n"
                + "\n".join(lines)
            )
    assets = assessment.get("affected_assets", [])
    if isinstance(assets, list) and assets:
        lines = []
        for asset in assets:
            if isinstance(asset, dict):
                name = asset.get("asset", "")
                impact = asset.get("impact", "")
                lines.append(f"  - {name}: {impact}")
        if lines:
            parts.append(
                "Affected Assets:\n"
                + "\n".join(lines)
            )
    if not parts:
        return "No attack path information available."
    return "\n\n".join(parts)


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
    filters prompts/context_usage, keeps only structural
    nested_events (tool_call/tool_result/parallel_start/
    agent_done), recursively processes subEvents on
    tool_results, strips internal keys.

    :param collected: raw events from streaming tool execution
    :return: processed events for history storage
    """
    result: list[dict[str, Any]] = []
    for ev in collected:
        ev_type = ev.get("type")
        if ev_type in _SKIP_TYPES:
            continue
        if ev_type == "nested_event":
            inner = ev.get("event", {})
            for item in reversed(result):
                if (
                    item.get("type") == "tool_call"
                    and not item.get("_completed")
                ):
                    if "subEvents" not in item:
                        item["subEvents"] = []
                    item["subEvents"].append(inner)
                    break
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
        if ev_type == "tool_result":
            for item in reversed(result):
                if (
                    item.get("type") == "tool_call"
                    and not item.get("_completed")
                ):
                    item["_completed"] = True
                    if item.get("subEvents"):
                        item["subEvents"] = (
                            _process_collected_events(
                                item["subEvents"]
                            )
                        )
                    break
            if cleaned.get("subEvents"):
                cleaned["subEvents"] = (
                    _process_collected_events(
                        cleaned["subEvents"]
                    )
                )
        result.append(cleaned)
    return result


def _record_inner_stats(
    inner: dict[str, Any],
    stats: ExecutionStatsCollector,
    tool_map: dict[str, str],
    current_tool: str,
    collected: list[dict[str, Any]],
    deep_tool_map: dict[str, str] | None = None,
    deep_timers: dict[str, float] | None = None,
) -> None:
    """
    Record stats from an inner sub-agent event.

    Called during the tool execution loop for each
    ``sub_event`` from a streaming tool.  Intercepts
    ``context_usage`` events and maps them to the correct
    agent name.

    :param inner: the unwrapped inner event dict
    :param stats: the stats collector
    :param tool_map: maps outer tool names to agent names
    :param current_tool: current outer tool name
    :param collected: list of previously collected events
    :param deep_tool_map: optional map for doubly-nested
        agents (e.g. code_agent inside code_manager)
    :param deep_timers: mutable dict tracking start times
        for doubly-nested tool calls (wall-time tracking)
    """
    itype = inner.get("type", "")
    agent_name = tool_map.get(
        current_tool, current_tool,
    )
    if itype == "context_usage":
        stats.record_tokens(
            agent_name,
            inner.get("prompt_tokens", 0),
            inner.get("candidates_tokens", 0),
            inner.get("total_tokens", 0),
        )
    elif itype == "tool_call":
        stats.record_function_call(
            agent_name, inner.get("tool_name", ""),
        )
        if (
            deep_tool_map
            and deep_timers is not None
        ):
            tn = inner.get("tool_name", "")
            if tn in deep_tool_map:
                deep_timers[tn] = time.monotonic()
    elif (
        itype == "tool_result"
        and deep_tool_map
        and deep_timers is not None
    ):
        tn = inner.get("tool_name", "")
        if tn in deep_timers:
            deep_agent = deep_tool_map.get(
                tn, tn,
            )
            stats.record_wall_time(
                deep_agent,
                time.monotonic()
                - deep_timers.pop(tn),
            )
    elif itype == "nested_event" and deep_tool_map:
        deep = inner.get("event", {})
        deep_type = deep.get("type", "")
        # Find the most recent inner tool_call to
        # determine which sub-agent this belongs to.
        inner_tool = ""
        for prev in reversed(collected):
            if prev.get("type") == "tool_call":
                inner_tool = prev.get(
                    "tool_name", "",
                )
                break
        deep_agent = deep_tool_map.get(
            inner_tool, agent_name,
        )
        if deep_type == "context_usage":
            stats.record_tokens(
                deep_agent,
                deep.get("prompt_tokens", 0),
                deep.get("candidates_tokens", 0),
                deep.get("total_tokens", 0),
            )
        elif deep_type == "tool_call":
            stats.record_function_call(
                deep_agent,
                deep.get("tool_name", ""),
            )


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


def run_report_agent_direct_stream(
    context: dict[str, Any],
) -> Generator[dict[str, Any], None, None]:
    """
    Run the ReportAgent directly, bypassing ReportManagerAgent.

    Used when the report verifier is disabled. Delegates to
    ``run_report_agent_stream`` and wraps its events with an
    extra nesting layer so downstream code (summariser, route
    assessment extraction, frontend history) works unchanged.

    :param context: dict with system_description,
        security_alerts, operator_feedback, images,
        report_agent_model, username, dt_config
    :return: generator yielding event dicts
    """
    validation_fb = context.get(
        "validation_feedback", "",
    )
    if validation_fb:
        existing = context.get(
            "operator_feedback", "",
        )
        context = {
            **context,
            "operator_feedback": (
                f"{existing}\n\n"
                f"--- ATTACK PATH VERIFICATION FEEDBACK ---\n"
                f"{validation_fb}\n"
                f"--- END ATTACK PATH VERIFICATION FEEDBACK ---"
                if existing else validation_fb
            ),
        }

    stats: ExecutionStatsCollector | None = context.get(
        "_stats_collector",
    )

    assessment: dict[str, Any] = {}
    attack_path_img: str | None = None

    # Emit a synthetic tool_call so the frontend creates
    # an activity panel for run_report_agent.
    yield {
        "type": "sub_event",
        "event": {
            "type": "tool_call",
            "tool_name": "run_report_agent",
            "tool_args": {},
        },
    }

    ra_start = time.monotonic()
    for event in run_report_agent_stream(
        context=context,
    ):
        etype = event.get("type")
        if etype == "sub_event":
            inner = event.get("event", {})
            if stats and inner.get("type") == (
                "context_usage"
            ):
                stats.record_tokens(
                    "report_agent",
                    inner.get("prompt_tokens", 0),
                    inner.get(
                        "candidates_tokens", 0,
                    ),
                    inner.get("total_tokens", 0),
                )
            yield {
                "type": "sub_event",
                "event": {
                    "type": "nested_event",
                    "event": inner,
                },
            }
        elif etype == "output_chunk":
            yield event
        elif etype == "done":
            result = event.get("result", {})
            assessment = result.get(
                "assessment", {},
            )
            attack_path_img = result.get(
                "attack_path_image",
            )
    if stats:
        stats.record_wall_time(
            "report_agent",
            time.monotonic() - ra_start,
        )

    # Emit a synthetic tool_result to close the
    # run_report_agent activity panel.
    tool_result_data: dict[str, Any] = {
        "assessment": assessment,
    }
    if attack_path_img:
        tool_result_data["attack_path_image"] = (
            attack_path_img
        )
    yield {
        "type": "sub_event",
        "event": {
            "type": "tool_result",
            "tool_name": "run_report_agent",
            "result": _truncate_result(
                tool_result_data,
            ),
        },
    }

    done_result: dict[str, Any] = {
        "report_manager_report": {
            "executive_summary": (
                "Direct assessment (review skipped)"
            ),
            "iterations": 0,
            "final_verdict": "approved",
            "report_summary": "",
            "review_summary": "",
        },
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


def run_report_manager_stream(
    context: dict[str, Any],
) -> Generator[dict[str, Any], None, None]:
    """
    Run the ReportManagerAgent sub-agent to completion.

    Runs the full ReportManager loop (ReportAgent +
    ReportVerifierAgent internally), streaming events back.
    The ReportManager's own streaming tools produce
    nested_event wrappers (3-level nesting).

    :param context: dict with system_description,
        security_alerts, operator_feedback, images,
        report_manager_model, report_agent_model,
        reviewer_agent_model, username, dt_config
    :return: generator yielding event dicts
    """
    stats: ExecutionStatsCollector | None = context.get(
        "_stats_collector",
    )
    rm_start = time.monotonic()

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
        "dt_enabled": context.get(
            "dt_enabled", True,
        ),
        "info_tools_enabled": context.get(
            "info_tools_enabled", True,
        ),
        "report_verifier_enabled": context.get(
            "report_verifier_enabled", True,
        ),
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
        "info_tools_enabled": context.get(
            "info_tools_enabled", True,
        ),
    }

    report_manager_report: dict[str, Any] | None = None
    assessment: dict[str, Any] = {}
    attack_path_img: str | None = None

    report_verifier_enabled = context.get(
        "report_verifier_enabled", True,
    )
    if not report_verifier_enabled:
        # Bypass the ReportManager LLM loop — run
        # ReportAgent directly and produce a synthetic
        # manager report.  This avoids unnecessary Gemini
        # API calls that can hang when the verifier is
        # disabled.
        yield {
            "type": "output_chunk",
            "text": (
                "[ReportManager] Verifier disabled "
                "— running ReportAgent directly...\n"
            ),
        }
        for event in run_report_agent_stream(
            context=rm_context,
        ):
            etype = event.get("type")
            if etype == "sub_event":
                yield event
            elif etype == "output_chunk":
                yield event
            elif etype == "done":
                result = event.get("result", {})
                assessment = result.get(
                    "assessment", {},
                )
                attack_path_img = result.get(
                    "attack_path_image",
                )

        report_manager_report = {
            "executive_summary": (
                "Report generated directly "
                "(verifier disabled)."
            ),
            "iterations": 1,
            "final_verdict": "pass",
            "report_summary": assessment.get(
                "incident_summary", "",
            ),
            "review_summary": (
                "Reviewer was disabled."
            ),
        }
        saved_assessment = (
            dict(assessment) if assessment else {}
        )
        if attack_path_img:
            saved_assessment["attack_path_image"] = (
                attack_path_img
            )
        try:
            DatabaseFacade.save_agent_report(
                agent_type="report_manager",
                report={
                    **report_manager_report,
                    "final_assessment": (
                        saved_assessment
                    ),
                },
                username=context.get(
                    "username", "system",
                ),
                incident_id=context.get(
                    "incident_id",
                ),
                conversation_history=[],
            )
        except Exception as e:
            logger.warning(
                "Failed to save report_manager "
                "report: %s", e,
            )
        done_result: dict[str, Any] = {
            "report_manager_report": (
                report_manager_report
            ),
            "assessment": assessment,
        }
        if attack_path_img:
            done_result["attack_path_image"] = (
                attack_path_img
            )
        yield {"type": "done", "result": done_result}
        return

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
                if stats:
                    stats.record_tokens(
                        "report_manager",
                        event.get("prompt_tokens", 0),
                        event.get(
                            "candidates_tokens", 0,
                        ),
                        event.get("total_tokens", 0),
                    )
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
                if stats:
                    stats.record_function_call(
                        "report_manager",
                        event.get("tool_name", ""),
                    )
                pending_tool = event

        if step_reasoning:
            conversation_history.append({
                "role": "model",
                "type": "reasoning",
                "text": step_reasoning,
            })

        if report_manager_report is not None:
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
                rm_tool_start = time.monotonic()
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
                            if stats:
                                _record_inner_stats(
                                    inner, stats,
                                    _RM_TOOL_TO_AGENT,
                                    tool_name,
                                    collected,
                                )
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
                            inner_done = tool_event.get(
                                "result",
                            )
                            if inner_done is not None:
                                tool_result = (
                                    inner_done
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

                if stats:
                    rm_agent = _RM_TOOL_TO_AGENT.get(
                        tool_name, tool_name,
                    )
                    stats.record_wall_time(
                        rm_agent,
                        time.monotonic() - rm_tool_start,
                    )

                if tool_name == "run_report_agent":
                    assessment = tool_result.get(
                        "assessment", {},
                    )
                    new_img = tool_result.get(
                        "attack_path_image",
                    )
                    if new_img is not None:
                        attack_path_img = new_img
                    rm_context[
                        "prior_attack_path_image"
                    ] = attack_path_img
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

    if report_manager_report is None:
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

    if stats:
        stats.record_wall_time(
            "report_manager",
            time.monotonic() - rm_start,
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
    if stats:
        done_result["_execution_stats"] = (
            stats.to_dict()
        )
    yield {
        "type": "done",
        "result": done_result,
    }


def run_attack_path_verifier_agent_stream(
    context: dict[str, Any],
) -> Generator[dict[str, Any], None, None]:
    """
    Run the AttackPathVerifierAgent sub-agent to completion.

    Extracts the attack path from the assessment in context
    and runs the AttackPathVerifierAgent loop, auto-approving
    tool calls (dt_exec, dt_restart) and streaming progress events.

    :param context: dict with assessment, system_description,
        dt_config, attack_path_verifier_agent_model, username
    :return: generator yielding event dicts
    """
    stats: ExecutionStatsCollector | None = context.get(
        "_stats_collector",
    )
    pt_start = time.monotonic()

    agent = AttackPathVerifierAgent()
    conversation_history: list[dict[str, Any]] = []

    assessment = context.get("assessment", {})
    attack_path = ""
    if isinstance(assessment, dict):
        attack_path = assessment.get(
            "attack_vector_analysis", "",
        )
        if not attack_path:
            attack_path = _summarize_assessment(
                assessment,
            )

    system_description = context.get(
        "system_description", "",
    )
    dt_config = context.get("dt_config")
    step_kwargs: dict[str, Any] = {
        "system_description": system_description,
        "attack_path": attack_path,
        "model_name": context.get(
            "attack_path_verifier_agent_model",
        ),
        "dt_config": dt_config,
        "compaction_model": context.get(
            "compaction_model",
        ),
        "compaction_threshold": context.get(
            "attack_path_verifier_agent_compaction", 0.8,
        ),
        "conversation_history": conversation_history,
        "dt_enabled": context.get(
            "dt_enabled", True,
        ),
    }

    attack_path_verifier_report: dict[str, Any] = {}

    for step_num in range(MAX_INNER_STEPS):
        yield {
            "type": "output_chunk",
            "text": (
                f"[AttackPathVerifierAgent] Step "
                f"{step_num + 1}...\n"
            ),
        }

        pending_tool = None
        step_reasoning = ""
        step_start = time.monotonic()
        for event in _timeout_step_stream(
            agent, step_kwargs, step_start,
            step_num, "AttackPathVerifierAgent",
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
            elif etype == "attack_path_verifier_report":
                attack_path_verifier_report = event.get(
                    "attack_path_verifier_report", {},
                )
                yield {
                    "type": "sub_event",
                    "event": {"type": "report"},
                }
                yield {
                    "type": "output_chunk",
                    "text": (
                        "[AttackPathVerifierAgent] Report "
                        "produced.\n"
                    ),
                }
            elif etype == "context_usage":
                if stats:
                    stats.record_tokens(
                        "attack_path_verifier_agent",
                        event.get("prompt_tokens", 0),
                        event.get(
                            "candidates_tokens", 0,
                        ),
                        event.get("total_tokens", 0),
                    )
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
                if stats:
                    stats.record_function_call(
                        "attack_path_verifier_agent",
                        event.get("tool_name", ""),
                    )
                pending_tool = event

        if step_reasoning:
            conversation_history.append({
                "role": "model",
                "type": "reasoning",
                "text": step_reasoning,
            })

        if attack_path_verifier_report:
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
                    f"[AttackPathVerifierAgent] Running tool: "
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
                            if stats:
                                _record_inner_stats(
                                    inner, stats,
                                    _PT_TOOL_TO_AGENT,
                                    tool_name,
                                    collected,
                                )
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

    if not attack_path_verifier_report:
        attack_path_verifier_report = {
            "executive_summary": (
                "AttackPathVerifierAgent did not complete "
                "within the step limit."
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
            agent_type="attack_path_verifier",
            report=attack_path_verifier_report,
            username=context.get(
                "username", "system",
            ),
            incident_id=context.get("incident_id"),
            conversation_history=filtered_history,
        )
    except Exception as e:
        logger.warning(
            "Failed to save attack path verifier report: %s", e,
        )

    if stats:
        stats.record_wall_time(
            "attack_path_verifier_agent",
            time.monotonic() - pt_start,
        )

    pt_done: dict[str, Any] = {
        "attack_path_verifier_report": attack_path_verifier_report,
    }
    if stats:
        pt_done["_execution_stats"] = stats.to_dict()
    yield {
        "type": "done",
        "result": pt_done,
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
        plan_verifier_agent_model, code_manager_iterations,
        rl_time_limit_minutes, dt_config, username
    :return: generator yielding event dicts
    """
    stats: ExecutionStatsCollector | None = context.get(
        "_stats_collector",
    )
    pm_start = time.monotonic()

    from ccs_response_planner_backend.constants.constants import (
        DIGITAL_TWIN,
    )

    report_manager_enabled = context.get(
        "report_manager_enabled", True,
    )
    raw_assessment = context.get("assessment", {})
    assessment = {
        k: v for k, v in raw_assessment.items()
        if k != "attack_path_image"
    }
    if report_manager_enabled:
        incident_report = json.dumps(
            assessment, indent=2, default=str,
        )
    else:
        incident_report = ""
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
        "code_model_enabled": context.get(
            "code_model_enabled", True,
        ),
        "plan_verifier_enabled": context.get(
            "plan_verifier_enabled", True,
        ),
        "report_manager_enabled": report_manager_enabled,
        "security_alerts": context.get(
            "security_alerts", "",
        ),
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
            "code_verifier_agent_model",
        ),
        "planner_agent_model": context.get(
            "planner_agent_model",
        ),
        "plan_verifier_agent_model": context.get(
            "plan_verifier_agent_model",
        ),
        "code_manager_iterations": context.get(
            "code_manager_iterations", 2,
        ),
        "rl_time_limit_minutes": context.get(
            "rl_time_limit_minutes", 5,
        ),
        "dt_config": dt_config,
        "dt_enabled": context.get("dt_enabled", True),
        "plan_verifier_enabled": context.get(
            "plan_verifier_enabled", True,
        ),
        "code_model_enabled": context.get(
            "code_model_enabled", True,
        ),
        "incident_report": incident_report,
        "specification": specification,
        "report_manager_enabled": report_manager_enabled,
        "security_alerts": context.get(
            "security_alerts", "",
        ),
    }

    plan_manager_report: dict[str, Any] = {}
    response_plan = ""
    planner_report: dict[str, Any] = {}
    code_report: dict[str, Any] = {}
    plan_verifier_report: dict[str, Any] = {}

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
                if stats:
                    stats.record_tokens(
                        "plan_manager",
                        event.get("prompt_tokens", 0),
                        event.get(
                            "candidates_tokens", 0,
                        ),
                        event.get("total_tokens", 0),
                    )
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
                if stats:
                    stats.record_function_call(
                        "plan_manager",
                        event.get("tool_name", ""),
                    )
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
                pm_tool_start = time.monotonic()
                pm_deep_map = (
                    _CM_TOOL_TO_AGENT
                    if tool_name == "run_code_manager"
                    else None
                )
                pm_deep_timers: (
                    dict[str, float] | None
                ) = (
                    {} if pm_deep_map else None
                )
                tool_stream: Iterator[
                    dict[str, Any]
                ]
                try:
                    if (
                        tool_name
                        == "run_plan_verifier_agent"
                        and not pm_context.get(
                            "plan_verifier_enabled",
                            True,
                        )
                    ):
                        tool_stream = iter([{
                            "type": "done",
                            "result": {
                                "plan_verifier_report": {
                                    "overall_verdict":
                                        "skipped",
                                    "executive_summary":
                                        "Validation "
                                        "skipped by "
                                        "user",
                                },
                            },
                        }])
                    else:
                        tool_stream = (
                            agent.execute_tool_stream(
                                tool_name, tool_args,
                                context=pm_context,
                            )
                        )
                    for tool_event in tool_stream:
                        te_type = tool_event.get("type")
                        if te_type == "sub_event":
                            inner = tool_event["event"]
                            if stats:
                                _record_inner_stats(
                                    inner, stats,
                                    _PM_TOOL_TO_AGENT,
                                    tool_name,
                                    collected,
                                    pm_deep_map,
                                    pm_deep_timers,
                                )
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

                if stats:
                    pm_agent = _PM_TOOL_TO_AGENT.get(
                        tool_name, tool_name,
                    )
                    stats.record_wall_time(
                        pm_agent,
                        time.monotonic()
                        - pm_tool_start,
                    )

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
                    "run_plan_verifier_agent"
                ):
                    plan_verifier_report = (
                        tool_result.get(
                            "plan_verifier_report", {},
                        )
                    )
                    pm_context["plan_verifier_report"] = (
                        plan_verifier_report
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

    if not plan_verifier_report:
        for entry in reversed(conversation_history):
            if (
                entry.get("type") == "tool_result"
                and entry.get("tool_name")
                == "run_plan_verifier_agent"
            ):
                plan_verifier_report = entry.get(
                    "result", {},
                ).get("plan_verifier_report", {})
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

    if stats:
        stats.record_wall_time(
            "plan_manager",
            time.monotonic() - pm_start,
        )

    pm_done: dict[str, Any] = {
        "plan_manager_report": (
            plan_manager_report
        ),
        "code_report": code_report,
        "planner_report": planner_report,
        "plan_verifier_report": plan_verifier_report,
        "response_plan": response_plan,
    }
    if stats:
        pm_done["_execution_stats"] = stats.to_dict()
    yield {
        "type": "done",
        "result": pm_done,
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
    "run_attack_path_verifier_agent": (
        run_attack_path_verifier_agent_stream
    ),
    "run_plan_manager": run_plan_manager_stream,
}
