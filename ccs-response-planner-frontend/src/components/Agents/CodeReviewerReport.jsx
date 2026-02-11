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
 * Renders the final code review report for the Code Reviewer Agent.
 */
function CodeReviewerReport({ entry, index, isExpanded, toggleEntry }) {
  if (entry.type !== 'review_report') return null

  const r = entry.review_report || {}
  const findings = r.findings || []
  const missingActions = r.missing_actions || []
  const commandIssues = r.command_issues || []
  const strengths = r.strengths || []

  return (
    <div key={index} className="card ia-entry border-dark">
      <div className="card-body">
        <div className="ia-result-header" onClick={() => toggleEntry(index)}>
          <span className="badge badge-dark">Review Report</span>
          <span className="ia-tool-name">MDP Code Review</span>
          <span className="ia-toggle-hint">{isExpanded ? 'collapse' : 'expand'}</span>
        </div>

        {isExpanded && (
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
                          <span
                            className={`badge badge-${SEVERITY_STYLES[f.severity] || 'secondary'}`}
                          >
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
        )}
      </div>
    </div>
  )
}

export default CodeReviewerReport
