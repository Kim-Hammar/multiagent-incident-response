"""
Pydantic models for all agent report schemas.

These models are the source of truth for report structure.
Integration tests validate that tool declarations and fallback
dicts stay consistent with these definitions.
"""
from pydantic import BaseModel


# ── Shared sub-models ──────────────────────────────────────────


class CommandEntry(BaseModel):
    """
    A shell command targeting a specific container.
    """

    container: str
    command: str


class RecoveryState(BaseModel):
    """
    Boolean flags tracking incident recovery progress.
    """

    is_attack_contained: bool
    is_attack_assessed: bool
    is_forensic_evidence_preserved: bool
    is_attack_evicted: bool
    is_system_hardened: bool
    are_services_restored: bool


class ServiceStateEntry(BaseModel):
    """
    A single service specification check result.
    """

    description: str
    passed: bool


# ── Code Agent ─────────────────────────────────────────────────


class CodeAction(BaseModel):
    """
    An action in the MDP environment.
    """

    name: str
    description: str
    state_effect: str
    success_probability: str = ""
    commands: list[CommandEntry] = []


class VerificationCheck(BaseModel):
    """
    A single gym_verify check result.
    """

    check: str
    passed: bool
    detail: str = ""


class CodeReport(BaseModel):
    """
    Report produced by the code_agent.
    """

    executive_summary: str
    generated_code: str
    actions: list[CodeAction]
    state_description: str
    verification_result: str
    verification_checks: list[VerificationCheck]


# ── Code Reviewer Agent ────────────────────────────────────────


class ReviewFinding(BaseModel):
    """
    A specific issue found during code review.
    """

    category: str
    severity: str
    description: str
    recommendation: str


class MissingAction(BaseModel):
    """
    An action the MDP should include but does not.
    """

    name: str
    description: str
    commands: list[CommandEntry] = []
    rationale: str


class CommandIssue(BaseModel):
    """
    A broken or incorrect command in ACTION_TABLE.
    """

    action_name: str
    container: str
    command: str
    issue: str
    fix: str


class ReviewReport(BaseModel):
    """
    Report produced by the code_reviewer_agent.
    """

    executive_summary: str
    findings: list[ReviewFinding]
    missing_actions: list[MissingAction]
    command_issues: list[CommandIssue]
    strengths: list[str]
    overall_verdict: str


# ── Code Manager Agent ─────────────────────────────────────────


class OrchestratorReport(BaseModel):
    """
    Report produced by the code_manager_agent.
    """

    executive_summary: str
    iterations: int
    final_verdict: str
    code_report_summary: str
    review_report_summary: str


# ── RL Agent ───────────────────────────────────────────────────


class RlActionStep(BaseModel):
    """
    A single step in the RL-derived action sequence.
    """

    step: int
    phase: str
    action: str
    description: str
    commands: list[CommandEntry] = []
    rationale: str
    spec_impact: str


class PlannerReport(BaseModel):
    """
    Report produced by the rl_agent.
    """

    executive_summary: str
    algorithm: str
    hyperparameters: str
    training_summary: str
    action_sequence: list[RlActionStep]
    expected_total_cost: float
    risks: list[str]


# ── Validation Agent ───────────────────────────────────────────


class ActionResult(BaseModel):
    """
    Result of executing a single response action on the DT.
    """

    action_name: str
    action_description: str
    commands_executed: list[str]
    outcome: str
    recovery_state: RecoveryState
    service_state: list[ServiceStateEntry]
    actual_step_cost: float


class ValidationReport(BaseModel):
    """
    Report produced by the validation_agent.
    """

    executive_summary: str
    action_results: list[ActionResult]
    final_recovery_state: RecoveryState
    final_service_state: list[ServiceStateEntry]
    overall_result: str
    recommendations: list[str]
    actual_total_cost: float
    simulated_total_cost: float


# ── Information Agent ──────────────────────────────────────────


class IOCEntry(BaseModel):
    """
    An indicator of compromise.
    """

    type: str
    value: str
    context: str


class AffectedAsset(BaseModel):
    """
    An asset affected by the incident.
    """

    asset: str
    impact: str


class InformationReport(BaseModel):
    """
    Report produced by the information_agent.
    """

    incident_summary: str
    attack_vector_analysis: str
    indicators_of_compromise: list[IOCEntry]
    severity: str
    severity_justification: str
    affected_assets: list[AffectedAsset]


# ── Plan Manager Agent ─────────────────────────────────────────


class PlanManagerReport(BaseModel):
    """
    Report produced by the plan_manager_agent.
    """

    executive_summary: str
    iterations: int
    final_verdict: str
    code_manager_summary: str
    rl_agent_summary: str
    validation_summary: str


# ── Penetration Test Agent ─────────────────────────────────────


class AttackPath(BaseModel):
    """
    An attack path discovered during penetration testing.
    """

    name: str
    description: str
    steps: list[str]
    severity: str
    compromised_assets: list[str]


class VulnerabilityEntry(BaseModel):
    """
    A vulnerability found during penetration testing.
    """

    vulnerability: str
    affected_asset: str
    severity: str
    remediation: str


class PentestReport(BaseModel):
    """
    Report produced by the penetration_test_agent.
    """

    executive_summary: str
    attack_paths: list[AttackPath]
    vulnerabilities_found: list[VulnerabilityEntry]
    compromised_servers: list[str]
    recommendations: list[str]


# ── DP Agent ───────────────────────────────────────────────────


class DpActionStep(BaseModel):
    """
    A single step in the DP-derived action sequence.
    """

    step: int
    action: str
    description: str
    commands: list[CommandEntry] = []
    expected_effect: str


class Contingency(BaseModel):
    """
    A fallback action if a primary action fails.
    """

    condition: str
    alternative_action: str
    rationale: str


class DpPlannerReport(BaseModel):
    """
    Report produced by the dp_agent.
    """

    executive_summary: str
    method: str
    parameters: str
    solving_summary: str
    action_sequence: list[DpActionStep]
    contingencies: list[Contingency]
    expected_total_cost: float
    risks: list[str]


# ── Registry ───────────────────────────────────────────────────

REPORT_MODELS: dict[str, type[BaseModel]] = {
    "code_agent": CodeReport,
    "code_reviewer_agent": ReviewReport,
    "code_manager_agent": OrchestratorReport,
    "rl_agent": PlannerReport,
    "validation_agent": ValidationReport,
    "information_agent": InformationReport,
    "plan_manager_agent": PlanManagerReport,
    "penetration_test_agent": PentestReport,
    "dp_agent": DpPlannerReport,
}
