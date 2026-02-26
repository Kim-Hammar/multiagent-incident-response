"""
Tool dispatch for the CodeManagerAgent.

Provides streaming generator functions that run sub-agents
(CodeAgent and CodeReviewerAgent) internally, auto-approving
tool calls and yielding progress events.
"""
import logging
import time
from typing import Any, Callable, Generator

import httpx

from ccs_response_planner_backend.agents.stream_timeout import (
    AgentTimeoutError,
)

from ccs_response_planner_backend.agents.code_agent.agent import CodeAgent
from ccs_response_planner_backend.agents.code_reviewer_agent.agent import (
    CodeReviewerAgent,
)
from ccs_response_planner_backend.db.database_facade import DatabaseFacade

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


def run_code_agent_stream(
    context: dict[str, Any],
    previous_code: str = "",
    review_feedback: str = "",
) -> Generator[dict[str, Any], None, None]:
    """
    Run the CodeAgent sub-agent to completion, streaming progress.

    Auto-approves all sub-agent tool calls. Yields output_chunk
    events for progress, sub_event events for rich UI rendering,
    and a done event with the code_report.

    :param context: dict with system_description, incident_report,
        specification, operator_feedback, images,
        code_agent_model, username
    :param previous_code: generated code from a prior iteration
    :param review_feedback: reviewer findings for revision
    :return: generator yielding event dicts
    """
    agent = CodeAgent()
    operator_feedback = context.get("operator_feedback", "")
    if previous_code and review_feedback:
        operator_feedback += (
            "\n\n--- REVISION CONTEXT ---\n"
            "The previous iteration of the generated code is "
            "shown below, along with the reviewer's feedback. "
            "Please revise the code to address ALL of the "
            "reviewer's findings.\n\n"
            "## Previous Generated Code\n"
            f"```python\n{previous_code}\n```\n\n"
            "## Reviewer Feedback\n"
            f"{review_feedback}\n"
            "--- END REVISION CONTEXT ---"
        )

    conversation_history: list[dict[str, Any]] = []
    code_report = None

    for step_num in range(MAX_INNER_STEPS):
        yield {
            "type": "output_chunk",
            "text": f"[CodeAgent] Step {step_num + 1}...\n",
        }

        step_reasoning = ""
        step_start = time.monotonic()
        ca_kwargs: dict[str, Any] = {
            "system_description": context.get(
                "system_description", "",
            ),
            "incident_report": context.get(
                "incident_report", "",
            ),
            "specification": context.get(
                "specification", "",
            ),
            "operator_feedback": operator_feedback,
            "conversation_history": conversation_history,
            "model_name": context.get(
                "code_agent_model",
            ),
            "dt_config": context.get("dt_config"),
            "is_revision": bool(
                previous_code and review_feedback
            ),
            "compaction_model": context.get(
                "compaction_model",
            ),
            "compaction_threshold": context.get(
                "code_agent_compaction", 0.8,
            ),
            "dt_enabled": context.get(
                "dt_enabled", True,
            ),
        }
        for event in _timeout_step_stream(
            agent, ca_kwargs, step_start,
            step_num, "CodeAgent",
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
            elif etype == "code_report":
                code_report = event.get("code_report", {})
                if step_reasoning:
                    conversation_history.append({
                        "role": "model",
                        "type": "reasoning",
                        "text": step_reasoning,
                    })
                    step_reasoning = ""
                conversation_history.append({
                    "role": "model",
                    "type": "code_report",
                    "code_report": code_report,
                })
                yield {
                    "type": "sub_event",
                    "event": {"type": "report"},
                }
                yield {
                    "type": "output_chunk",
                    "text": (
                        "[CodeAgent] Code report produced.\n"
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
                        f"[CodeAgent] Running tool: "
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
                    result = agent.execute_tool(
                        tool_name, tool_args,
                    )
                    tool_result = result.get("result", {})
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
                        f"[CodeAgent] {tool_name} "
                        f"result: "
                        f"{str(output)[:500]}\n"
                    ),
                }

        if code_report is not None:
            break

    if code_report is None:
        code_report = {
            "executive_summary": (
                "CodeAgent did not produce a report "
                "within the step limit."
            ),
            "generated_code": "",
            "actions": [],
            "state_description": "",
            "verification_result": "",
            "verification_checks": [],
        }

    filtered_history = [
        {k: v for k, v in e.items()
         if k not in _INTERNAL_KEYS}
        for e in conversation_history
        if e.get("type") not in _FINAL_REPORT_TYPES
    ]
    try:
        DatabaseFacade.save_agent_report(
            agent_type="code",
            report=code_report,
            username=context.get("username", "system"),
            incident_id=context.get("incident_id"),
            conversation_history=filtered_history,
        )
    except Exception as e:
        logger.warning("Failed to save code report: %s", e)

    yield {
        "type": "done",
        "result": {"code_report": code_report},
    }


def run_code_reviewer_agent_stream(
    context: dict[str, Any],
    previous_review_summary: str = "",
) -> Generator[dict[str, Any], None, None]:
    """
    Run the CodeReviewerAgent sub-agent to completion.

    Auto-approves all sub-agent tool calls. Yields output_chunk
    events for progress, sub_event events for rich UI rendering,
    and a done event with the review_report.

    :param context: dict with system_description, incident_report,
        specification, operator_feedback, images,
        reviewer_agent_model, username, and last_code_report
    :param previous_review_summary: concise summary of prior
        review findings for re-review iterations
    :return: generator yielding event dicts
    """
    agent = CodeReviewerAgent()
    code_report = context.get("last_code_report", {})
    operator_feedback = context.get("operator_feedback", "")
    if previous_review_summary:
        operator_feedback += (
            "\n\n--- PREVIOUS REVIEW CONTEXT ---\n"
            "This is a RE-REVIEW iteration. The code "
            "was revised based on a previous review's "
            "findings. Below is a summary of what was "
            "already checked and found. Focus your "
            "review on:\n"
            "1. Verifying that the previously identified "
            "issues have been fixed.\n"
            "2. Checking for any NEW issues introduced "
            "by the revision.\n"
            "3. You may skip re-validating checks that "
            "passed in the previous review unless the "
            "revision could have affected them.\n\n"
            "## Previous Review Summary\n"
            f"{previous_review_summary}\n"
            "--- END PREVIOUS REVIEW CONTEXT ---"
        )
    validation_feedback = context.get(
        "validation_feedback", "",
    )
    if validation_feedback:
        operator_feedback += (
            "\n\n--- VALIDATION CONTEXT ---\n"
            "This code was revised to address issues "
            "found during policy validation on the "
            "digital twin. The validation feedback "
            "below describes what went wrong when the "
            "previous version of this MDP code was "
            "used to train an RL policy and execute "
            "it on the digital twin. Focus your "
            "review on verifying that the revised "
            "code properly addresses these validation "
            "issues.\n\n"
            "## Validation Feedback\n"
            f"{validation_feedback}\n"
            "--- END VALIDATION CONTEXT ---"
        )
    conversation_history: list[dict[str, Any]] = []
    review_report = None

    for step_num in range(MAX_INNER_STEPS):
        yield {
            "type": "output_chunk",
            "text": (
                f"[CodeReviewerAgent] Step "
                f"{step_num + 1}...\n"
            ),
        }

        step_reasoning = ""
        step_start = time.monotonic()
        cr_kwargs: dict[str, Any] = {
            "system_description": context.get(
                "system_description", "",
            ),
            "incident_report": context.get(
                "incident_report", "",
            ),
            "specification": context.get(
                "specification", "",
            ),
            "operator_feedback": operator_feedback,
            "code_report": code_report,
            "conversation_history": conversation_history,
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
                "code_reviewer_compaction", 0.8,
            ),
            "dt_enabled": context.get(
                "dt_enabled", True,
            ),
        }
        for event in _timeout_step_stream(
            agent, cr_kwargs, step_start,
            step_num, "CodeReviewerAgent",
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
            elif etype == "review_report":
                review_report = event.get(
                    "review_report", {},
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
                    "type": "review_report",
                    "review_report": review_report,
                })
                yield {
                    "type": "sub_event",
                    "event": {"type": "report"},
                }
                yield {
                    "type": "output_chunk",
                    "text": (
                        "[CodeReviewerAgent] Review "
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
                        f"[CodeReviewerAgent] Running "
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
                    tool_result = result.get("result", {})
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
                        f"[CodeReviewerAgent] "
                        f"{tool_name} result: "
                        f"{str(output)[:500]}\n"
                    ),
                }

        if review_report is not None:
            break

    if review_report is None:
        review_report = {
            "executive_summary": (
                "CodeReviewerAgent did not produce a "
                "report within the step limit."
            ),
            "findings": [],
            "missing_actions": [],
            "command_issues": [],
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
            agent_type="code_review",
            report=review_report,
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
        "result": {"review_report": review_report},
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
            out[key] = val[:_OUTPUT_LIMIT] + "... (truncated)"
        else:
            out[key] = val
    return out


TOOL_DISPATCH: dict[str, Callable[..., dict[str, Any]]] = {}

STREAMING_TOOL_DISPATCH: dict[
    str, Callable[..., Generator[dict[str, Any], None, None]]
] = {
    "run_code_agent": run_code_agent_stream,
    "run_code_reviewer_agent": run_code_reviewer_agent_stream,
}
