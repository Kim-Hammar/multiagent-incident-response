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
 * Strip trailing JSON structure that sometimes leaks into LLM field values
 * via function calling (e.g. "None. Validated.}],executive_summary:").
 */
function cleanField(val) {
  if (typeof val !== 'string') return val == null ? '' : String(val)
  return val.replace(/}\][,\s]*[a-z_]\w*\s*:[\s\S]*$/i, '').trim() || val
}

/**
 * Renders the final review report for the Report Reviewer Agent.
 */
function ReportReviewerReport({ entry, index, isExpanded, toggleEntry }) {
  if (entry.type !== 'report_review') return null

  const r = entry.report_review || {}
  const findings = r.findings || []
  const missingElements = r.missing_elements || []
  const evidenceGaps = r.evidence_gaps || []
  const strengths = r.strengths || []

  return (
    <div key={index} className="card ia-entry border-dark">
      <div className="card-body">
        <div className="ia-result-header" onClick={() => toggleEntry(index)}>
          <span className="badge badge-dark">Review Report</span>
          <span className="ia-tool-name">Incident Report Review</span>
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
                        <td>{cleanField(f.category)}</td>
                        <td>
                          <span
                            className={`badge badge-${SEVERITY_STYLES[f.severity] || 'secondary'}`}
                          >
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
        )}
      </div>
    </div>
  )
}

export default ReportReviewerReport
