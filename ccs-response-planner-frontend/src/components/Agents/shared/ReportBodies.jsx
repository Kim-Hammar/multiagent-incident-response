/**
 * Shared report body components for rendering sub-agent results
 * (code reports, review reports) in both the CodeManagerAgent and
 * nested SubAgentLog contexts.
 */

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
          <div className="ia-assessment-label">Executive Summary</div>
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
          <table className="ia-ioc-table">
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
                          <code key={j} style={{ fontSize: '11px', whiteSpace: 'nowrap' }}>
                            {c.container}: {c.command}
                          </code>
                        ))}
                      </div>
                    ) : (
                      <span style={{ color: '#999' }}>-</span>
                    )}
                  </td>
                  <td>
                    <code>{a.state_effect}</code>
                  </td>
                  <td>{a.success_probability || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
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
                    <strong>{m.element}</strong>
                  </td>
                  <td>{m.description}</td>
                  <td>{m.importance}</td>
                  <td>{m.recommendation}</td>
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
                  <td>{g.claim}</td>
                  <td>{g.section}</td>
                  <td>{g.issue}</td>
                  <td>{g.suggestion}</td>
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

export {
  CodeReportBody,
  ReviewReportBody,
  AssessmentBody,
  IncidentReviewBody,
  VERDICT_STYLES,
  SEVERITY_STYLES
}
