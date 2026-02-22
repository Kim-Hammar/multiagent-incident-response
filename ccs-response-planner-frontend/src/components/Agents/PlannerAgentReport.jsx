function downloadPolicyZip(policyData) {
  const bytes = Uint8Array.from(atob(policyData), (c) => c.charCodeAt(0))
  const blob = new Blob([bytes], { type: 'application/zip' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'rl_policy.zip'
  a.click()
  URL.revokeObjectURL(url)
}

/**
 * Renders the final Planner Agent report.
 */
function PlannerAgentReport({ entry, index, isExpanded, toggleEntry, policyData }) {
  if (entry.type !== 'planner_report') return null

  const r = entry.planner_report || {}
  const actions = r.action_sequence || []
  const risks = r.risks || []

  return (
    <div key={index} className="card ia-entry border-dark">
      <div className="card-body">
        <div className="ia-result-header" onClick={() => toggleEntry(index)}>
          <span className="badge badge-dark">Planner Report</span>
          <span className="ia-tool-name">MDP Incident Response Plan</span>
          <span className="ia-toggle-hint">{isExpanded ? 'collapse' : 'expand'}</span>
        </div>

        {isExpanded && (
          <div style={{ marginTop: '10px' }}>
            {r.executive_summary && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Executive Summary</div>
                <p className="ia-assessment-body mb-0">{r.executive_summary}</p>
              </div>
            )}

            {(r.algorithm || r.hyperparameters) && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Algorithm &amp; Hyperparameters</div>
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
                <div className="ia-assessment-label">Training Summary</div>
                <p className="ia-assessment-body mb-0">{r.training_summary}</p>
              </div>
            )}

            {actions.length > 0 && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Recommended Action Sequence</div>
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
                          <td style={{ fontSize: '12px' }}>
                            {a.rationale || a.expected_effect || '-'}
                          </td>
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
                <span
                  className="badge badge-dark"
                  style={{ fontSize: '14px', padding: '6px 12px' }}
                >
                  {r.expected_total_cost}
                </span>
              </div>
            )}

            {policyData && (
              <div className="ia-assessment-section">
                <button
                  className="btn btn-sm btn-outline-dark"
                  onClick={() => downloadPolicyZip(policyData)}
                >
                  <i className="fa fa-download" /> Download policy
                </button>
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
        )}
      </div>
    </div>
  )
}

export default PlannerAgentReport
