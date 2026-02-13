/**
 * Renders the final DP agent report for the DP Agent.
 */
function DpAgentReport({ entry, index, isExpanded, toggleEntry }) {
  if (entry.type !== 'planner_report') return null

  const r = entry.planner_report || {}
  const actions = r.action_sequence || []
  const contingencies = r.contingencies || []
  const risks = r.risks || []

  return (
    <div key={index} className="card ia-entry border-dark">
      <div className="card-body">
        <div className="ia-result-header" onClick={() => toggleEntry(index)}>
          <span className="badge badge-dark">DP Planner Report</span>
          <span className="ia-tool-name">DP Incident Response Plan</span>
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

            {(r.method || r.parameters) && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Method &amp; Parameters</div>
                {r.method && (
                  <p className="ia-assessment-body mb-1">
                    <strong>Method:</strong> {r.method}
                  </p>
                )}
                {r.parameters && (
                  <p className="ia-assessment-body mb-0">
                    <strong>Parameters:</strong> {r.parameters}
                  </p>
                )}
              </div>
            )}

            {r.solving_summary && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Solving Summary</div>
                <p className="ia-assessment-body mb-0">{r.solving_summary}</p>
              </div>
            )}

            {actions.length > 0 && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Recommended Action Sequence</div>
                <table className="ia-ioc-table">
                  <thead>
                    <tr>
                      <th>Step</th>
                      <th>Action</th>
                      <th>Description</th>
                      <th>Commands</th>
                      <th>Expected Effect</th>
                    </tr>
                  </thead>
                  <tbody>
                    {actions.map((a, i) => (
                      <tr key={i}>
                        <td>{a.step}</td>
                        <td>
                          <strong>{a.action}</strong>
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
                        <td>{a.expected_effect}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {contingencies.length > 0 && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Contingencies</div>
                <table className="ia-ioc-table">
                  <thead>
                    <tr>
                      <th>Condition</th>
                      <th>Alternative Action</th>
                      <th>Rationale</th>
                    </tr>
                  </thead>
                  <tbody>
                    {contingencies.map((c, i) => (
                      <tr key={i}>
                        <td>{c.condition}</td>
                        <td>{c.alternative_action}</td>
                        <td>{c.rationale}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
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

export default DpAgentReport
