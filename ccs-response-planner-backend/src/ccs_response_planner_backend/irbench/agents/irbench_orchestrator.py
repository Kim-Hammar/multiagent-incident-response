"""
IRBench orchestrator -- per-subtask investigation with
Investigator + Verifier loop.

Pipeline -- For each subtask, invoke the Investigator with
a focused prompt (scenario + this subtask + prior answers).
After all subtasks, the Verifier reviews and gives feedback.
If needs_revision, the Investigator retries flagged subtasks.
"""
import base64
import json
import logging
import os
import time
from typing import Any, Callable

from google import genai  # type: ignore[attr-defined]
from google.genai import types as genai_types  # type: ignore[attr-defined]

from ccs_response_planner_backend.agents.stream_timeout import (
    iter_with_idle_timeout,
)
from ccs_response_planner_backend.irbench.config import (
    IRBenchConfig,
)
from ccs_response_planner_backend.irbench.scenarios import (
    Scenario,
    Subtask,
)
from ccs_response_planner_backend.irbench.ssh_client import (
    SSHClient,
)
from ccs_response_planner_backend.irbench.prompts import (
    report_agent as investigator_prompt,
    investigator_verifier as verifier_prompt,
)
from ccs_response_planner_backend.irbench.tools.tool_declarations import (
    INVESTIGATION_DECLARATIONS,
    INVESTIGATION_DECLARATIONS_NO_INFO,
    VERIFIER_DECLARATIONS,
)
from ccs_response_planner_backend.irbench.tools.tool_dispatch import (
    build_investigation_dispatch,
    build_verifier_dispatch,
)

logger = logging.getLogger(__name__)


# Max characters per tool result stored in conversation
# history.  Prevents a single large output (e.g. binary
# dump) from blowing past the 1M token context limit.
_MAX_RESULT_CHARS = 30_000


# ── Generic agent loop ───────────────────────────────────


def run_agent_loop(
    *,
    system_prompt: str,
    tool_declarations: list[Any],
    tool_dispatch: dict[str, Callable[..., Any]],
    final_tool_name: str,
    model_name: str = "gemini-3.1-pro-preview",
    thinking_budget: int = 8192,
    max_steps: int = 15,
    verbose: bool = True,
    print_prompts: bool = False,
    agent_label: str = "Agent",
) -> dict[str, Any]:
    """
    Run a Gemini function-calling agent loop to completion.

    :param system_prompt: the system instruction
    :param tool_declarations: Gemini FunctionDeclaration list
    :param tool_dispatch: maps tool names to callables
    :param final_tool_name: the tool that signals completion
    :param model_name: Gemini model name
    :param thinking_budget: thinking token budget
    :param max_steps: max LLM interaction rounds
    :param verbose: print progress to terminal
    :param agent_label: label for terminal output
    :return: the final tool call arguments
    """
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY", ""),
    )
    config = genai_types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=[genai_types.Tool(
            function_declarations=tool_declarations,
        )],
        tool_config=genai_types.ToolConfig(
            function_calling_config=(
                genai_types.FunctionCallingConfig(
                    mode="ANY",
                )
            ),
        ),
        thinking_config=genai_types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=thinking_budget,
        ),
        automatic_function_calling=(
            genai_types.AutomaticFunctionCallingConfig(
                disable=True,
            )
        ),
    )

    contents: list[dict[str, Any]] = [
        {
            "role": "user",
            "parts": [{
                "text": (
                    "Please begin. Use the available "
                    "tools to complete the task."
                ),
            }],
        },
    ]

    if print_prompts:
        print(f"\n{'.' * 60}")
        print(f"  [{agent_label}] System Prompt:")
        print(f"{'.' * 60}")
        print(system_prompt)
        print(f"{'.' * 60}\n")

    loop_start = time.monotonic()

    for step in range(max_steps):
        step_start = time.monotonic()
        elapsed_total = step_start - loop_start
        if verbose:
            print(
                f"\n  [{agent_label}] Step {step + 1}"
                f"/{max_steps} "
                f"(elapsed {elapsed_total:.0f}s)...",
            )

        full_text = ""
        thinking_trace = ""
        function_call = None
        all_parts: list[Any] = []

        try:
            raw_stream = (
                client.models.generate_content_stream(
                    model=model_name,
                    contents=contents,
                    config=config,
                )
            )
            for chunk in iter_with_idle_timeout(
                raw_stream,
            ):
                if not chunk.candidates:
                    continue
                candidate = chunk.candidates[0]
                if (
                    not candidate.content
                    or not candidate.content.parts
                ):
                    continue
                for part in candidate.content.parts:
                    all_parts.append(part)
                    if part.text:
                        if getattr(
                            part, "thought", False,
                        ):
                            thinking_trace += part.text
                        else:
                            full_text += part.text
                    if (
                        part.function_call
                        and part.function_call.name
                    ):
                        function_call = (
                            part.function_call
                        )
        except Exception as e:
            err_msg = str(e)
            if "token" in err_msg.lower():
                logger.warning(
                    "Context overflow: %s. "
                    "Returning best-effort answer.",
                    err_msg[:200],
                )
                return {
                    "answer": "",
                    "completed": False,
                    "error": (
                        "Context limit exceeded."
                    ),
                }
            raise

        if verbose and thinking_trace:
            print(f"    Thinking:\n{thinking_trace}")

        if verbose and full_text:
            print(f"    Text:\n{full_text}")

        if not function_call:
            if verbose:
                print(
                    f"    [{agent_label}] No tool call; "
                    f"ending loop."
                )
            return {"raw_text": full_text}

        tool_name = function_call.name
        tool_args = (
            dict(function_call.args)
            if function_call.args else {}
        )

        if verbose:
            args_preview = json.dumps(
                tool_args, default=str,
            )[:150]
            print(
                f"    Tool: {tool_name}"
                f"({args_preview})"
            )

        # Final tool — return the answer
        if tool_name == final_tool_name:
            if verbose:
                print(
                    f"    [{agent_label}] Answer "
                    f"produced."
                )
            return _normalize_args(tool_args)

        # Execute the tool
        fn = tool_dispatch.get(tool_name)
        if fn is None:
            result = {
                "error": f"Unknown tool: {tool_name}",
            }
        else:
            try:
                result = fn(**tool_args)
            except Exception as e:
                result = {
                    "error": f"{type(e).__name__}: {e}",
                }

        if verbose:
            step_elapsed = time.monotonic() - step_start
            result_preview = json.dumps(
                result, default=str,
            )[:200]
            print(
                f"    Result ({step_elapsed:.1f}s): "
                f"{result_preview}"
            )

        # Append to conversation history with
        # thought_signature preservation.
        model_parts = _serialize_parts(all_parts)
        contents.append({
            "role": "model",
            "parts": model_parts,
        })

        # Truncate tool output to prevent context
        # overflow (the 1M token limit).
        result_str = json.dumps(result, default=str)
        if len(result_str) > _MAX_RESULT_CHARS:
            result_str = (
                result_str[:_MAX_RESULT_CHARS]
                + "\n\n[TRUNCATED — output too large. "
                "Use more targeted commands.]"
            )

        nudge = ""
        if step >= max_steps - 3:
            nudge = (
                f" WARNING: You have "
                f"{max_steps - step - 1} step(s) "
                f"remaining. Call "
                f"`{final_tool_name}` now with "
                f"your best answer."
            )

        contents.append({
            "role": "user",
            "parts": [
                {
                    "function_response": {
                        "name": tool_name,
                        "response": {
                            "result": result_str,
                        },
                    },
                },
                {
                    "text": (
                        "Tool result received. "
                        "Analyze and decide next step."
                        + nudge
                    ),
                },
            ],
        })

    # Force final answer
    if verbose:
        print(
            f"    [{agent_label}] Max steps. "
            f"Forcing answer..."
        )
    contents.append({
        "role": "user",
        "parts": [{
            "text": (
                f"You have used all steps. Call "
                f"`{final_tool_name}` RIGHT NOW "
                f"with your best answer."
            ),
        }],
    })
    try:
        function_call = None
        raw_stream = (
            client.models.generate_content_stream(
                model=model_name,
                contents=contents,
                config=config,
            )
        )
        for chunk in iter_with_idle_timeout(raw_stream):
            if not chunk.candidates:
                continue
            candidate = chunk.candidates[0]
            if (
                not candidate.content
                or not candidate.content.parts
            ):
                continue
            for part in candidate.content.parts:
                if (
                    part.function_call
                    and part.function_call.name
                ):
                    function_call = part.function_call
        if (
            function_call
            and function_call.name == final_tool_name
        ):
            args = (
                dict(function_call.args)
                if function_call.args else {}
            )
            return _normalize_args(args)
    except Exception as e:
        logger.warning(
            "Forced answer call failed: %s", e,
        )
    return {
        "answer": "",
        "completed": False,
        "error": "Max steps without answer.",
    }


def _normalize_args(obj: Any) -> Any:
    """
    Recursively convert proto MapComposite to native dicts.

    :param obj: a proto value
    :return: a native Python value
    """
    if isinstance(
        obj, (bool, int, float, str, type(None)),
    ):
        return obj
    if hasattr(obj, "items"):
        return {
            str(k): _normalize_args(v)
            for k, v in obj.items()
        }
    if hasattr(obj, "__iter__"):
        return [_normalize_args(v) for v in obj]
    return obj


def _serialize_parts(
    parts: list[Any],
) -> list[dict[str, Any]]:
    """
    Serialize Gemini Part objects preserving thought_signature.

    :param parts: raw Gemini Part objects
    :return: list of JSON-serializable part dicts
    """
    result: list[dict[str, Any]] = []
    for part in parts:
        d: dict[str, Any] = {}
        if part.text:
            d["text"] = part.text
        fc = part.function_call
        if fc and fc.name:
            d["function_call"] = {
                "name": fc.name,
                "args": (
                    dict(fc.args) if fc.args else {}
                ),
            }
        if getattr(part, "thought", False):
            d["thought"] = True
        sig = getattr(part, "thought_signature", None)
        if sig:
            if isinstance(sig, str):
                d["thought_signature"] = (
                    base64.b64decode(sig)
                )
            else:
                d["thought_signature"] = sig
        if d:
            result.append(d)
    return result


def format_subtask_list(
    subtasks: list[Subtask],
) -> str:
    """
    Format subtasks as a numbered checklist.

    :param subtasks: list of Subtask objects
    :return: formatted string
    """
    lines: list[str] = []
    for st in subtasks:
        lines.append(
            f"{st.number}. [{st.task_type}] "
            f"{st.description}"
        )
    return "\n".join(lines)


def _format_prior_answers(
    answers: list[dict[str, Any]],
    subtasks: list[Subtask],
) -> str:
    """
    Format accumulated answers for the prompt context.

    :param answers: list of answer dicts with task_number,
        answer, evidence, etc.
    :param subtasks: the full subtask list
    :return: formatted string
    """
    if not answers:
        return ""
    subtask_map = {
        st.number: st for st in subtasks
    }
    lines: list[str] = []
    for ans in answers:
        num = ans.get("task_number", "?")
        st = subtask_map.get(num)
        desc = (
            st.description[:50] if st
            else "Unknown task"
        )
        answer = ans.get("answer", "(no answer)")
        lines.append(
            f"- Task {num} ({desc}): {answer}"
        )
    return "\n".join(lines)


# ── IRBench Orchestrator ─────────────────────────────────


class IRBenchOrchestrator:
    """
    Drives per-subtask investigation with Verifier review.

    For each subtask:
    1. Build focused prompt with prior answers as context
    2. Run Investigator agent loop → answer
    3. Print answer immediately
    4. Accumulate for next subtask

    Then: Verifier reviews all answers → feedback.
    If needs_revision: retry flagged subtasks.

    :param config: IRBench evaluation configuration
    :param ssh_client: SSH connection to the target
    """

    def __init__(
        self,
        config: IRBenchConfig,
        ssh_client: SSHClient,
    ) -> None:
        self._config = config
        self._ssh = ssh_client

    def run_scenario(
        self, scenario: Scenario,
    ) -> dict[str, Any]:
        """
        Execute per-subtask investigation + verification.

        :param scenario: the IRBench scenario to evaluate
        :return: report with all subtask answers
        """
        ssh_host = self._ssh._config.hostname
        ssh_user = self._ssh._config.username
        ssh_password = self._ssh._config.password

        inv_dispatch, _ = build_investigation_dispatch(
            self._ssh,
            info_tools_enabled=(
                self._config.info_tools_enabled
            ),
        )
        inv_declarations = (
            INVESTIGATION_DECLARATIONS
            if self._config.info_tools_enabled
            else INVESTIGATION_DECLARATIONS_NO_INFO
        )
        ver_dispatch, _ = build_verifier_dispatch(
            self._ssh,
        )

        answers: list[dict[str, Any]] = []
        verification: dict[str, Any] = {}
        feedback = ""

        for iteration in range(
            self._config.max_iterations,
        ):
            print(
                f"\n{'=' * 60}"
                f"\n  ITERATION {iteration + 1}/"
                f"{self._config.max_iterations}"
                f"\n{'=' * 60}"
            )

            # Determine which subtasks to (re-)investigate
            if iteration == 0:
                tasks_to_do = list(scenario.subtasks)
            else:
                # Re-investigate flagged subtasks only
                flagged = _get_flagged_tasks(
                    verification, scenario.subtasks,
                )
                if flagged:
                    tasks_to_do = flagged
                    print(
                        f"  Re-investigating "
                        f"{len(flagged)} flagged "
                        f"subtask(s)..."
                    )
                else:
                    print(
                        "  No specific subtasks "
                        "flagged — re-investigating "
                        "all."
                    )
                    tasks_to_do = list(
                        scenario.subtasks,
                    )

            # ── Per-subtask investigation ────────────
            for subtask in tasks_to_do:
                print(
                    f"\n{'─' * 60}"
                    f"\n  Task {subtask.number}/"
                    f"{len(scenario.subtasks)}: "
                    f"{subtask.description}"
                    f"\n  Type: {subtask.task_type}"
                    f"\n{'─' * 60}"
                )

                prior_text = _format_prior_answers(
                    answers, scenario.subtasks,
                )
                revision_notice = ""
                if feedback and iteration > 0:
                    revision_notice = (
                        "\n\n## Verifier Feedback\n\n"
                        "The verifier found issues "
                        "with a previous attempt. "
                        "Address the feedback:\n\n"
                        f"{feedback}\n"
                    )

                prompt = (
                    investigator_prompt
                    .build_system_prompt(
                        scenario_description=(
                            scenario.description
                        ),
                        keywords=", ".join(
                            scenario.keywords,
                        ),
                        platform=scenario.platform,
                        os_type=scenario.os_type,
                        difficulty=scenario.difficulty,
                        ssh_host=ssh_host,
                        ssh_user=ssh_user,
                        ssh_password=ssh_password,
                        task_number=subtask.number,
                        task_description=(
                            subtask.description
                        ),
                        task_type=subtask.task_type,
                        prior_answers=prior_text,
                        revision_notice=revision_notice,
                        info_tools_enabled=(
                            self._config
                            .info_tools_enabled
                        ),
                        ssh_timeout=(
                            self._config
                            .ssh_command_timeout
                        ),
                        max_steps=(
                            self._config
                            .max_steps_per_subtask
                        ),
                    )
                )

                result = run_agent_loop(
                    system_prompt=prompt,
                    tool_declarations=(
                        inv_declarations
                    ),
                    tool_dispatch=inv_dispatch,
                    final_tool_name=(
                        "produce_subtask_answer"
                    ),
                    model_name=(
                        self._config.model_name
                    ),
                    thinking_budget=(
                        self._config.thinking_budget
                    ),
                    max_steps=(
                        self._config
                        .max_steps_per_subtask
                    ),
                    verbose=self._config.verbose,
                    print_prompts=(
                        self._config.print_prompts
                    ),
                    agent_label=(
                        f"Task-{subtask.number}"
                    ),
                )

                # Store / update answer
                result["task_number"] = subtask.number
                _upsert_answer(answers, result)

                # Print answer immediately
                answer_text = result.get(
                    "answer", "(no answer)",
                )
                completed = result.get(
                    "completed", False,
                )
                status = (
                    "DONE" if completed else "TODO"
                )
                print(
                    f"\n  >>> [{status}] Task "
                    f"{subtask.number}: "
                    f"{answer_text[:100]}"
                )

            # ── Verifier phase ───────────────────────
            print(
                f"\n{'=' * 60}"
                f"\n  VERIFIER (iteration "
                f"{iteration + 1}/"
                f"{self._config.max_iterations})"
                f"\n{'=' * 60}"
            )

            all_answers_text = json.dumps(
                answers, indent=2, default=str,
            )
            subtask_list = format_subtask_list(
                scenario.subtasks,
            )
            ver_prompt = (
                verifier_prompt.build_system_prompt(
                    scenario_description=(
                        scenario.description
                    ),
                    keywords=", ".join(
                        scenario.keywords,
                    ),
                    platform=scenario.platform,
                    os_type=scenario.os_type,
                    difficulty=scenario.difficulty,
                    subtask_list=subtask_list,
                    investigator_report=(
                        all_answers_text
                    ),
                )
            )

            verification = run_agent_loop(
                system_prompt=ver_prompt,
                tool_declarations=(
                    VERIFIER_DECLARATIONS
                ),
                tool_dispatch=ver_dispatch,
                final_tool_name=(
                    "produce_verification_report"
                ),
                model_name=self._config.model_name,
                thinking_budget=(
                    self._config.thinking_budget
                ),
                max_steps=self._config.max_agent_steps,
                verbose=self._config.verbose,
                print_prompts=(
                    self._config.print_prompts
                ),
                agent_label="Verifier",
            )

            verdict = verification.get(
                "verdict", "approved",
            )
            summary = verification.get("summary", "")
            print(
                f"\n  Verdict: {verdict}"
                f"\n  Summary: {summary[:200]}"
            )

            if verdict == "approved":
                print("\n  Verifier approved.")
                break

            # Build feedback for next iteration
            subtask_fb = verification.get(
                "subtask_feedback", [],
            )
            fb_parts = [summary]
            for item in subtask_fb:
                if isinstance(item, dict):
                    num = item.get("task_number", "?")
                    issue = item.get("issue", "")
                    sug = item.get("suggestion", "")
                    fb_parts.append(
                        f"- Task {num}: {issue}"
                        + (f" Suggestion: {sug}"
                           if sug else "")
                    )
            feedback = "\n".join(fb_parts)

            if iteration < (
                self._config.max_iterations - 1
            ):
                print(
                    "\n  Verifier requested revision. "
                    "Retrying flagged subtasks..."
                )
            else:
                print(
                    "\n  Max iterations reached. "
                    "Using latest answers."
                )

        # Build final report in the format scorer expects
        return {
            "scenario_id": scenario.id,
            "scenario_name": scenario.name,
            "assessment": {
                "subtask_answers": answers,
            },
            "verification": verification,
            "iterations": iteration + 1,
        }


def _upsert_answer(
    answers: list[dict[str, Any]],
    new_answer: dict[str, Any],
) -> None:
    """
    Insert or update an answer in the list.

    :param answers: accumulated answer list
    :param new_answer: the new answer dict
    """
    num = new_answer.get("task_number")
    for i, ans in enumerate(answers):
        if ans.get("task_number") == num:
            answers[i] = new_answer
            return
    answers.append(new_answer)


def _get_flagged_tasks(
    verification: dict[str, Any],
    subtasks: list[Subtask],
) -> list[Subtask]:
    """
    Extract subtasks flagged by the verifier for revision.

    :param verification: verifier report
    :param subtasks: full subtask list
    :return: list of flagged Subtask objects
    """
    feedback = verification.get(
        "subtask_feedback", [],
    )
    flagged_nums: set[int] = set()
    for item in feedback:
        if isinstance(item, dict):
            num = item.get("task_number")
            if num is not None:
                flagged_nums.add(int(num))
    if not flagged_nums:
        return []
    return [
        st for st in subtasks
        if st.number in flagged_nums
    ]
