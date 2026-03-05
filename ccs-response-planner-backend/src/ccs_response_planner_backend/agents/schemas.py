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


# ── Code Verifier Agent ────────────────────────────────────────


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
    Report produced by the code_verifier_agent.
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


# ── Planner Agent ─────────────────────────────────────────────


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
    Report produced by the planner_agent.
    """

    executive_summary: str
    algorithm: str
    hyperparameters: str
    training_summary: str
    action_sequence: list[RlActionStep]
    expected_total_cost: float
    risks: list[str]


# ── Plan Verifier Agent ────────────────────────────────────────


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


class PlanVerifierReport(BaseModel):
    """
    Report produced by the plan_verifier_agent.
    """

    executive_summary: str
    action_results: list[ActionResult]
    final_recovery_state: RecoveryState
    final_service_state: list[ServiceStateEntry]
    overall_result: str
    recommendations: list[str]
    actual_total_cost: float
    simulated_total_cost: float


# ── Report Agent ──────────────────────────────────────────────


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
    Report produced by the report_agent.
    """

    incident_summary: str
    attack_vector_analysis: str
    indicators_of_compromise: list[IOCEntry]
    severity: str
    severity_justification: str
    affected_assets: list[AffectedAsset]


# ── Report Verifier Agent ─────────────────────────────────────


class ReportVerificationFinding(BaseModel):
    """
    A specific issue found during report verification.
    """

    category: str
    severity: str
    description: str
    recommendation: str


class MissingElement(BaseModel):
    """
    An element missing from the incident report.
    """

    element: str
    description: str
    importance: str
    recommendation: str


class EvidenceGap(BaseModel):
    """
    A claim in the report that lacks sufficient evidence.
    """

    claim: str
    section: str
    issue: str
    suggestion: str


class ReportVerificationReport(BaseModel):
    """
    Report produced by the report_verifier_agent.
    """

    executive_summary: str
    findings: list[ReportVerificationFinding]
    missing_elements: list[MissingElement]
    evidence_gaps: list[EvidenceGap]
    strengths: list[str]
    overall_verdict: str


# ── Report Manager Agent ──────────────────────────────────────


class ReportManagerReport(BaseModel):
    """
    Report produced by the report_manager_agent.
    """

    executive_summary: str
    iterations: int
    final_verdict: str
    report_summary: str
    review_summary: str


# ── Plan Manager Agent ─────────────────────────────────────────


class PlanManagerReport(BaseModel):
    """
    Report produced by the plan_manager_agent.
    """

    executive_summary: str
    iterations: int
    final_verdict: str
    code_manager_summary: str
    planner_agent_summary: str
    verification_summary: str


# ── Orchestrator Agent ────────────────────────────────────────


class OrchestratorAgentReport(BaseModel):
    """
    Report produced by the orchestrator_agent.
    """

    executive_summary: str
    iterations: int
    final_verdict: str
    assessment_summary: str
    response_plan_summary: str


# ── Pentest Agent ─────────────────────────────────────────────


class PentestStepResult(BaseModel):
    """
    Result of executing a single attack path step on the DT.
    """

    step_name: str
    step_description: str
    target_host: str
    commands_executed: list[str]
    command_outputs: list[str]
    success: bool
    evidence: str
    notes: str = ""


class PentestReport(BaseModel):
    """
    Report produced by the pentest_agent.
    """

    executive_summary: str
    attack_path_steps: list[PentestStepResult]
    overall_verdict: str
    hosts_compromised: list[str]
    reproduction_commands: list[str]
    defensive_recommendations: list[str]


# ── Host Analyzer Agent ──────────────────────────────────────


class HostAttackVector(BaseModel):
    """
    An attack vector identified on a host.
    """

    vector: str
    description: str
    evidence: str


class HostIOCEntry(BaseModel):
    """
    An indicator of compromise found on a host.
    """

    type: str
    value: str
    context: str


class HostServiceEntry(BaseModel):
    """
    A service affected on the analyzed host.
    """

    service: str
    status: str
    impact: str


class HostAnalysisReport(BaseModel):
    """
    Report produced by the host_analyzer_agent.
    """

    host_name: str
    compromise_status: str
    compromise_details: str
    attack_vectors: list[HostAttackVector]
    security_posture: str
    indicators_of_compromise: list[HostIOCEntry]
    affected_services: list[HostServiceEntry]
    recommendations: list[str]
    executive_summary: str


# ── Action Verifier Agent ───────────────────────────────────


class CommandResult(BaseModel):
    """
    Result of executing a single command on a container.
    """

    command: str
    container: str
    exit_code: int
    output: str


class ActionVerificationReport(BaseModel):
    """
    Report produced by the action_verifier_agent.
    """

    action_name: str
    action_description: str
    commands_executed: list[str]
    command_results: list[CommandResult]
    outcome: str
    recovery_state_before: RecoveryState
    recovery_state_after: RecoveryState
    service_state: list[ServiceStateEntry]
    step_cost: float
    executive_summary: str
    recommendations: list[str]


# ── Registry ───────────────────────────────────────────────────

REPORT_MODELS: dict[str, type[BaseModel]] = {
    "code_agent": CodeReport,
    "code_verifier_agent": ReviewReport,
    "code_manager_agent": OrchestratorReport,
    "planner_agent": PlannerReport,
    "plan_verifier_agent": PlanVerifierReport,
    "report_agent": InformationReport,
    "plan_manager_agent": PlanManagerReport,
    "report_verifier_agent": ReportVerificationReport,
    "report_manager_agent": ReportManagerReport,
    "orchestrator_agent": OrchestratorAgentReport,
    "pentest_agent": PentestReport,
    "host_analyzer_agent": HostAnalysisReport,
    "action_verifier_agent": ActionVerificationReport,
}
