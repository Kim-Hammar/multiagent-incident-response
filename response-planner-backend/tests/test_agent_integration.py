"""
Integration tests that exercise the full agent loop with real LLM calls.

Uses gemini-2.0-flash (cheapest/fastest) and API keys from .env.
Verifies that agents reason, call tools, and produce structured reports.

Run::

    cd response-planner-backend
    set -a && source ../.env && set +a
    pytest tests/test_agent_integration.py -v --timeout=600

Skip Docker-dependent tests::

    pytest tests/test_agent_integration.py -v -m "not docker" --timeout=600

Skip slow tests::

    pytest tests/test_agent_integration.py -v -m "not slow" --timeout=120
"""
import json
import logging
import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from response_planner_backend.constants.constants import EXAMPLES

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Skip markers
# -------------------------------------------------------------------
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
skip_no_gemini = pytest.mark.skipif(
    not GEMINI_KEY, reason="GEMINI_API_KEY not set",
)
MODEL = "gemini-2.5-flash"


def _docker_available() -> bool:
    """
    Check whether the Docker daemon is reachable.

    :return: True when docker is importable and the daemon responds
    """
    try:
        import docker  # noqa: F811
        docker.from_env().ping()
        return True
    except Exception:
        return False


skip_no_docker = pytest.mark.skipif(
    not _docker_available(),
    reason="Docker daemon not reachable",
)

# -------------------------------------------------------------------
# Shared test data
# -------------------------------------------------------------------
SYSTEM_DESC = EXAMPLES.SYSTEM_DESCRIPTION
SECURITY_ALERTS = EXAMPLES.SECURITY_ALERTS
OPERATOR_FEEDBACK = EXAMPLES.OPERATOR_FEEDBACK
SPECIFICATION = EXAMPLES.SPECIFICATION
INCIDENT_REPORT = EXAMPLES.INCIDENT_REPORT
RESPONSE_PLAN = EXAMPLES.RESPONSE_PLAN

MINIMAL_CODE_REPORT: dict[str, Any] = {
    "environment_code": "class Env: pass",
    "action_definitions": "[]",
    "gym_verification": "skipped",
}

MINIMAL_PLANNER_REPORT: dict[str, Any] = {
    "training_summary": "placeholder",
    "response_plan": RESPONSE_PLAN,
    "policy_available": False,
}

# -------------------------------------------------------------------
# Agent loop helper
# -------------------------------------------------------------------


def run_agent_loop(
    agent: Any,
    step_kwargs: dict[str, Any],
    tool_dispatch: dict[str, Any],
    streaming_dispatch: dict[str, Any],
    report_event_type: str,
    context: dict[str, Any] | None = None,
    max_steps: int = 50,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """
    Run an agent's multi-step loop to completion.

    Mirrors the ``_run_sub_agent_loop`` pattern from
    ``plan_manager_agent/tools.py``: auto-approves tool calls,
    feeds results back, and loops until a report event.

    :param agent: the agent instance
    :param step_kwargs: kwargs forwarded to agent.step_stream()
    :param tool_dispatch: non-streaming TOOL_DISPATCH dict
    :param streaming_dispatch: STREAMING_TOOL_DISPATCH dict
    :param report_event_type: event type signalling completion
    :param context: optional context dict for streaming tools
    :param max_steps: safety cap on number of turns
    :return: (all_events, report_event_or_None)
    """
    events: list[dict[str, Any]] = []
    conversation_history: list[dict[str, Any]] = (
        step_kwargs.setdefault("conversation_history", [])
    )
    report = None

    for step_num in range(max_steps):
        logger.info("Agent step %d", step_num + 1)
        pending_tool = None

        for event in agent.step_stream(**step_kwargs):
            events.append(event)
            etype = event.get("type")
            if etype == "tool_proposal":
                pending_tool = event
            elif etype == report_event_type:
                return events, event

        if pending_tool is None:
            break

        tool_name = pending_tool["tool_name"]
        tool_args = pending_tool.get("tool_args", {})
        logger.info("Auto-approving tool: %s", tool_name)

        conversation_history.append({
            "role": "model",
            "type": "tool_proposal",
            "tool_name": tool_name,
            "tool_args": tool_args,
            "rationale": pending_tool.get("rationale", ""),
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

        tool_result: dict[str, Any] = {}
        if tool_name in streaming_dispatch:
            try:
                for tool_event in agent.execute_tool_stream(
                    tool_name, tool_args, context=context,
                ):
                    events.append(tool_event)
                    te_type = tool_event.get("type")
                    if te_type == "done":
                        done_result = tool_event.get("result")
                        if done_result is not None:
                            tool_result = done_result
                        else:
                            tool_result = {
                                k: v
                                for k, v in tool_event.items()
                                if k != "type"
                            }
                    elif te_type == "error":
                        tool_result["error"] = (
                            tool_event.get("message", "error")
                        )
            except Exception as exc:
                tool_result = {"error": str(exc)}
        else:
            try:
                result_obj = agent.execute_tool(
                    tool_name, tool_args,
                )
                if result_obj.get("error"):
                    tool_result = {
                        "error": result_obj["error"],
                    }
                else:
                    tool_result = result_obj.get(
                        "result", result_obj,
                    )
            except Exception as exc:
                tool_result = {"error": str(exc)}

        conversation_history.append({
            "role": "tool",
            "type": "tool_result",
            "tool_name": tool_name,
            "result": tool_result,
        })

    return events, report


# -------------------------------------------------------------------
# DB mock fixture for manager agents
# -------------------------------------------------------------------
_DB_PATCH_TARGETS = [
    "response_planner_backend.agents"
    ".report_manager_agent.tools.DatabaseFacade",
    "response_planner_backend.agents"
    ".code_manager_agent.tools.DatabaseFacade",
    "response_planner_backend.agents"
    ".plan_manager_agent.tools.DatabaseFacade",
]


@pytest.fixture()
def mock_db():
    """
    Patch DatabaseFacade in all sub-agent tool modules.

    Manager streaming tools call DatabaseFacade.save_agent_report()
    and get_digital_twin_config(); a MagicMock silences those calls.

    :return: yields nothing; patches are active for the test duration
    """
    patchers = []
    for target in _DB_PATCH_TARGETS:
        p = patch(target, new=MagicMock())
        p.start()
        patchers.append(p)
    yield
    for p in patchers:
        p.stop()


# ===================================================================
# Leaf agent tests
# ===================================================================

@skip_no_gemini
@pytest.mark.slow
class TestReportAgentIntegration:
    """Integration test for ReportAgent (assessment generation)."""

    def test_produces_assessment(self):
        """
        ReportAgent should gather information via tools and produce
        a structured assessment.
        """
        from response_planner_backend.agents.report_agent.agent import (
            ReportAgent,
        )
        from response_planner_backend.agents.report_agent.tools import (
            STREAMING_TOOL_DISPATCH,
            TOOL_DISPATCH,
        )

        agent = ReportAgent()
        events, report = run_agent_loop(
            agent=agent,
            step_kwargs={
                "system_description": SYSTEM_DESC,
                "security_alerts": SECURITY_ALERTS,
                "operator_feedback": OPERATOR_FEEDBACK,
                "model_name": MODEL,
                "compaction_threshold": 0.0,
            },
            tool_dispatch=TOOL_DISPATCH,
            streaming_dispatch=STREAMING_TOOL_DISPATCH,
            report_event_type="assessment",
        )
        assert report is not None, (
            "ReportAgent did not produce an assessment"
        )
        assert "assessment" in report
        assert report["assessment"], "Assessment is empty"
        tool_calls = [
            e for e in events
            if e.get("type") == "tool_proposal"
        ]
        assert len(tool_calls) >= 1, (
            "Expected at least 1 tool call"
        )


@skip_no_gemini
@skip_no_docker
@pytest.mark.slow
@pytest.mark.docker
class TestCodeAgentIntegration:
    """Integration test for CodeAgent (Gymnasium env generation)."""

    def test_produces_code_report(self):
        """
        CodeAgent should write a Gymnasium environment and produce
        a structured code report.
        """
        from response_planner_backend.agents.code_agent.agent import (
            CodeAgent,
        )
        from response_planner_backend.agents.code_agent.tools import (
            STREAMING_TOOL_DISPATCH,
            TOOL_DISPATCH,
        )

        agent = CodeAgent()
        events, report = run_agent_loop(
            agent=agent,
            step_kwargs={
                "system_description": SYSTEM_DESC,
                "incident_report": INCIDENT_REPORT,
                "specification": SPECIFICATION,
                "operator_feedback": OPERATOR_FEEDBACK,
                "model_name": MODEL,
                "compaction_threshold": 0.0,
            },
            tool_dispatch=TOOL_DISPATCH,
            streaming_dispatch=STREAMING_TOOL_DISPATCH,
            report_event_type="code_report",
        )
        assert report is not None, (
            "CodeAgent did not produce a code report"
        )
        assert "code_report" in report


@skip_no_gemini
@skip_no_docker
@pytest.mark.slow
@pytest.mark.docker
class TestPlannerAgentIntegration:
    """Integration test for PlannerAgent (RL training)."""

    def test_produces_planner_report(self):
        """
        PlannerAgent should train a policy and produce a planner report.
        """
        from response_planner_backend.agents.planner_agent.agent import (
            PlannerAgent,
        )
        from response_planner_backend.agents.planner_agent.tools import (
            STREAMING_TOOL_DISPATCH,
            TOOL_DISPATCH,
        )

        agent = PlannerAgent()
        events, report = run_agent_loop(
            agent=agent,
            step_kwargs={
                "system_description": SYSTEM_DESC,
                "incident_report": INCIDENT_REPORT,
                "specification": SPECIFICATION,
                "operator_feedback": OPERATOR_FEEDBACK,
                "code_report": MINIMAL_CODE_REPORT,
                "model_name": MODEL,
                "time_limit_minutes": 2,
                "compaction_threshold": 0.0,
            },
            tool_dispatch=TOOL_DISPATCH,
            streaming_dispatch=STREAMING_TOOL_DISPATCH,
            report_event_type="planner_report",
        )
        assert report is not None, (
            "PlannerAgent did not produce a planner report"
        )
        assert "planner_report" in report


@skip_no_gemini
@skip_no_docker
@pytest.mark.slow
@pytest.mark.docker
class TestPlanVerifierAgentIntegration:
    """Integration test for PlanVerifierAgent."""

    def test_produces_plan_verifier_report(self):
        """
        PlanVerifierAgent should execute DT commands and produce
        a plan verifier report.
        """
        from response_planner_backend.agents.plan_verifier_agent.agent import (  # noqa: E501
            PlanVerifierAgent,
        )
        from response_planner_backend.agents.plan_verifier_agent.tools import (  # noqa: E501
            STREAMING_TOOL_DISPATCH,
            TOOL_DISPATCH,
        )

        agent = PlanVerifierAgent()
        events, report = run_agent_loop(
            agent=agent,
            step_kwargs={
                "system_description": SYSTEM_DESC,
                "incident_report": INCIDENT_REPORT,
                "response_plan": RESPONSE_PLAN,
                "specification": SPECIFICATION,
                "planner_report": MINIMAL_PLANNER_REPORT,
                "code_report": MINIMAL_CODE_REPORT,
                "model_name": MODEL,
                "has_policy": False,
                "compaction_threshold": 0.0,
            },
            tool_dispatch=TOOL_DISPATCH,
            streaming_dispatch=STREAMING_TOOL_DISPATCH,
            report_event_type="plan_verifier_report",
        )
        assert report is not None, (
            "PlanVerifierAgent did not produce a plan verifier report"
        )
        assert "plan_verifier_report" in report


# ===================================================================
# Manager agent tests
# ===================================================================

@skip_no_gemini
@pytest.mark.slow
@pytest.mark.usefixtures("mock_db")
class TestReportManagerIntegration:
    """Integration test for ReportManagerAgent."""

    def test_orchestrates_report_flow(self):
        """
        ReportManagerAgent should invoke run_report_agent (and
        optionally the reviewer) then produce a manager report.
        """
        from response_planner_backend.agents.report_manager_agent.agent import (  # noqa: E501
            ReportManagerAgent,
        )
        from response_planner_backend.agents.report_manager_agent.tools import (  # noqa: E501
            STREAMING_TOOL_DISPATCH,
            TOOL_DISPATCH,
        )

        context = {
            "system_description": SYSTEM_DESC,
            "security_alerts": SECURITY_ALERTS,
            "operator_feedback": OPERATOR_FEEDBACK,
            "images": [],
            "report_agent_model": MODEL,
            "reviewer_agent_model": MODEL,
            "username": "test",
            "dt_config": None,
            "compaction_model": None,
            "compaction_threshold": 0.0,
        }
        agent = ReportManagerAgent()
        events, report = run_agent_loop(
            agent=agent,
            step_kwargs={
                "system_description": SYSTEM_DESC,
                "security_alerts": SECURITY_ALERTS,
                "operator_feedback": OPERATOR_FEEDBACK,
                "model_name": MODEL,
                "max_iterations": 1,
                "compaction_threshold": 0.0,
            },
            tool_dispatch=TOOL_DISPATCH,
            streaming_dispatch=STREAMING_TOOL_DISPATCH,
            report_event_type="report_manager_report",
            context=context,
        )
        assert report is not None, (
            "ReportManagerAgent did not produce a report"
        )
        assert "report_manager_report" in report
        tool_names = {
            e["tool_name"] for e in events
            if e.get("type") == "tool_proposal"
        }
        assert "run_report_agent" in tool_names, (
            f"run_report_agent not called: {tool_names}"
        )


@skip_no_gemini
@skip_no_docker
@pytest.mark.slow
@pytest.mark.docker
@pytest.mark.usefixtures("mock_db")
class TestCodeManagerIntegration:
    """Integration test for CodeManagerAgent."""

    def test_orchestrates_code_flow(self):
        """
        CodeManagerAgent should invoke run_code_agent and produce
        an orchestrator report.
        """
        from response_planner_backend.agents.code_manager_agent.agent import (  # noqa: E501
            CodeManagerAgent,
        )
        from response_planner_backend.agents.code_manager_agent.tools import (  # noqa: E501
            STREAMING_TOOL_DISPATCH,
            TOOL_DISPATCH,
        )

        context = {
            "system_description": SYSTEM_DESC,
            "incident_report": INCIDENT_REPORT,
            "specification": SPECIFICATION,
            "operator_feedback": OPERATOR_FEEDBACK,
            "images": [],
            "code_agent_model": MODEL,
            "reviewer_agent_model": MODEL,
            "username": "test",
            "dt_config": None,
            "validation_feedback": "",
            "compaction_model": None,
            "compaction_threshold": 0.0,
        }
        agent = CodeManagerAgent()
        events, report = run_agent_loop(
            agent=agent,
            step_kwargs={
                "system_description": SYSTEM_DESC,
                "incident_report": INCIDENT_REPORT,
                "specification": SPECIFICATION,
                "operator_feedback": OPERATOR_FEEDBACK,
                "model_name": MODEL,
                "max_iterations": 1,
                "compaction_threshold": 0.0,
            },
            tool_dispatch=TOOL_DISPATCH,
            streaming_dispatch=STREAMING_TOOL_DISPATCH,
            report_event_type="orchestrator_report",
            context=context,
        )
        assert report is not None, (
            "CodeManagerAgent did not produce a report"
        )
        assert "orchestrator_report" in report


@skip_no_gemini
@skip_no_docker
@pytest.mark.slow
@pytest.mark.docker
@pytest.mark.usefixtures("mock_db")
class TestPlanManagerIntegration:
    """Integration test for PlanManagerAgent (full pipeline)."""

    def test_orchestrates_full_pipeline(self):
        """
        PlanManagerAgent should invoke code_manager, planner_agent, and
        plan_verifier_agent, then produce a plan_manager_report.
        """
        from response_planner_backend.agents.plan_manager_agent.agent import (  # noqa: E501
            PlanManagerAgent,
        )
        from response_planner_backend.agents.plan_manager_agent.tools import (  # noqa: E501
            STREAMING_TOOL_DISPATCH,
            TOOL_DISPATCH,
        )

        context = {
            "system_description": SYSTEM_DESC,
            "incident_report": INCIDENT_REPORT,
            "specification": SPECIFICATION,
            "operator_feedback": OPERATOR_FEEDBACK,
            "images": [],
            "code_manager_model": MODEL,
            "code_agent_model": MODEL,
            "reviewer_agent_model": MODEL,
            "planner_agent_model": MODEL,
            "plan_verifier_agent_model": MODEL,
            "planner_time_limit_minutes": 1,
            "username": "test",
            "dt_config": None,
            "compaction_model": None,
            "compaction_threshold": 0.0,
        }
        agent = PlanManagerAgent()
        events, report = run_agent_loop(
            agent=agent,
            step_kwargs={
                "system_description": SYSTEM_DESC,
                "incident_report": INCIDENT_REPORT,
                "specification": SPECIFICATION,
                "operator_feedback": OPERATOR_FEEDBACK,
                "model_name": MODEL,
                "max_iterations": 1,
                "compaction_threshold": 0.0,
            },
            tool_dispatch=TOOL_DISPATCH,
            streaming_dispatch=STREAMING_TOOL_DISPATCH,
            report_event_type="plan_manager_report",
            context=context,
        )
        assert report is not None, (
            "PlanManagerAgent did not produce a report"
        )
        assert "plan_manager_report" in report


# ===================================================================
# Cross-cutting tests
# ===================================================================

@skip_no_gemini
@pytest.mark.slow
class TestCrossCutting:
    """Cross-cutting integration tests."""

    def test_no_base64_images_in_context(self):
        """
        Verify that compact_tool_result strips base64 image data
        before tool results are passed to the LLM context.
        """
        from response_planner_backend.agents.context_utils import (
            compact_tool_result,
        )
        from response_planner_backend.agents.report_agent.agent import (
            ReportAgent,
        )
        from response_planner_backend.agents.report_agent.tools import (
            STREAMING_TOOL_DISPATCH,
            TOOL_DISPATCH,
        )

        agent = ReportAgent()
        step_kwargs: dict[str, Any] = {
            "system_description": SYSTEM_DESC,
            "security_alerts": SECURITY_ALERTS,
            "operator_feedback": OPERATOR_FEEDBACK,
            "model_name": MODEL,
            "compaction_threshold": 0.0,
        }
        run_agent_loop(
            agent=agent,
            step_kwargs=step_kwargs,
            tool_dispatch=TOOL_DISPATCH,
            streaming_dispatch=STREAMING_TOOL_DISPATCH,
            report_event_type="assessment",
        )
        history = step_kwargs["conversation_history"]
        for entry in history:
            if entry.get("type") != "tool_result":
                continue
            tool_name = entry.get("tool_name", "")
            result = entry.get("result", {})
            compacted = compact_tool_result(
                tool_name, result,
            )
            compacted_str = json.dumps(
                compacted, default=str,
            )
            assert "data:image/" not in compacted_str, (
                "Found base64 image in compacted "
                f"tool_result for {tool_name}"
            )

    @pytest.mark.usefixtures("mock_db")
    def test_manager_invokes_expected_subagents(self):
        """
        ReportManagerAgent should invoke run_report_agent at
        minimum when given max_iterations=1.
        """
        from response_planner_backend.agents.report_manager_agent.agent import (  # noqa: E501
            ReportManagerAgent,
        )
        from response_planner_backend.agents.report_manager_agent.tools import (  # noqa: E501
            STREAMING_TOOL_DISPATCH,
            TOOL_DISPATCH,
        )

        context = {
            "system_description": SYSTEM_DESC,
            "security_alerts": SECURITY_ALERTS,
            "operator_feedback": OPERATOR_FEEDBACK,
            "images": [],
            "report_agent_model": MODEL,
            "reviewer_agent_model": MODEL,
            "username": "test",
            "dt_config": None,
            "compaction_model": None,
            "compaction_threshold": 0.0,
        }
        agent = ReportManagerAgent()
        events, _ = run_agent_loop(
            agent=agent,
            step_kwargs={
                "system_description": SYSTEM_DESC,
                "security_alerts": SECURITY_ALERTS,
                "operator_feedback": OPERATOR_FEEDBACK,
                "model_name": MODEL,
                "max_iterations": 1,
                "compaction_threshold": 0.0,
            },
            tool_dispatch=TOOL_DISPATCH,
            streaming_dispatch=STREAMING_TOOL_DISPATCH,
            report_event_type="report_manager_report",
            context=context,
        )
        tool_names = {
            e["tool_name"] for e in events
            if e.get("type") == "tool_proposal"
        }
        assert "run_report_agent" in tool_names, (
            "run_report_agent not in tool calls: "
            f"{tool_names}"
        )
