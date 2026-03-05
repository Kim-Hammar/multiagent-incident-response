"""
Tool dispatch for the ReportManagerAgent.

Provides streaming generator functions that run sub-agents
(ReportAgent and ReportVerifierAgent) internally, auto-approving
tool calls and yielding progress events.
"""
import logging
import time
from typing import Any, Callable, Generator

import httpx

from ccs_response_planner_backend.agents.stream_timeout import (
    AgentTimeoutError,
)

from ccs_response_planner_backend.agents.report_agent.agent import (
    ReportAgent,
)
from ccs_response_planner_backend.agents.report_agent.tools import (
    STREAMING_TOOL_DISPATCH as REPORT_STREAMING_DISPATCH,
)
from ccs_response_planner_backend.agents.report_verifier_agent.agent import (
    ReportVerifierAgent,
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


def run_report_agent_stream(
    context: dict[str, Any],
    previous_assessment: str = "",
    review_feedback: str = "",
) -> Generator[dict[str, Any], None, None]:
    """
    Run the ReportAgent sub-agent to completion, streaming progress.

    Auto-approves all sub-agent tool calls. Yields output_chunk
    events for progress, sub_event events for rich UI rendering,
    and a done event with the assessment.

    :param context: dict with system_description, security_alerts,
        operator_feedback, images, report_agent_model, username,
        dt_config
    :param previous_assessment: assessment from a prior iteration
    :param review_feedback: reviewer findings for revision
    :return: generator yielding event dicts
    """
    agent = ReportAgent()
    operator_feedback = context.get("operator_feedback", "")
    if previous_assessment and review_feedback:
        operator_feedback += (
            "\n\n--- REVISION CONTEXT ---\n"
            "The previous assessment produced by you is "
            "shown below, along with the reviewer's "
            "feedback. Focus on fixing the specific issues "
            "identified. Do NOT start from scratch.\n\n"
            "## Previous Assessment\n"
            f"{previous_assessment}\n\n"
            "## Reviewer Feedback\n"
            f"{review_feedback}\n"
            "--- END REVISION CONTEXT ---"
        )

    conversation_history: list[dict[str, Any]] = []
    assessment = None
    attack_path_image = None

    for step_num in range(MAX_INNER_STEPS):
        yield {
            "type": "output_chunk",
            "text": (
                f"[ReportAgent] Step {step_num + 1}...\n"
            ),
        }

        step_reasoning = ""
        step_start = time.monotonic()
        ra_kwargs: dict[str, Any] = {
            "system_description": context.get(
                "system_description", "",
            ),
            "security_alerts": context.get(
                "security_alerts", "",
            ),
            "operator_feedback": operator_feedback,
            "conversation_history": conversation_history,
            "images": context.get("images"),
            "model_name": context.get(
                "report_agent_model",
            ),
            "dt_config": context.get("dt_config"),
            "is_revision": bool(
                previous_assessment and review_feedback
            ),
            "compaction_model": context.get(
                "compaction_model",
            ),
            "compaction_threshold": context.get(
                "report_agent_compaction", 0.8,
            ),
            "dt_enabled": context.get(
                "dt_enabled", True,
            ),
            "info_tools_enabled": context.get(
                "info_tools_enabled", True,
            ),
        }
        for event in _timeout_step_stream(
            agent, ra_kwargs, step_start,
            step_num, "ReportAgent",
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
                step_reasoning += event.get(
                    "delta", "",
                )
            elif etype == "assessment":
                assessment = event.get(
                    "assessment", {},
                )
                if step_reasoning:
                    conversation_history.append({
                        "role": "model",
                        "type": "reasoning",
                        "text": step_reasoning,
                    })
                    step_reasoning = ""
                conversation_history.append({
                    "role": "model",
                    "type": "assessment",
                    "assessment": assessment,
                })
                yield {
                    "type": "sub_event",
                    "event": {"type": "report"},
                }
                yield {
                    "type": "output_chunk",
                    "text": (
                        "[ReportAgent] Assessment "
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
                tool_name = event.get("tool_name", "")
                tool_args = event.get("tool_args", {})
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
                        f"[ReportAgent] Running tool: "
                        f"{tool_name}...\n"
                    ),
                }
                if step_reasoning:
                    conversation_history.append({
                        "role": "model",
                        "type": "reasoning",
                        "text": step_reasoning,
                    })
                    step_reasoning = ""
                conversation_history.append({
                    "role": "model",
                    "type": "tool_proposal",
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "rationale": event.get(
                        "rationale", "",
                    ),
                    "_model_parts": event.get(
                        "_model_parts",
                    ),
                    "_anthropic_content": event.get(
                        "_anthropic_content",
                    ),
                    "_tool_use_id": event.get(
                        "_tool_use_id",
                    ),
                    "_vendor": event.get("_vendor"),
                })
                conversation_history.append({
                    "role": "user",
                    "type": "tool_approval",
                    "tool_name": tool_name,
                    "approved": True,
                })
                try:
                    if tool_name in REPORT_STREAMING_DISPATCH:
                        tool_result = {}
                        for sevt in agent.execute_tool_stream(
                            tool_name, tool_args,
                            context=context,
                        ):
                            sevt_type = sevt.get("type")
                            if sevt_type == "done":
                                tool_result = sevt.get(
                                    "result", {},
                                )
                            elif sevt_type == "error":
                                tool_result = {
                                    "error": sevt.get(
                                        "message", "",
                                    ),
                                }
                            elif sevt_type == "sub_event":
                                inner = dict(
                                    sevt.get("event", {}),
                                )
                                if sevt.get("agent_id"):
                                    inner["agent_id"] = (
                                        sevt["agent_id"]
                                    )
                                if sevt.get("agent_label"):
                                    inner["agent_label"] = (
                                        sevt["agent_label"]
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
                            elif sevt_type == "output_chunk":
                                yield sevt
                    else:
                        result = agent.execute_tool(
                            tool_name, tool_args,
                        )
                        tool_result = result.get(
                            "result", {},
                        )
                        if result.get("error"):
                            tool_result = {
                                "error": result["error"],
                            }
                except Exception as e:
                    tool_result = {"error": str(e)}
                conversation_history.append({
                    "role": "tool",
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "result": tool_result,
                })
                if (
                    tool_name == "generate_attack_image"
                    and isinstance(tool_result, dict)
                    and tool_result.get("image")
                ):
                    attack_path_image = (
                        tool_result["image"]
                    )
                output = ""
                if isinstance(tool_result, dict):
                    output = tool_result.get(
                        "output",
                        tool_result.get("error", ""),
                    ) or ""
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
                yield {
                    "type": "output_chunk",
                    "text": (
                        f"[ReportAgent] {tool_name} "
                        f"result: "
                        f"{str(output)[:500]}\n"
                    ),
                }

        if assessment is not None:
            break

    if assessment is None:
        assessment = {
            "incident_summary": (
                "ReportAgent did not produce an "
                "assessment within the step limit."
            ),
            "attack_vector_analysis": "",
            "indicators_of_compromise": [],
            "severity": "Unknown",
            "severity_justification": "",
            "affected_assets": [],
        }

    if attack_path_image is None:
        attack_path_image = context.get(
            "prior_attack_path_image",
        )

    if attack_path_image and assessment is not None:
        assessment["attack_path_image"] = (
            attack_path_image
        )

    filtered_history = [
        {k: v for k, v in e.items()
         if k not in _INTERNAL_KEYS}
        for e in conversation_history
        if e.get("type") not in _FINAL_REPORT_TYPES
    ]
    try:
        DatabaseFacade.save_agent_report(
            agent_type="report",
            report=assessment,
            username=context.get("username", "system"),
            incident_id=context.get("incident_id"),
            conversation_history=filtered_history,
        )
    except Exception as e:
        logger.warning(
            "Failed to save report: %s", e,
        )

    # Separate attack_path_image from assessment to prevent
    # the large base64 blob from entering conversation history
    # and downstream agent contexts.  The image is already
    # saved in the DB record above.
    done_assessment = {
        k: v for k, v in assessment.items()
        if k != "attack_path_image"
    }
    yield {
        "type": "done",
        "result": {
            "assessment": done_assessment,
            "attack_path_image": assessment.get(
                "attack_path_image",
            ),
        },
    }


def run_report_verifier_agent_stream(
    context: dict[str, Any],
    previous_review_summary: str = "",
) -> Generator[dict[str, Any], None, None]:
    """
    Run the ReportVerifierAgent sub-agent to completion.

    Auto-approves all sub-agent tool calls. Yields output_chunk
    events for progress, sub_event events for rich UI rendering,
    and a done event with the report_review.

    :param context: dict with system_description, security_alerts,
        operator_feedback, images, verifier_agent_model, username,
        last_assessment, dt_config
    :param previous_review_summary: concise summary of prior
        review findings for re-review iterations
    :return: generator yielding event dicts
    """
    agent = ReportVerifierAgent()
    last_assessment = context.get("last_assessment", {})
    operator_feedback = context.get("operator_feedback", "")
    if previous_review_summary:
        operator_feedback += (
            "\n\n--- PREVIOUS REVIEW CONTEXT ---\n"
            "This is a RE-REVIEW iteration. The report "
            "was revised based on your previous findings. "
            "Focus on:\n"
            "1. Verify previously identified issues are "
            "fixed\n"
            "2. Check for NEW issues introduced by "
            "revision\n"
            "3. Skip re-validating passed checks unless "
            "revision affects them\n\n"
            "## Previous Review Summary\n"
            f"{previous_review_summary}\n"
            "--- END PREVIOUS REVIEW CONTEXT ---"
        )
    conversation_history: list[dict[str, Any]] = []
    report_review = None

    for step_num in range(MAX_INNER_STEPS):
        yield {
            "type": "output_chunk",
            "text": (
                f"[ReportVerifierAgent] Step "
                f"{step_num + 1}...\n"
            ),
        }

        step_reasoning = ""
        step_start = time.monotonic()
        rr_kwargs: dict[str, Any] = {
            "system_description": context.get(
                "system_description", "",
            ),
            "security_alerts": context.get(
                "security_alerts", "",
            ),
            "operator_feedback": operator_feedback,
            "incident_report": last_assessment,
            "conversation_history": conversation_history,
            "images": context.get("images"),
            "model_name": context.get(
                "reviewer_agent_model",
            ),
            "dt_config": context.get("dt_config"),
            "review_iteration": context.get(
                "review_count", 1,
            ),
            "compaction_model": context.get(
                "compaction_model",
            ),
            "compaction_threshold": context.get(
                "report_verifier_compaction", 0.8,
            ),
            "dt_enabled": context.get(
                "dt_enabled", True,
            ),
            "info_tools_enabled": context.get(
                "info_tools_enabled", True,
            ),
        }
        for event in _timeout_step_stream(
            agent, rr_kwargs, step_start,
            step_num, "ReportVerifierAgent",
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
                step_reasoning += event.get(
                    "delta", "",
                )
            elif etype == "report_review":
                report_review = event.get(
                    "report_review", {},
                )
                if step_reasoning:
                    conversation_history.append({
                        "role": "model",
                        "type": "reasoning",
                        "text": step_reasoning,
                    })
                    step_reasoning = ""
                conversation_history.append({
                    "role": "model",
                    "type": "report_review",
                    "report_review": report_review,
                })
                yield {
                    "type": "sub_event",
                    "event": {"type": "report"},
                }
                yield {
                    "type": "output_chunk",
                    "text": (
                        "[ReportVerifierAgent] Review "
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
            elif etype == "context_compaction":
                yield {
                    "type": "sub_event",
                    "event": event,
                }
            elif etype == "tool_proposal":
                tool_name = event.get("tool_name", "")
                tool_args = event.get("tool_args", {})
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
                        f"[ReportVerifierAgent] Running "
                        f"tool: {tool_name}...\n"
                    ),
                }
                if step_reasoning:
                    conversation_history.append({
                        "role": "model",
                        "type": "reasoning",
                        "text": step_reasoning,
                    })
                    step_reasoning = ""
                conversation_history.append({
                    "role": "model",
                    "type": "tool_proposal",
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "rationale": event.get(
                        "rationale", "",
                    ),
                    "_model_parts": event.get(
                        "_model_parts",
                    ),
                    "_anthropic_content": event.get(
                        "_anthropic_content",
                    ),
                    "_tool_use_id": event.get(
                        "_tool_use_id",
                    ),
                    "_vendor": event.get("_vendor"),
                })
                conversation_history.append({
                    "role": "user",
                    "type": "tool_approval",
                    "tool_name": tool_name,
                    "approved": True,
                })
                try:
                    result = agent.execute_tool(
                        tool_name, tool_args,
                    )
                    tool_result = result.get(
                        "result", {},
                    )
                    if result.get("error"):
                        tool_result = {
                            "error": result["error"],
                        }
                except Exception as e:
                    tool_result = {"error": str(e)}
                conversation_history.append({
                    "role": "tool",
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "result": tool_result,
                })
                output = ""
                if isinstance(tool_result, dict):
                    output = tool_result.get(
                        "output",
                        tool_result.get("error", ""),
                    ) or ""
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
                yield {
                    "type": "output_chunk",
                    "text": (
                        f"[ReportVerifierAgent] "
                        f"{tool_name} result: "
                        f"{str(output)[:500]}\n"
                    ),
                }

        if report_review is not None:
            break

    if report_review is None:
        report_review = {
            "executive_summary": (
                "ReportVerifierAgent did not produce a "
                "report within the step limit."
            ),
            "findings": [],
            "missing_elements": [],
            "evidence_gaps": [],
            "strengths": [],
            "overall_verdict": "major_issues",
        }

    filtered_history = [
        {k: v for k, v in e.items()
         if k not in _INTERNAL_KEYS}
        for e in conversation_history
        if e.get("type") not in _FINAL_REPORT_TYPES
    ]
    try:
        DatabaseFacade.save_agent_report(
            agent_type="report_verifier",
            report=report_review,
            username=context.get("username", "system"),
            incident_id=context.get("incident_id"),
            conversation_history=filtered_history,
        )
    except Exception as e:
        logger.warning(
            "Failed to save review report: %s", e,
        )

    yield {
        "type": "done",
        "result": {"report_review": report_review},
    }


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


TOOL_DISPATCH: dict[
    str, Callable[..., dict[str, Any]]
] = {}

STREAMING_TOOL_DISPATCH: dict[
    str,
    Callable[
        ..., Generator[dict[str, Any], None, None]
    ],
] = {
    "run_report_agent": run_report_agent_stream,
    "run_report_verifier_agent": (
        run_report_verifier_agent_stream
    ),
}
