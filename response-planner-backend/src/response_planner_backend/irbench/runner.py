"""
IRBench evaluation runner.

Coordinates scenario loading, pipeline execution, scoring,
and result persistence for one or more IRBench scenarios.
"""
import json
import logging
import os
import time
from dataclasses import asdict

from response_planner_backend.irbench.agents.irbench_orchestrator import (
    IRBenchOrchestrator,
)
from response_planner_backend.irbench.config import (
    IRBenchConfig,
)
from response_planner_backend.irbench.scenarios import (
    load_scenario,
)
from response_planner_backend.irbench.scorer import (
    ScenarioResult,
    score_scenario,
)
from response_planner_backend.irbench.ssh_client import (
    SSHClient,
)

logger = logging.getLogger(__name__)


def _print_scenario_header(
    scenario_id: int,
    name: str,
    difficulty: str,
    platform: str,
    os_type: str,
    num_subtasks: int,
) -> None:
    """
    Print a scenario header to the terminal.
    """
    print(f"\n{'=' * 60}")
    print(f"  IRBench Scenario {scenario_id}: {name}")
    print(
        f"  {difficulty} | {platform} | "
        f"{os_type} | {num_subtasks} subtasks"
    )
    print(f"{'=' * 60}")


def _print_scenario_summary(
    result: ScenarioResult,
) -> None:
    """
    Print a scenario result summary to the terminal.
    """
    print(f"\n{'─' * 60}")
    print(
        f"  Results: {result.scenario_name} "
        f"({result.scenario_id})"
    )
    print(f"{'─' * 60}")
    print(
        f"  Completion Rate: "
        f"{result.completion_rate:.1%}"
    )
    print(
        f"  Wall Time: "
        f"{result.wall_time_seconds:.1f}s"
    )
    print()
    for s in result.subtask_scores:
        if s.match_method == "unscored":
            mark = "????"
        elif s.score > 0:
            mark = "PASS"
        else:
            mark = "FAIL"
        print(
            f"  [{mark}] Task {s.task_number}: "
            f"{s.description[:50]}"
        )
        if s.agent_answer:
            print(
                f"         Agent: "
                f"{s.agent_answer[:60]}"
            )
        if (
            s.expected_answer
            and s.match_method != "unscored"
        ):
            print(
                f"         Expected: "
                f"{s.expected_answer[:60]}"
            )
    print()


def _print_overall_summary(
    results: list[ScenarioResult],
) -> None:
    """
    Print an overall summary across all scenarios.
    """
    print(f"\n{'=' * 60}")
    print("  IRBench Overall Summary")
    print(f"{'=' * 60}")
    total_scored = 0
    total_passed = 0
    for r in results:
        scored = [
            s for s in r.subtask_scores
            if s.match_method != "unscored"
        ]
        passed = sum(
            1 for s in scored if s.score > 0
        )
        total_scored += len(scored)
        total_passed += passed
        rate = (
            f"{r.completion_rate:.1%}"
            if scored else "N/A"
        )
        print(
            f"  Scenario {r.scenario_id} "
            f"({r.scenario_name}): "
            f"{rate} "
            f"({passed}/{len(scored)} scored, "
            f"{len(r.subtask_scores)} total)"
        )
    if total_scored > 0:
        overall = total_passed / total_scored
        print(
            f"\n  Overall: {overall:.1%} "
            f"({total_passed}/{total_scored} scored)"
        )
    print(f"{'=' * 60}\n")


def _save_result(
    result: ScenarioResult,
    results_dir: str,
) -> str:
    """
    Save a scenario result to a JSON file.

    :param result: the scenario result to save
    :param results_dir: directory for result files
    :return: path to the saved file
    """
    os.makedirs(results_dir, exist_ok=True)
    filename = (
        f"scenario_{result.scenario_id}_"
        f"{int(time.time())}.json"
    )
    filepath = os.path.join(results_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(
            asdict(result), f,
            indent=2, default=str,
        )
    return filepath


class IRBenchRunner:
    """
    Run IRBench evaluation for one or more scenarios.

    :param config: IRBench evaluation configuration
    """

    def __init__(self, config: IRBenchConfig) -> None:
        self._config = config

    def run_scenario(
        self, scenario_id: int,
    ) -> ScenarioResult:
        """
        Run the full pipeline for a single scenario.

        :param scenario_id: IRBench scenario number
        :return: scored scenario result
        """
        scenario = load_scenario(
            scenario_id,
            irbench_dir=(
                self._config.irbench_dir or None
            ),
        )

        _print_scenario_header(
            scenario.id, scenario.name,
            scenario.difficulty, scenario.platform,
            scenario.os_type, len(scenario.subtasks),
        )

        ssh_config = self._config.ssh_configs.get(
            scenario_id,
        )
        if ssh_config is None:
            print(
                f"  ERROR: No SSH config for scenario "
                f"{scenario_id}. Add it to "
                f"IRBenchConfig.ssh_configs."
            )
            return ScenarioResult(
                scenario_id=scenario.id,
                scenario_name=scenario.name,
            )

        ssh_client = SSHClient(
            ssh_config,
            command_timeout=(
                self._config.ssh_command_timeout
            ),
        )

        start_time = time.monotonic()

        try:
            orchestrator = IRBenchOrchestrator(
                self._config, ssh_client,
            )
            report = orchestrator.run_scenario(scenario)
            result = score_scenario(
                report, scenario, ssh_client,
            )
        finally:
            ssh_client.close()

        result.wall_time_seconds = (
            time.monotonic() - start_time
        )

        # Save results
        filepath = _save_result(
            result, self._config.results_dir,
        )
        print(f"  Results saved to: {filepath}")

        _print_scenario_summary(result)
        return result

    def run_all(self) -> list[ScenarioResult]:
        """
        Run all configured scenarios sequentially.

        :return: list of scored results
        """
        results: list[ScenarioResult] = []
        for sid in self._config.scenario_ids:
            result = self.run_scenario(sid)
            results.append(result)

        _print_overall_summary(results)
        return results
