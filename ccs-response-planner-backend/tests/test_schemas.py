"""
Integration tests for Pydantic report schemas.

Validates that Pydantic models, tool declarations, and fallback
dicts stay consistent across all 10 agents.
"""
import pytest
from pydantic import ValidationError

from ccs_response_planner_backend.agents.schemas import (
    REPORT_MODELS,
    CodeReport,
    ReviewReport,
    OrchestratorReport,
    PlannerReport,
    ValidationReport,
    InformationReport,
    PlanManagerReport,
    PentestReport,
    DpPlannerReport,
    ReportReviewReport,
    ReportManagerReport,
)

# ── Tool declaration imports ───────────────────────────────────

from ccs_response_planner_backend.agents.code_agent.tool_declarations import (
    PRODUCE_CODE_REPORT_DECL,
)
from ccs_response_planner_backend.agents.code_reviewer_agent.tool_declarations import (  # noqa: E501
    PRODUCE_REVIEW_REPORT_DECL,
)
from ccs_response_planner_backend.agents.code_manager_agent.tool_declarations import (  # noqa: E501
    PRODUCE_ORCHESTRATOR_REPORT_DECL,
)
from ccs_response_planner_backend.agents.rl_agent.tool_declarations import (
    PRODUCE_PLANNER_REPORT_DECL as RL_REPORT_DECL,
)
from ccs_response_planner_backend.agents.dp_agent.tool_declarations import (
    PRODUCE_PLANNER_REPORT_DECL as DP_REPORT_DECL,
)
from ccs_response_planner_backend.agents.validation_agent.tool_declarations import (  # noqa: E501
    PRODUCE_REPORT_DECL as VALIDATION_REPORT_DECL,
)
from ccs_response_planner_backend.agents.plan_manager_agent.tool_declarations import (  # noqa: E501
    PRODUCE_PLAN_MANAGER_REPORT_DECL,
)
from ccs_response_planner_backend.agents.report_agent.tool_declarations import (  # noqa: E501
    TOOL_DECLARATIONS as INFO_DECLARATIONS,
)
from ccs_response_planner_backend.agents.report_reviewer_agent.tool_declarations import (  # noqa: E501
    PRODUCE_REPORT_REVIEW_DECL,
)
from ccs_response_planner_backend.agents.penetration_test_agent.tool_declarations import (  # noqa: E501
    TOOL_DECLARATIONS as PENTEST_DECLARATIONS,
)
from ccs_response_planner_backend.agents.report_manager_agent.tool_declarations import (  # noqa: E501
    PRODUCE_REPORT_MANAGER_REPORT_DECL,
)


def _find_decl(declarations, name):
    """
    Find a FunctionDeclaration by name in a list.

    :param declarations: list of FunctionDeclaration objects
    :param name: the function name to find
    :return: the matching FunctionDeclaration
    """
    for d in declarations:
        if d.name == name:
            return d
    raise ValueError(f"No declaration named {name!r}")


INFO_REPORT_DECL = _find_decl(
    INFO_DECLARATIONS, "produce_assessment",
)
PENTEST_REPORT_DECL = _find_decl(
    PENTEST_DECLARATIONS, "produce_report",
)


def _get_decl_fields(decl):
    """
    Extract property names and required list from a declaration.

    :param decl: a FunctionDeclaration with a Schema parameters object
    :return: tuple of (set of property names, set of required names)
    """
    params = decl.parameters
    props = set(params.properties.keys())
    required = set(params.required or [])
    return props, required


def _get_model_fields(model_cls):
    """
    Extract field names and required fields from a Pydantic model.

    :param model_cls: a Pydantic BaseModel subclass
    :return: tuple of (set of field names, set of required field names)
    """
    all_fields = set(model_cls.model_fields.keys())
    required = set()
    for name, field_info in model_cls.model_fields.items():
        if field_info.is_required():
            required.add(name)
    return all_fields, required


# ── Map each agent to its declaration and model ────────────────

AGENT_DECL_MODEL = [
    ("code_agent", PRODUCE_CODE_REPORT_DECL, CodeReport),
    ("code_reviewer_agent", PRODUCE_REVIEW_REPORT_DECL, ReviewReport),
    ("code_manager_agent", PRODUCE_ORCHESTRATOR_REPORT_DECL, OrchestratorReport),
    ("rl_agent", RL_REPORT_DECL, PlannerReport),
    ("dp_agent", DP_REPORT_DECL, DpPlannerReport),
    ("validation_agent", VALIDATION_REPORT_DECL, ValidationReport),
    ("report_agent", INFO_REPORT_DECL, InformationReport),
    ("plan_manager_agent", PRODUCE_PLAN_MANAGER_REPORT_DECL, PlanManagerReport),
    ("penetration_test_agent", PENTEST_REPORT_DECL, PentestReport),
    ("report_reviewer_agent", PRODUCE_REPORT_REVIEW_DECL, ReportReviewReport),
    ("report_manager_agent", PRODUCE_REPORT_MANAGER_REPORT_DECL, ReportManagerReport),
]


# ── Fallback dicts (from _parse_*_report except branches) ─────

FALLBACK_DICTS = {
    "code_agent": {
        "executive_summary": "fallback",
        "generated_code": "",
        "actions": [],
        "state_description": "",
        "verification_result": "",
        "verification_checks": [],
    },
    "code_reviewer_agent": {
        "executive_summary": "fallback",
        "findings": [],
        "missing_actions": [],
        "command_issues": [],
        "strengths": [],
        "overall_verdict": "",
    },
    "code_manager_agent": {
        "executive_summary": "fallback",
        "iterations": 0,
        "final_verdict": "unknown",
        "code_report_summary": "",
        "review_report_summary": "",
    },
    "rl_agent": {
        "executive_summary": "fallback",
        "algorithm": "",
        "hyperparameters": "",
        "training_summary": "",
        "action_sequence": [],
        "expected_total_cost": 0,
        "risks": [],
    },
    "dp_agent": {
        "executive_summary": "fallback",
        "method": "",
        "parameters": "",
        "solving_summary": "",
        "action_sequence": [],
        "contingencies": [],
        "expected_total_cost": 0,
        "risks": [],
    },
    "validation_agent": {
        "executive_summary": "fallback",
        "action_results": [],
        "final_recovery_state": {
            "is_attack_contained": False,
            "is_attack_assessed": False,
            "is_forensic_evidence_preserved": False,
            "is_attack_evicted": False,
            "is_system_hardened": False,
            "are_services_restored": False,
        },
        "final_service_state": [],
        "overall_result": "Plan validation failed",
        "recommendations": [],
        "actual_total_cost": 0,
        "simulated_total_cost": 0,
    },
    "report_agent": {
        "incident_summary": "fallback",
        "attack_vector_analysis": "",
        "indicators_of_compromise": [],
        "severity": "Unknown",
        "severity_justification": "",
        "affected_assets": [],
    },
    "plan_manager_agent": {
        "executive_summary": "fallback",
        "iterations": 0,
        "final_verdict": "unknown",
        "code_manager_summary": "",
        "rl_agent_summary": "",
        "validation_summary": "",
    },
    "penetration_test_agent": {
        "executive_summary": "fallback",
        "attack_paths": [],
        "vulnerabilities_found": [],
        "compromised_servers": [],
        "recommendations": [],
    },
    "report_reviewer_agent": {
        "executive_summary": "fallback",
        "findings": [],
        "missing_elements": [],
        "evidence_gaps": [],
        "strengths": [],
        "overall_verdict": "",
    },
    "report_manager_agent": {
        "executive_summary": "fallback",
        "iterations": 0,
        "final_verdict": "unknown",
        "report_summary": "",
        "review_summary": "",
    },
}


# ═══════════════════════════════════════════════════════════════
# (a) Fallback reports validate against Pydantic models
# ═══════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "agent_type",
    list(FALLBACK_DICTS.keys()),
)
def test_fallback_validates(agent_type):
    """
    Each fallback dict must validate against its Pydantic model.
    """
    model_cls = REPORT_MODELS[agent_type]
    data = FALLBACK_DICTS[agent_type]
    report = model_cls.model_validate(data)
    assert report.model_dump() is not None


# ═══════════════════════════════════════════════════════════════
# (b) Tool declaration field consistency
# ═══════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "agent_type,decl,model_cls",
    AGENT_DECL_MODEL,
    ids=[t[0] for t in AGENT_DECL_MODEL],
)
def test_declaration_fields_match_model(agent_type, decl, model_cls):
    """
    Tool declaration properties and required list must match the
    Pydantic model's field names and required fields.
    """
    decl_props, decl_required = _get_decl_fields(decl)
    model_props, model_required = _get_model_fields(model_cls)

    assert decl_props == model_props, (
        f"{agent_type}: declaration properties {decl_props} "
        f"!= model fields {model_props}"
    )
    assert decl_required == model_required, (
        f"{agent_type}: declaration required {decl_required} "
        f"!= model required {model_required}"
    )


# ═══════════════════════════════════════════════════════════════
# (c) Representative sample reports
# ═══════════════════════════════════════════════════════════════


def test_sample_code_report():
    """
    A realistic CodeReport with actions and verification checks.
    """
    report = CodeReport.model_validate({
        "executive_summary": "Generated MDP environment for SSH brute-force.",
        "generated_code": "import gymnasium\nclass IncidentEnv: ...",
        "actions": [
            {
                "name": "block_attacker_ip",
                "description": "Block attacker IP on firewall.",
                "state_effect": "Containment achieved.",
                "success_probability": "0.95",
                "commands": [
                    {
                        "container": "i1_firewall",
                        "command": "iptables -A INPUT -s 10.0.0.5 -j DROP",
                    },
                ],
            },
            {
                "name": "restart_ssh",
                "description": "Restart SSH service.",
                "state_effect": "Service restored.",
                "commands": [
                    {
                        "container": "i1_server_1",
                        "command": "systemctl restart sshd",
                    },
                ],
            },
        ],
        "state_description": "6 recovery bools + 4 service specs.",
        "verification_result": "All 9 checks passed",
        "verification_checks": [
            {"check": "find_env_class", "passed": True},
            {"check": "has_reset", "passed": True, "detail": "OK"},
            {"check": "has_step", "passed": False, "detail": "Missing"},
        ],
    })
    assert len(report.actions) == 2
    assert report.actions[0].commands[0].container == "i1_firewall"
    assert report.verification_checks[2].passed is False


def test_sample_validation_report():
    """
    A realistic ValidationReport with action results and recovery state.
    """
    report = ValidationReport.model_validate({
        "executive_summary": "Plan partially validated.",
        "action_results": [
            {
                "action_name": "block_ip",
                "action_description": "Block attacker.",
                "commands_executed": ["iptables -A INPUT -s 10.0.0.5 -j DROP"],
                "outcome": "Success",
                "recovery_state": {
                    "is_attack_contained": True,
                    "is_attack_assessed": False,
                    "is_forensic_evidence_preserved": False,
                    "is_attack_evicted": False,
                    "is_system_hardened": False,
                    "are_services_restored": False,
                },
                "service_state": [
                    {"description": "HTTP reachable", "passed": True},
                ],
                "actual_step_cost": 1.0,
            },
        ],
        "final_recovery_state": {
            "is_attack_contained": True,
            "is_attack_assessed": False,
            "is_forensic_evidence_preserved": False,
            "is_attack_evicted": False,
            "is_system_hardened": False,
            "are_services_restored": False,
        },
        "final_service_state": [
            {"description": "HTTP reachable", "passed": True},
        ],
        "overall_result": "Plan partially validated",
        "recommendations": ["Add forensic evidence collection step."],
        "actual_total_cost": 1.0,
        "simulated_total_cost": 3.5,
    })
    assert report.final_recovery_state.is_attack_contained is True
    assert len(report.action_results) == 1
    assert report.action_results[0].actual_step_cost == 1.0


def test_sample_planner_report():
    """
    A realistic PlannerReport with an action sequence.
    """
    report = PlannerReport.model_validate({
        "executive_summary": "RL-derived plan for SSH brute-force.",
        "algorithm": "PPO",
        "hyperparameters": "lr=3e-4, gamma=0.99, epochs=10",
        "training_summary": "500 episodes, final reward=-2.3",
        "action_sequence": [
            {
                "step": 1,
                "phase": "containment",
                "action": "block_attacker_ip",
                "description": "Block attacker IP on firewall.",
                "commands": [
                    {
                        "container": "i1_firewall",
                        "command": "iptables -A INPUT -s 10.0.0.5 -j DROP",
                    },
                ],
                "rationale": "Immediate containment to stop ongoing attack.",
                "spec_impact": "No service impact.",
            },
        ],
        "expected_total_cost": 2.3,
        "risks": ["Attacker may pivot before containment."],
    })
    assert report.action_sequence[0].phase == "containment"
    assert report.expected_total_cost == 2.3


def test_sample_information_report():
    """
    A realistic InformationReport with IOCs.
    """
    report = InformationReport.model_validate({
        "incident_summary": "SSH brute-force from external IP.",
        "attack_vector_analysis": "Dictionary attack on port 22.",
        "indicators_of_compromise": [
            {
                "type": "ip",
                "value": "203.0.113.42",
                "context": "Source of brute-force attempts.",
            },
            {
                "type": "cve",
                "value": "CVE-2021-44228",
                "context": "Log4Shell used for initial access.",
            },
        ],
        "severity": "High",
        "severity_justification": "Active exploitation with lateral movement.",
        "affected_assets": [
            {"asset": "i1_server_1", "impact": "Compromised root."},
        ],
    })
    assert len(report.indicators_of_compromise) == 2
    assert report.severity == "High"


# ═══════════════════════════════════════════════════════════════
# (d) Edge cases
# ═══════════════════════════════════════════════════════════════


def test_empty_arrays_validate():
    """
    Reports with all-empty arrays should validate.
    """
    report = PentestReport.model_validate({
        "executive_summary": "No vulnerabilities found.",
        "attack_paths": [],
        "vulnerabilities_found": [],
        "compromised_servers": [],
        "recommendations": [],
    })
    assert report.attack_paths == []


def test_verification_check_detail_defaults_empty():
    """
    VerificationCheck.detail defaults to empty string.
    """
    from ccs_response_planner_backend.agents.schemas import VerificationCheck
    check = VerificationCheck(check="test", passed=True)
    assert check.detail == ""


def test_wrong_type_raises_validation_error():
    """
    Passing a string for an integer field raises ValidationError.
    """
    with pytest.raises(ValidationError):
        OrchestratorReport.model_validate({
            "executive_summary": "test",
            "iterations": "not_an_int",
            "final_verdict": "pass",
            "code_report_summary": "",
            "review_report_summary": "",
        })


def test_missing_required_field_raises():
    """
    Omitting a required field raises ValidationError.
    """
    with pytest.raises(ValidationError):
        PlannerReport.model_validate({
            "executive_summary": "test",
            # missing algorithm, hyperparameters, etc.
        })


def test_registry_contains_all_eleven_agents():
    """
    REPORT_MODELS registry has exactly 11 entries.
    """
    assert len(REPORT_MODELS) == 11
    expected = {
        "code_agent", "code_reviewer_agent", "code_manager_agent",
        "rl_agent", "validation_agent", "report_agent",
        "plan_manager_agent", "penetration_test_agent", "dp_agent",
        "report_reviewer_agent", "report_manager_agent",
    }
    assert set(REPORT_MODELS.keys()) == expected
