/**
 * Shared report body components for rendering sub-agent results
 * (code reports, review reports) in both the CodeManagerAgent and
 * nested SubAgentLog contexts.
 */

import ReactMarkdown from 'react-markdown'

const CHECK_LABELS = {
  find_env_class: 'Env class found',
  has_get_actions: 'get_actions()',
  has_step: 'step()',
  has_reset: 'reset()',
  has_set_state: 'set_state()',
  reset_state_shape: 'State shape valid',
  get_actions_nonempty: 'Actions non-empty',
  step_returns_tuple5: 'step() returns 5-tuple',
  set_state_works: 'set_state() works'
}

const VERDICT_STYLES = {
  pass: 'success',
  needs_revision: 'warning',
  major_issues: 'danger'
}

const SEVERITY_STYLES = {
  critical: 'danger',
  major: 'warning',
  minor: 'info',
  info: 'secondary'
}

/**
 * Inline code report body (no card wrapper) for tool_result rendering.
 */
function CodeReportBody({ report: r }) {
  const checks = r.verification_checks || []
  return (
    <div style={{ marginTop: '10px' }}>
      {(checks.length > 0 || r.verification_result) && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Verification</div>
          {checks.length > 0 ? (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
              {checks.map((c, i) => (
                <span
                  key={i}
                  className={`badge badge-${c.passed ? 'success' : 'danger'}`}
                  style={{ fontSize: '12px', padding: '5px 8px' }}
                  title={c.detail || ''}
                >
                  <i
                    className={`fa fa-${c.passed ? 'check' : 'times'}`}
                    aria-hidden="true"
                    style={{ marginRight: '4px' }}
                  />
                  {CHECK_LABELS[c.check] || c.check}
                </span>
              ))}
            </div>
          ) : (
            <span
              className={`badge badge-${r.verification_result?.toLowerCase().includes('pass') ? 'success' : 'warning'}`}
              style={{ fontSize: '12px', padding: '5px 8px' }}
            >
              {r.verification_result}
            </span>
          )}
        </div>
      )}
      {r.executive_summary && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Code Agent Summary</div>
          <p className="ia-assessment-body mb-0">{r.executive_summary}</p>
        </div>
      )}
      {r.state_description && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">State Description</div>
          <p className="ia-assessment-body mb-0">{r.state_description}</p>
        </div>
      )}
      {r.actions && r.actions.length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Actions</div>
          <div style={{ overflowX: 'auto' }}>
            <table className="ia-ioc-table" style={{ minWidth: '600px' }}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Description</th>
                  <th>Commands</th>
                  <th>State Effect</th>
                  <th>P(success)</th>
                </tr>
              </thead>
              <tbody>
                {r.actions.map((a, i) => (
                  <tr key={i}>
                    <td>
                      <strong>{a.name}</strong>
                    </td>
                    <td>{a.description}</td>
                    <td>
                      {a.commands && a.commands.length > 0 ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          {a.commands.map((c, j) => (
                            <code
                              key={j}
                              style={{
                                fontSize: '11px',
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-word'
                              }}
                            >
                              {c.container}: {c.command}
                            </code>
                          ))}
                        </div>
                      ) : (
                        <span style={{ color: '#999' }}>-</span>
                      )}
                    </td>
                    <td>
                      <code style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                        {a.state_effect}
                      </code>
                    </td>
                    <td>{a.success_probability || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {r.generated_code && (
        <div className="ia-assessment-section">
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}
          >
            <div className="ia-assessment-label" style={{ marginBottom: 0 }}>
              Generated Code
            </div>
            <button
              type="button"
              className="btn btn-outline-dark btn-sm"
              style={{ fontSize: '11px', padding: '2px 10px' }}
              onClick={() => {
                const blob = new Blob([r.generated_code], { type: 'text/x-python' })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = 'mdp_environment.py'
                a.click()
                URL.revokeObjectURL(url)
              }}
            >
              <i className="fa fa-download" aria-hidden="true" /> Download .py
            </button>
          </div>
          <pre
            style={{
              background: '#f5f5f5',
              padding: '12px',
              borderRadius: '4px',
              fontSize: '12px',
              maxHeight: '500px',
              overflow: 'auto',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word'
            }}
          >
            {r.generated_code}
          </pre>
        </div>
      )}
    </div>
  )
}

/**
 * Inline review report body (no card wrapper) for tool_result rendering.
 */
function ReviewReportBody({ report: r }) {
  const findings = r.findings || []
  const missingActions = r.missing_actions || []
  const commandIssues = r.command_issues || []
  const strengths = r.strengths || []
  return (
    <div style={{ marginTop: '10px' }}>
      {r.overall_verdict && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Overall Verdict</div>
          <span
            className={`badge badge-${VERDICT_STYLES[r.overall_verdict] || 'secondary'}`}
            style={{ fontSize: '14px', padding: '6px 12px' }}
          >
            {r.overall_verdict.replace(/_/g, ' ')}
          </span>
        </div>
      )}
      {r.executive_summary && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Executive Summary</div>
          <p className="ia-assessment-body mb-0">{r.executive_summary}</p>
        </div>
      )}
      {findings.length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Findings</div>
          <table className="ia-ioc-table">
            <thead>
              <tr>
                <th>Category</th>
                <th>Severity</th>
                <th>Description</th>
                <th>Recommendation</th>
              </tr>
            </thead>
            <tbody>
              {findings.map((f, i) => (
                <tr key={i}>
                  <td>{f.category}</td>
                  <td>
                    <span className={`badge badge-${SEVERITY_STYLES[f.severity] || 'secondary'}`}>
                      {f.severity}
                    </span>
                  </td>
                  <td>{f.description}</td>
                  <td>{f.recommendation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {missingActions.length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Missing Actions</div>
          <table className="ia-ioc-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Description</th>
                <th>Commands</th>
                <th>Rationale</th>
              </tr>
            </thead>
            <tbody>
              {missingActions.map((a, i) => (
                <tr key={i}>
                  <td>
                    <strong>{a.name}</strong>
                  </td>
                  <td>{a.description}</td>
                  <td>
                    {a.commands && a.commands.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        {a.commands.map((c, j) => (
                          <code key={j} style={{ fontSize: '11px', whiteSpace: 'nowrap' }}>
                            {c.container}: {c.command}
                          </code>
                        ))}
                      </div>
                    ) : (
                      <span style={{ color: '#999' }}>-</span>
                    )}
                  </td>
                  <td>{a.rationale}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {commandIssues.length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Command Issues</div>
          <table className="ia-ioc-table">
            <thead>
              <tr>
                <th>Action</th>
                <th>Container</th>
                <th>Command</th>
                <th>Issue</th>
                <th>Fix</th>
              </tr>
            </thead>
            <tbody>
              {commandIssues.map((c, i) => (
                <tr key={i}>
                  <td>{c.action_name}</td>
                  <td>{c.container}</td>
                  <td>
                    <code style={{ fontSize: '11px' }}>{c.command}</code>
                  </td>
                  <td>{c.issue}</td>
                  <td>
                    <code style={{ fontSize: '11px' }}>{c.fix}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {strengths.length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Strengths</div>
          <ul style={{ marginBottom: 0 }}>
            {strengths.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

/* ── Incident assessment body (from ReportAgent results) ─────── */

const ASSESSMENT_SEVERITY_MAP = {
  Critical: 'danger',
  High: 'warning',
  Medium: 'info',
  Low: 'success'
}

function AssessmentBody({ report: a }) {
  return (
    <div style={{ marginTop: '10px' }}>
      {a.incident_summary && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Incident Summary</div>
          <p className="ia-assessment-body mb-0">{a.incident_summary}</p>
        </div>
      )}
      {a.attack_vector_analysis && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Attack Vector Analysis</div>
          <p className="ia-assessment-body mb-0">{a.attack_vector_analysis}</p>
        </div>
      )}
      {a.severity && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Severity</div>
          <span className={`badge badge-${ASSESSMENT_SEVERITY_MAP[a.severity] || 'secondary'}`}>
            {a.severity}
          </span>
          {a.severity_justification && (
            <p className="ia-assessment-body mb-0 mt-1">{a.severity_justification}</p>
          )}
        </div>
      )}
      {a.indicators_of_compromise && a.indicators_of_compromise.length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Indicators of Compromise</div>
          <table className="ia-ioc-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Value</th>
                <th>Context</th>
              </tr>
            </thead>
            <tbody>
              {a.indicators_of_compromise.map((ioc, i) => (
                <tr key={i}>
                  <td>{ioc.type}</td>
                  <td>{ioc.value}</td>
                  <td>{ioc.context}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {a.affected_assets && a.affected_assets.length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Affected Assets</div>
          <table className="ia-asset-table">
            <thead>
              <tr>
                <th>Asset</th>
                <th>Impact</th>
              </tr>
            </thead>
            <tbody>
              {a.affected_assets.map((asset, i) => (
                <tr key={i}>
                  <td>{asset.asset}</td>
                  <td>{asset.impact}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {a.attack_path_image && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Attack Path Diagram</div>
          <img
            src={a.attack_path_image}
            alt="Attack path diagram"
            style={{
              maxWidth: '100%',
              border: '1px solid #dee2e6',
              borderRadius: '4px'
            }}
          />
        </div>
      )}
    </div>
  )
}

/* ── Incident review body (from ReportReviewerAgent results) ── */

/**
 * Strip trailing JSON structure that sometimes leaks into LLM field values
 * via function calling (e.g. "None. Validated.}],executive_summary:").
 */
function cleanField(val) {
  if (typeof val !== 'string') return val == null ? '' : String(val)
  return val.replace(/}\][,\s]*[a-z_]\w*\s*:[\s\S]*$/i, '').trim() || val
}

function IncidentReviewBody({ report: r }) {
  const findings = r.findings || []
  const missingElements = r.missing_elements || []
  const evidenceGaps = r.evidence_gaps || []
  const strengths = r.strengths || []
  return (
    <div style={{ marginTop: '10px' }}>
      {r.overall_verdict && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Overall Verdict</div>
          <span
            className={`badge badge-${VERDICT_STYLES[r.overall_verdict] || 'secondary'}`}
            style={{ fontSize: '14px', padding: '6px 12px' }}
          >
            {r.overall_verdict.replace(/_/g, ' ')}
          </span>
        </div>
      )}
      {r.executive_summary && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Executive Summary</div>
          <p className="ia-assessment-body mb-0">{r.executive_summary}</p>
        </div>
      )}
      {findings.length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Findings</div>
          <table className="ia-ioc-table">
            <thead>
              <tr>
                <th>Category</th>
                <th>Severity</th>
                <th>Description</th>
                <th>Recommendation</th>
              </tr>
            </thead>
            <tbody>
              {findings.map((f, i) => (
                <tr key={i}>
                  <td>{cleanField(f.category)}</td>
                  <td>
                    <span className={`badge badge-${SEVERITY_STYLES[f.severity] || 'secondary'}`}>
                      {f.severity}
                    </span>
                  </td>
                  <td>{cleanField(f.description)}</td>
                  <td>{cleanField(f.recommendation)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {missingElements.length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Missing Elements</div>
          <table className="ia-ioc-table">
            <thead>
              <tr>
                <th>Element</th>
                <th>Description</th>
                <th>Importance</th>
                <th>Recommendation</th>
              </tr>
            </thead>
            <tbody>
              {missingElements.map((m, i) => (
                <tr key={i}>
                  <td>
                    <strong>{cleanField(m.element)}</strong>
                  </td>
                  <td>{cleanField(m.description)}</td>
                  <td>{cleanField(m.importance)}</td>
                  <td>{cleanField(m.recommendation)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {evidenceGaps.length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Evidence Gaps</div>
          <table className="ia-ioc-table">
            <thead>
              <tr>
                <th>Claim</th>
                <th>Section</th>
                <th>Issue</th>
                <th>Suggestion</th>
              </tr>
            </thead>
            <tbody>
              {evidenceGaps.map((g, i) => (
                <tr key={i}>
                  <td>{cleanField(g.claim)}</td>
                  <td>{cleanField(g.section)}</td>
                  <td>{cleanField(g.issue)}</td>
                  <td>{cleanField(g.suggestion)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {strengths.length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Strengths</div>
          <ul style={{ marginBottom: 0 }}>
            {strengths.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

/* ── Validation report body (from ValidationAgent results) ──── */

const RECOVERY_LABELS = {
  is_attack_contained: 'Contained',
  is_attack_assessed: 'Assessed',
  is_forensic_evidence_preserved: 'Evidence Preserved',
  is_attack_evicted: 'Evicted',
  is_system_hardened: 'Hardened',
  are_services_restored: 'Restored'
}

const VALIDATION_VERDICT_MAP = {
  'Plan fully validated': 'success',
  'Plan partially validated': 'warning',
  'Plan validation failed': 'danger'
}

function RecoveryStateBadges({ state }) {
  if (!state || typeof state !== 'object') return null
  const entries = Object.entries(RECOVERY_LABELS)
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
      {entries.map(([key, label]) => {
        const val = state[key]
        if (val === undefined) return null
        return (
          <span
            key={key}
            className={`badge badge-${val ? 'success' : 'danger'}`}
            style={{ fontSize: '11px', padding: '4px 8px' }}
          >
            <i
              className={`fa fa-${val ? 'check' : 'times'}`}
              aria-hidden="true"
              style={{ marginRight: '4px' }}
            />
            {label}
          </span>
        )
      })}
    </div>
  )
}

function ServiceStateBadges({ services }) {
  if (!services || services.length === 0) return null
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
      {services.map((s, i) => (
        <span
          key={i}
          className={`badge badge-${s.passed ? 'success' : 'danger'}`}
          style={{ fontSize: '11px', padding: '4px 8px' }}
        >
          <i
            className={`fa fa-${s.passed ? 'check' : 'times'}`}
            aria-hidden="true"
            style={{ marginRight: '4px' }}
          />
          {s.description}
        </span>
      ))}
    </div>
  )
}

function ValidationReportBody({ report: r }) {
  const actionResults = r.action_results || []
  const recommendations = r.recommendations || []
  const overallResult = r.overall_result || r.overall_verdict || ''
  const verdictStyle =
    VALIDATION_VERDICT_MAP[overallResult] || VERDICT_STYLES[overallResult] || 'secondary'
  return (
    <div style={{ marginTop: '10px' }}>
      {overallResult && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Overall Result</div>
          <span
            className={`badge badge-${verdictStyle}`}
            style={{ fontSize: '14px', padding: '6px 12px' }}
          >
            {overallResult.replace(/_/g, ' ')}
          </span>
        </div>
      )}
      {r.executive_summary && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Executive Summary</div>
          <p className="ia-assessment-body mb-0">{r.executive_summary}</p>
        </div>
      )}
      {(r.actual_total_cost != null || r.simulated_total_cost != null) && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Cost Comparison</div>
          <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
            {r.actual_total_cost != null && (
              <div>
                <strong>Actual:</strong> {r.actual_total_cost}
              </div>
            )}
            {r.simulated_total_cost != null && (
              <div>
                <strong>Simulated:</strong> {r.simulated_total_cost}
              </div>
            )}
          </div>
        </div>
      )}
      {r.final_recovery_state && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Final Recovery State</div>
          <RecoveryStateBadges state={r.final_recovery_state} />
        </div>
      )}
      {r.final_service_state && r.final_service_state.length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Final Service State</div>
          <ServiceStateBadges services={r.final_service_state} />
        </div>
      )}
      {actionResults.length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Action Results ({actionResults.length})</div>
          <div style={{ overflowX: 'auto' }}>
            <table className="ia-ioc-table" style={{ minWidth: '700px' }}>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Action</th>
                  <th>Outcome</th>
                  <th>Recovery</th>
                  <th>Services</th>
                  <th>Cost</th>
                </tr>
              </thead>
              <tbody>
                {actionResults.map((a, i) => (
                  <tr key={i}>
                    <td>{i + 1}</td>
                    <td>
                      <strong>{a.action_name}</strong>
                      {a.action_description && (
                        <div style={{ fontSize: '11px', color: '#666' }}>
                          {a.action_description}
                        </div>
                      )}
                      {a.commands_executed && a.commands_executed.length > 0 && (
                        <div style={{ marginTop: '4px' }}>
                          {a.commands_executed.map((cmd, j) => (
                            <code
                              key={j}
                              style={{
                                fontSize: '10px',
                                display: 'block',
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-word'
                              }}
                            >
                              {cmd}
                            </code>
                          ))}
                        </div>
                      )}
                    </td>
                    <td>
                      <span
                        className={`badge badge-${a.success === false || (a.outcome && a.outcome.toLowerCase().includes('fail')) ? 'danger' : 'success'}`}
                        style={{ fontSize: '11px' }}
                      >
                        {a.outcome || '-'}
                      </span>
                    </td>
                    <td>
                      <RecoveryStateBadges state={a.recovery_state} />
                    </td>
                    <td>
                      <ServiceStateBadges services={a.service_state} />
                    </td>
                    <td>{a.actual_step_cost != null ? a.actual_step_cost : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {recommendations.length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Recommendations</div>
          <ul style={{ marginBottom: 0 }}>
            {recommendations.map((rec, i) => (
              <li key={i}>{rec}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

/* ── Plan Manager report body (from run_plan_manager result) ─── */

function PlanManagerReportBody({ result: r }) {
  const report = r.plan_manager_report || {}
  return (
    <div style={{ marginTop: '10px' }}>
      {report.executive_summary && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">
            Plan Manager Summary
            {report.iterations != null && (
              <span
                className="badge badge-info ml-2"
                style={{ fontSize: '11px', padding: '4px 8px', verticalAlign: 'middle' }}
              >
                {report.iterations} iteration(s)
              </span>
            )}
          </div>
          <div className="ia-assessment-body mb-0">
            <ReactMarkdown>{report.executive_summary}</ReactMarkdown>
          </div>
        </div>
      )}
      {r.code_report && Object.keys(r.code_report).length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">MDP Code Report</div>
          <CodeReportBody report={r.code_report} />
        </div>
      )}
      {r.planner_report && Object.keys(r.planner_report).length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Planner Agent Report</div>
          <PlannerReportInline report={r.planner_report} />
        </div>
      )}
      {r.validation_report && Object.keys(r.validation_report).length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Validation Report</div>
          <ValidationReportBody report={r.validation_report} />
        </div>
      )}
      {r.response_plan && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Response Plan</div>
          <pre
            style={{
              background: '#f5f5f5',
              padding: '12px',
              borderRadius: '4px',
              fontSize: '12px',
              maxHeight: '400px',
              overflow: 'auto',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word'
            }}
          >
            {r.response_plan}
          </pre>
        </div>
      )}
    </div>
  )
}

function PlannerReportInline({ report: r }) {
  const actions = r.action_sequence || []
  const risks = r.risks || []
  return (
    <div style={{ marginTop: '6px' }}>
      {r.executive_summary && (
        <div className="ia-assessment-section">
          <p className="ia-assessment-body mb-0">{r.executive_summary}</p>
        </div>
      )}
      {(r.algorithm || r.hyperparameters) && (
        <div className="ia-assessment-section">
          {r.algorithm && (
            <p className="ia-assessment-body mb-1">
              <strong>Algorithm:</strong> {r.algorithm}
            </p>
          )}
          {r.hyperparameters && (
            <p className="ia-assessment-body mb-0">
              <strong>Hyperparameters:</strong> {r.hyperparameters}
            </p>
          )}
        </div>
      )}
      {r.training_summary && (
        <div className="ia-assessment-section">
          <p className="ia-assessment-body mb-0">{r.training_summary}</p>
        </div>
      )}
      {actions.length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Action Sequence</div>
          <div style={{ overflowX: 'auto' }}>
            <table
              className="ia-ioc-table"
              style={{ tableLayout: 'fixed', width: '100%', minWidth: '700px' }}
            >
              <thead>
                <tr>
                  <th style={{ width: '4%' }}>Step</th>
                  <th style={{ width: '10%' }}>Phase</th>
                  <th style={{ width: '12%' }}>Action</th>
                  <th style={{ width: '30%' }}>Commands</th>
                  <th style={{ width: '22%' }}>Rationale</th>
                  <th style={{ width: '22%' }}>Spec Impact</th>
                </tr>
              </thead>
              <tbody>
                {actions.map((a, i) => (
                  <tr key={i}>
                    <td>{a.step}</td>
                    <td style={{ overflowWrap: 'break-word' }}>
                      <span
                        className="badge badge-secondary"
                        style={{ whiteSpace: 'normal', wordBreak: 'break-word' }}
                      >
                        {a.phase || '-'}
                      </span>
                    </td>
                    <td>
                      <strong>{a.action}</strong>
                      {a.description && (
                        <div style={{ fontSize: '11px', color: '#666', marginTop: '2px' }}>
                          {a.description}
                        </div>
                      )}
                    </td>
                    <td>
                      {a.commands && a.commands.length > 0 ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          {a.commands.map((c, j) => (
                            <code
                              key={j}
                              style={{
                                fontSize: '11px',
                                wordBreak: 'break-all',
                                whiteSpace: 'pre-wrap'
                              }}
                            >
                              {c.container}: {c.command}
                            </code>
                          ))}
                        </div>
                      ) : (
                        <span style={{ color: '#999' }}>-</span>
                      )}
                    </td>
                    <td style={{ fontSize: '12px' }}>{a.rationale || a.expected_effect || '-'}</td>
                    <td style={{ fontSize: '12px' }}>{a.spec_impact || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {r.expected_total_cost !== undefined && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Expected Total Cost</div>
          <span className="badge badge-dark" style={{ fontSize: '14px', padding: '6px 12px' }}>
            {r.expected_total_cost}
          </span>
        </div>
      )}
      {risks.length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Risks &amp; Limitations</div>
          <ul style={{ marginBottom: 0 }}>
            {risks.map((risk, i) => (
              <li key={i}>{risk}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

/* ── Host analysis body (from HostAnalyzerAgent results) ────── */

const HOST_STATUS_STYLES = {
  'Confirmed Compromised': 'danger',
  'Likely Compromised': 'warning',
  'Possibly Compromised': 'info',
  'No Evidence of Compromise': 'success'
}

function HostAnalysisBody({ report: a }) {
  const attackVectors = a.attack_vectors || []
  const iocs = a.indicators_of_compromise || []
  const services = a.affected_services || []
  const recommendations = a.recommendations || []
  return (
    <div style={{ marginTop: '10px' }}>
      {a.compromise_status && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Compromise Status</div>
          <span
            className={`badge badge-${HOST_STATUS_STYLES[a.compromise_status] || 'secondary'}`}
            style={{ fontSize: '14px', padding: '6px 12px' }}
          >
            {a.compromise_status}
          </span>
        </div>
      )}
      {a.executive_summary && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Executive Summary</div>
          <p className="ia-assessment-body mb-0">{a.executive_summary}</p>
        </div>
      )}
      {a.compromise_details && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Compromise Details</div>
          <p className="ia-assessment-body mb-0">{a.compromise_details}</p>
        </div>
      )}
      {a.security_posture && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Security Posture</div>
          <p className="ia-assessment-body mb-0">{a.security_posture}</p>
        </div>
      )}
      {attackVectors.length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Attack Vectors</div>
          <table className="ia-ioc-table">
            <thead>
              <tr>
                <th>Vector</th>
                <th>Description</th>
                <th>Evidence</th>
              </tr>
            </thead>
            <tbody>
              {attackVectors.map((v, i) => (
                <tr key={i}>
                  <td>{v.vector}</td>
                  <td>{v.description}</td>
                  <td>{v.evidence}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {iocs.length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Indicators of Compromise</div>
          <table className="ia-ioc-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Value</th>
                <th>Context</th>
              </tr>
            </thead>
            <tbody>
              {iocs.map((ioc, i) => (
                <tr key={i}>
                  <td>{ioc.type}</td>
                  <td>{ioc.value}</td>
                  <td>{ioc.context}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {services.length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Affected Services</div>
          <table className="ia-asset-table">
            <thead>
              <tr>
                <th>Service</th>
                <th>Status</th>
                <th>Impact</th>
              </tr>
            </thead>
            <tbody>
              {services.map((svc, i) => (
                <tr key={i}>
                  <td>{svc.service}</td>
                  <td>{svc.status}</td>
                  <td>{svc.impact}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {recommendations.length > 0 && (
        <div className="ia-assessment-section">
          <div className="ia-assessment-label">Recommendations</div>
          <ol className="ia-assessment-body mb-0">
            {recommendations.map((rec, i) => (
              <li key={i}>{rec}</li>
            ))}
          </ol>
        </div>
      )}
    </div>
  )
}

export {
  CodeReportBody,
  ReviewReportBody,
  AssessmentBody,
  IncidentReviewBody,
  ValidationReportBody,
  PlanManagerReportBody,
  PlannerReportInline,
  HostAnalysisBody,
  VERDICT_STYLES,
  SEVERITY_STYLES
}
