"""
Subtask scoring for IRBench evaluation.

Compares agent answers against ground truth using exact match,
substring match, regex match, or SSH verification commands.
"""
import re
from dataclasses import dataclass, field
from typing import Any

from ccs_response_planner_backend.irbench.ground_truth import (
    GROUND_TRUTH,
    GroundTruthEntry,
)
from ccs_response_planner_backend.irbench.scenarios import (
    Scenario,
)
from ccs_response_planner_backend.irbench.ssh_client import (
    SSHClient,
)


@dataclass
class SubtaskScore:
    """
    Scoring result for a single subtask.

    :param task_number: subtask number
    :param description: subtask description
    :param score: 0.0 or 1.0
    :param agent_answer: what the agent answered
    :param expected_answer: ground truth answer
    :param match_method: how the score was determined
    """

    task_number: int
    description: str
    score: float
    agent_answer: str
    expected_answer: str
    match_method: str


@dataclass
class ScenarioResult:
    """
    Aggregate evaluation result for one scenario.

    :param scenario_id: IRBench scenario number
    :param scenario_name: scenario name
    :param subtask_scores: per-subtask scores
    :param completion_rate: fraction of subtasks passed
    :param total_steps: total LLM tool-calling rounds
    :param wall_time_seconds: total wall-clock time
    :param assessment: full investigation report
    :param verification: verifier report
    """

    scenario_id: int
    scenario_name: str
    subtask_scores: list[SubtaskScore] = field(
        default_factory=list,
    )
    completion_rate: float = 0.0
    total_steps: int = 0
    wall_time_seconds: float = 0.0
    assessment: dict[str, Any] = field(
        default_factory=dict,
    )
    verification: dict[str, Any] = field(
        default_factory=dict,
    )


def _normalize(text: str) -> str:
    """
    Normalize text for comparison.

    :param text: input string
    :return: lowercased, stripped, collapsed whitespace
    """
    return " ".join(text.lower().strip().split())


def _score_exact(
    agent: str, expected: str,
) -> bool:
    """
    Case-insensitive exact match.

    :param agent: agent's answer
    :param expected: expected answer
    :return: True if they match
    """
    return _normalize(agent) == _normalize(expected)


def _score_substring(
    agent: str, expected: str,
) -> bool:
    """
    Check if expected is a substring of agent's answer.

    :param agent: agent's answer
    :param expected: expected substring
    :return: True if found
    """
    return _normalize(expected) in _normalize(agent)


def _score_regex(
    agent: str, pattern: str,
) -> bool:
    """
    Check if agent's answer matches a regex pattern.

    :param agent: agent's answer
    :param pattern: regex pattern
    :return: True if matched
    """
    return bool(re.search(
        pattern, agent, re.IGNORECASE,
    ))


def _score_verification(
    ssh_client: SSHClient | None,
    verify_command: str,
) -> bool:
    """
    Run a verification command via SSH.

    The subtask passes when the command exits with code 0
    or when the output contains ``PASS``.

    :param ssh_client: SSH client (None to skip)
    :param verify_command: shell command to run
    :return: True if verification passes
    """
    if ssh_client is None or not verify_command:
        return False
    result = ssh_client.exec(verify_command, timeout=30)
    exit_code = result.get("exit_code", -1)
    output = result.get("output", "")
    return exit_code == 0 or "PASS" in output


def score_subtask(
    agent_answer: str,
    ground_truth: GroundTruthEntry,
    ssh_client: SSHClient | None = None,
) -> tuple[float, str]:
    """
    Score a single subtask answer against ground truth.

    :param agent_answer: the agent's answer
    :param ground_truth: expected answer entry
    :param ssh_client: SSH client for verification
    :return: (score, match_method)
    """
    mt = ground_truth.match_type

    if mt == "exact":
        passed = _score_exact(
            agent_answer, ground_truth.answer,
        )
        return (1.0 if passed else 0.0, "exact")

    if mt == "substring":
        passed = _score_substring(
            agent_answer, ground_truth.answer,
        )
        return (1.0 if passed else 0.0, "substring")

    if mt == "regex":
        passed = _score_regex(
            agent_answer, ground_truth.answer,
        )
        return (1.0 if passed else 0.0, "regex")

    if mt == "verification":
        passed = _score_verification(
            ssh_client, ground_truth.verify_command,
        )
        return (
            1.0 if passed else 0.0, "verification",
        )

    return (0.0, "manual")


def score_scenario(
    report: dict[str, Any],
    scenario: Scenario,
    ssh_client: SSHClient | None = None,
) -> ScenarioResult:
    """
    Score all subtasks for a scenario.

    Extracts subtask answers from the agent's report and
    compares against ground truth.

    :param report: the consolidated orchestrator report
    :param scenario: the IRBench scenario
    :param ssh_client: SSH client for verification subtasks
    :return: a ScenarioResult with per-subtask scores
    """
    # Extract subtask answers from the assessment
    assessment = report.get("assessment", {})
    subtask_answers: dict[int, dict[str, Any]] = {}
    for ans in assessment.get("subtask_answers", []):
        if isinstance(ans, dict):
            num = ans.get("task_number")
            if num is not None:
                subtask_answers[int(num)] = ans

    scores: list[SubtaskScore] = []
    for subtask in scenario.subtasks:
        key = (scenario.id, subtask.number)
        gt = GROUND_TRUTH.get(key)
        agent_ans_data = subtask_answers.get(
            subtask.number, {},
        )
        agent_answer = str(
            agent_ans_data.get("answer", "")
        )

        if gt is None:
            # No ground truth — mark as unscored
            scores.append(SubtaskScore(
                task_number=subtask.number,
                description=subtask.description,
                score=0.0,
                agent_answer=agent_answer,
                expected_answer="(no ground truth)",
                match_method="unscored",
            ))
            continue

        score_val, method = score_subtask(
            agent_answer, gt, ssh_client,
        )
        scores.append(SubtaskScore(
            task_number=subtask.number,
            description=subtask.description,
            score=score_val,
            agent_answer=agent_answer,
            expected_answer=gt.answer,
            match_method=method,
        ))

    scored = [s for s in scores if s.match_method != "unscored"]
    completion_rate = (
        sum(s.score for s in scored) / len(scored)
        if scored else 0.0
    )

    return ScenarioResult(
        scenario_id=scenario.id,
        scenario_name=scenario.name,
        subtask_scores=scores,
        completion_rate=completion_rate,
        assessment=assessment,
        verification=report.get("verification", {}),
    )
