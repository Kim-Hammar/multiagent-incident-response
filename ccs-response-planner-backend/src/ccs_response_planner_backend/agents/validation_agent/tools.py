"""
Tool dispatch for the ValidationAgent.

Provides ``dt_exec`` for running commands on digital-twin containers,
``query_policy`` for querying a trained RL policy, and
``run_action_validators`` for parallel action validation.
"""
import base64
import json
import logging
import queue
import textwrap
import threading
import time
from typing import Any, Callable, Generator

import docker
import httpx

from ccs_response_planner_backend.agents.shared_tools import (
    dt_exec,
    dt_exec_stream,
    dt_restart,
    dt_restart_stream,
)
from ccs_response_planner_backend.constants.constants import DOCKER
from ccs_response_planner_backend.db.database_facade import (
    DatabaseFacade,
)

logger = logging.getLogger(__name__)

_CONCURRENCY_LIMIT = 3
_MAX_INNER_STEPS = 50
_OUTPUT_LIMIT = 2000

_INTERNAL_KEYS = {
    "_model_parts", "_anthropic_content",
    "_tool_use_id", "_vendor",
}
_FINAL_REPORT_TYPES = {"action_validation"}

_QUERY_POLICY_SCRIPT = textwrap.dedent("""\
    import json, sys, importlib.util, numpy as np
    from sb3_contrib import MaskablePPO
    spec = importlib.util.spec_from_file_location(
        "_env", "/workspace/_env.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    import gymnasium
    EnvClass = None
    for name in dir(mod):
        obj = getattr(mod, name)
        if (isinstance(obj, type)
                and issubclass(obj, gymnasium.Env)
                and obj is not gymnasium.Env):
            EnvClass = obj
            break
    env = EnvClass()
    expected_dims = env.observation_space.shape[0]
    state_arr = np.array(STATE_VEC, dtype=np.float32)
    if len(state_arr) != expected_dims:
        print(json.dumps({
            "error": (
                f"Dimension mismatch: expected "
                f"{expected_dims}, got {len(state_arr)}. "
                f"Check the Code Agent Report for the "
                f"correct state vector format."
            ),
            "expected_dimensions": expected_dims,
            "got_dimensions": len(state_arr)
        }))
        sys.exit(0)
    env.set_state(state_arr)
    mask = env.get_action_mask()
    model = MaskablePPO.load("/workspace/_policy", env=env)
    action, _ = model.predict(
        state_arr, action_masks=mask, deterministic=False
    )
    action_idx = int(action)
    actions = env.get_actions()
    a = actions[action_idx] if action_idx < len(actions) else {}
    mask_list = [bool(m) for m in mask]
    print(json.dumps({
        "action_index": action_idx,
        "name": a.get("name", f"action_{action_idx}"),
        "description": a.get("description", ""),
        "commands": a.get("commands", []),
        "action_mask": mask_list,
        "valid_action_count": sum(mask_list),
        "total_action_count": len(mask_list)
    }))
""")


def query_policy(state: list[float]) -> dict[str, Any]:
    """
    Query the trained RL policy for the best action given a state.

    Runs a Python script in the sandbox that loads the environment
    and policy, sets the environment state, computes the action mask,
    and calls model.predict with masking applied.

    :param state: the current state vector
    :return: dict with action_index, name, description, commands,
             action_mask, valid_action_count, total_action_count
    """
    script = _QUERY_POLICY_SCRIPT.replace(
        "STATE_VEC",
        repr(state),
    )

    client = docker.from_env()
    try:
        ct = client.containers.get(
            DOCKER.PYTHON_SANDBOX_CONTAINER,
        )
        if ct.status != "running":
            ct.start()
    except docker.errors.NotFound:
        return {
            "error": "Python sandbox not running. "
            "Policy may not be loaded.",
        }

    encoded = base64.b64encode(
        script.encode("utf-8"),
    ).decode("ascii")
    write_cmd = (
        f"python3 -c \"import base64; "
        f"open('/workspace/_query.py','wb')"
        f".write(base64.b64decode('{encoded}'))\""
    )
    client.api.exec_start(
        client.api.exec_create(
            ct.id, ["/bin/sh", "-c", write_cmd],
            stdout=True, stderr=True,
        )["Id"],
    )

    exec_id = client.api.exec_create(
        ct.id,
        ["/bin/sh", "-c",
         "python3 /workspace/_query.py 2>&1"],
        stdout=True, stderr=True,
    )["Id"]
    output = client.api.exec_start(exec_id).decode(
        "utf-8", errors="replace",
    )
    exit_code = client.api.exec_inspect(exec_id)[
        "ExitCode"
    ]

    if exit_code != 0:
        return {
            "error": f"Policy query failed "
            f"(exit {exit_code}): {output.strip()}",
        }

    for line in output.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            return dict(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            continue

    return {"error": f"No JSON output: {output.strip()}"}


def _truncate_sub_result(
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    Truncate long string values in a sub-agent tool result.

    :param result: the original tool result dict
    :return: a truncated copy of the result
    """
    out: dict[str, Any] = {}
    for key, val in result.items():
        if key == "image":
            out[key] = val
        elif (
            isinstance(val, str)
            and len(val) > _OUTPUT_LIMIT
        ):
            out[key] = (
                val[:_OUTPUT_LIMIT]
                + "... (truncated)"
            )
        else:
            out[key] = val
    return out


def _run_single_action_validator(
    action: dict[str, Any],
    context: dict[str, Any],
    event_queue: "queue.Queue[dict[str, Any]]",
    semaphore: threading.Semaphore,
) -> None:
    """
    Run an ActionValidatorAgent for a single action.

    Puts tagged sub_event dicts onto *event_queue*.
    When finished, puts an ``_agent_done`` sentinel.

    :param action: dict with action_name and
        action_description
    :param context: incident context dict
    :param event_queue: shared queue for events
    :param semaphore: limits concurrent LLM calls
    """
    from ccs_response_planner_backend.agents.action_validator_agent.agent import (  # noqa: E501
        ActionValidatorAgent,
    )

    agent_id = action.get(
        "action_name", "unknown",
    )
    agent_label = f"Validation of {agent_id}"

    try:
        agent = ActionValidatorAgent()
        conversation_history: list[dict[str, Any]] = []
        action_validation = None

        for step_num in range(_MAX_INNER_STEPS):
            event_queue.put({
                "type": "sub_event",
                "agent_id": agent_id,
                "agent_label": agent_label,
                "event": {
                    "type": "text_delta",
                    "text": (
                        f"Step {step_num + 1}...\n"
                    ),
                },
            })

            step_reasoning = ""
            step_start = time.monotonic()

            av_kwargs: dict[str, Any] = {
                "system_description": context.get(
                    "system_description", "",
                ),
                "action_to_validate": action.get(
                    "action_description", "",
                ),
                "operator_feedback": context.get(
                    "operator_feedback", "",
                ),
                "conversation_history": (
                    conversation_history
                ),
                "images": context.get("images"),
                "model_name": context.get(
                    "action_validator_model",
                ),
                "dt_config": context.get("dt_config"),
            }

            with semaphore:
                try:
                    for event in agent.step_stream(
                        **av_kwargs,
                    ):
                        etype = event.get("type")

                        if etype == "system_prompt":
                            event_queue.put({
                                "type": "sub_event",
                                "agent_id": agent_id,
                                "agent_label": (
                                    agent_label
                                ),
                                "event": {
                                    "type": "prompt",
                                    "text": event.get(
                                        "text", "",
                                    ),
                                    "images": event.get(
                                        "images", [],
                                    ),
                                },
                            })
                        elif etype == "thinking":
                            step_reasoning += (
                                event.get("delta", "")
                            )
                            event_queue.put({
                                "type": "sub_event",
                                "agent_id": agent_id,
                                "agent_label": (
                                    agent_label
                                ),
                                "event": {
                                    "type": (
                                        "thinking_delta"
                                    ),
                                    "text": event.get(
                                        "delta", "",
                                    ),
                                },
                            })
                        elif etype == "text":
                            step_reasoning += (
                                event.get("delta", "")
                            )
                            event_queue.put({
                                "type": "sub_event",
                                "agent_id": agent_id,
                                "agent_label": (
                                    agent_label
                                ),
                                "event": {
                                    "type": (
                                        "text_delta"
                                    ),
                                    "text": event.get(
                                        "delta", "",
                                    ),
                                },
                            })
                        elif etype == "action_validation":
                            action_validation = (
                                event.get(
                                    "action_validation",
                                    {},
                                )
                            )
                            if step_reasoning:
                                conversation_history.append({
                                    "role": "model",
                                    "type": "reasoning",
                                    "text": (
                                        step_reasoning
                                    ),
                                })
                                step_reasoning = ""
                            conversation_history.append({
                                "role": "model",
                                "type": (
                                    "action_validation"
                                ),
                                "action_validation": (
                                    action_validation
                                ),
                            })
                            event_queue.put({
                                "type": "sub_event",
                                "agent_id": agent_id,
                                "agent_label": (
                                    agent_label
                                ),
                                "event": {
                                    "type": "report",
                                    "action_validation": (
                                        action_validation
                                    ),
                                },
                            })
                        elif etype == "context_usage":
                            event_queue.put({
                                "type": "sub_event",
                                "agent_id": agent_id,
                                "agent_label": (
                                    agent_label
                                ),
                                "event": {
                                    "type": (
                                        "context_usage"
                                    ),
                                    "prompt_tokens": (
                                        event.get(
                                            "prompt_tokens",
                                            0,
                                        )
                                    ),
                                    "candidates_tokens": (
                                        event.get(
                                            "candidates_tokens",
                                            0,
                                        )
                                    ),
                                    "total_tokens": (
                                        event.get(
                                            "total_tokens",
                                            0,
                                        )
                                    ),
                                    "context_limit": (
                                        event.get(
                                            "context_limit",
                                            0,
                                        )
                                    ),
                                },
                            })
                        elif etype == "tool_proposal":
                            tool_name = event.get(
                                "tool_name", "",
                            )
                            tool_args = event.get(
                                "tool_args", {},
                            )
                            event_queue.put({
                                "type": "sub_event",
                                "agent_id": agent_id,
                                "agent_label": (
                                    agent_label
                                ),
                                "event": {
                                    "type": "tool_call",
                                    "tool_name": (
                                        tool_name
                                    ),
                                    "tool_args": (
                                        tool_args
                                    ),
                                },
                            })
                            if step_reasoning:
                                conversation_history.append({
                                    "role": "model",
                                    "type": "reasoning",
                                    "text": (
                                        step_reasoning
                                    ),
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
                                "_model_parts": (
                                    event.get(
                                        "_model_parts",
                                    )
                                ),
                                "_vendor": event.get(
                                    "_vendor",
                                ),
                            })
                            conversation_history.append({
                                "role": "user",
                                "type": "tool_approval",
                                "tool_name": tool_name,
                                "approved": True,
                            })
                            try:
                                result = (
                                    agent.execute_tool(
                                        tool_name,
                                        tool_args,
                                    )
                                )
                                tool_result = result.get(
                                    "result", {},
                                )
                                if result.get("error"):
                                    tool_result = {
                                        "error": (
                                            result[
                                                "error"
                                            ]
                                        ),
                                    }
                            except Exception as e:
                                tool_result = {
                                    "error": str(e),
                                }
                            conversation_history.append({
                                "role": "tool",
                                "type": "tool_result",
                                "tool_name": tool_name,
                                "result": tool_result,
                            })
                            sub_result = (
                                _truncate_sub_result(
                                    tool_result,
                                )
                            )
                            event_queue.put({
                                "type": "sub_event",
                                "agent_id": agent_id,
                                "agent_label": (
                                    agent_label
                                ),
                                "event": {
                                    "type": (
                                        "tool_result"
                                    ),
                                    "tool_name": (
                                        tool_name
                                    ),
                                    "result": (
                                        sub_result
                                    ),
                                },
                            })
                except (
                    TimeoutError,
                    OSError,
                    httpx.TimeoutException,
                ) as e:
                    elapsed = round(
                        time.monotonic() - step_start,
                    )
                    logger.error(
                        "ActionValidator[%s] step %d "
                        "TIMED OUT after %ds: %s",
                        agent_id, step_num + 1,
                        elapsed, e,
                    )
                    event_queue.put({
                        "type": "sub_event",
                        "agent_id": agent_id,
                        "agent_label": agent_label,
                        "event": {
                            "type": "text_delta",
                            "text": (
                                f"Timeout after "
                                f"{elapsed}s: {e}\n"
                            ),
                        },
                    })
                    break

            if action_validation is not None:
                break

        if action_validation is None:
            action_validation = {
                "action_name": agent_id,
                "executive_summary": (
                    "ActionValidatorAgent did not "
                    "produce a validation within the "
                    "step limit."
                ),
            }

        filtered_history = [
            {k: v for k, v in e.items()
             if k not in _INTERNAL_KEYS}
            for e in conversation_history
            if e.get("type") not in _FINAL_REPORT_TYPES
        ]
        try:
            DatabaseFacade.save_agent_report(
                agent_type="action-validator",
                report=action_validation,
                username=context.get(
                    "username", "system",
                ),
                incident_id=context.get("incident_id"),
                conversation_history=filtered_history,
                model_name=context.get(
                    "action_validator_model",
                ),
            )
        except Exception as e:
            logger.warning(
                "Failed to save action-validator "
                "report for %s: %s", agent_id, e,
            )

        event_queue.put({
            "type": "_agent_done",
            "agent_id": agent_id,
            "agent_label": agent_label,
            "action_validation": action_validation,
        })
    except Exception as exc:
        logger.exception(
            "ActionValidator[%s] failed: %s",
            agent_id, exc,
        )
        event_queue.put({
            "type": "sub_event",
            "agent_id": agent_id,
            "agent_label": agent_label,
            "event": {
                "type": "text_delta",
                "text": f"Error: {exc}\n",
            },
        })
        event_queue.put({
            "type": "_agent_done",
            "agent_id": agent_id,
            "agent_label": agent_label,
            "action_validation": {
                "action_name": agent_id,
                "error": str(exc),
            },
        })


def run_action_validators_stream(
    actions: list[dict[str, Any]],
    context: dict[str, Any] | None = None,
) -> Generator[dict[str, Any], None, None]:
    """
    Run parallel ActionValidatorAgents for multiple actions.

    Spawns one thread per action, each running an
    ActionValidatorAgent to completion with auto-approved
    tool calls. Uses a shared queue to yield tagged
    sub_event dicts and a final done event.

    :param actions: list of dicts with action_name and
        action_description
    :param context: incident context dict injected by
        the route handler
    :return: generator yielding event dicts
    """
    ctx = context or {}
    if not actions:
        yield {
            "type": "done",
            "result": {"action_validations": {}},
        }
        return

    yield {
        "type": "sub_event",
        "event": {
            "type": "parallel_start",
            "hosts": [
                {
                    "agent_id": a.get(
                        "action_name",
                        f"action_{i}",
                    ),
                    "agent_label": (
                        f"Validation of "
                        f"{a.get('action_name', f'action_{i}')}"
                    ),
                }
                for i, a in enumerate(actions)
            ],
        },
    }

    event_queue: queue.Queue[dict[str, Any]] = (
        queue.Queue()
    )
    semaphore = threading.Semaphore(_CONCURRENCY_LIMIT)
    threads: list[threading.Thread] = []

    for action in actions:
        t = threading.Thread(
            target=_run_single_action_validator,
            args=(action, ctx, event_queue, semaphore),
            daemon=True,
        )
        threads.append(t)
        t.start()

    done_count = 0
    total = len(actions)
    action_validations: dict[str, Any] = {}

    while done_count < total:
        try:
            event = event_queue.get(timeout=600)
        except queue.Empty:
            yield {
                "type": "output_chunk",
                "text": (
                    "[ActionValidators] Timed out "
                    "waiting for agents.\n"
                ),
            }
            break

        if event.get("type") == "_agent_done":
            done_count += 1
            agent_id = event.get("agent_id", "")
            action_validations[agent_id] = event.get(
                "action_validation", {},
            )
            yield {
                "type": "sub_event",
                "agent_id": agent_id,
                "agent_label": event.get(
                    "agent_label", agent_id,
                ),
                "event": {"type": "agent_done"},
            }
            yield {
                "type": "output_chunk",
                "text": (
                    f"[ActionValidators] {agent_id} "
                    f"done ({done_count}/{total}).\n"
                ),
            }
        else:
            yield event

    for t in threads:
        t.join(timeout=5)

    yield {
        "type": "done",
        "result": {
            "action_validations": action_validations,
        },
    }


TOOL_DISPATCH: dict[str, Callable[..., dict[str, Any]]] = {
    "dt_exec": dt_exec,
    "dt_restart": dt_restart,
    "query_policy": query_policy,
}

STREAMING_TOOL_DISPATCH: dict[
    str, Callable[..., Generator[dict[str, Any], None, None]]
] = {
    "dt_exec": dt_exec_stream,
    "dt_restart": dt_restart_stream,
    "run_action_validators": run_action_validators_stream,
}
