/**
 * Renders the final action validation report for the Action Validator Agent.
 */
function ActionValidatorAgentReport({ entry, index, isExpanded, toggleEntry }) {
  if (entry.type !== 'action_validation') return null

  const r = entry.action_validation || {}
  const outcomeClass = {
    'Action validated': 'success',
    'Action partially validated': 'warning',
    'Action failed': 'danger'
  }

  return (
    <div key={index} className="card ia-entry border-dark">
      <div className="card-body">
        <div className="ia-result-header" onClick={() => toggleEntry(index)}>
          <span className="badge badge-dark">Action Validation</span>
          <span className="ia-tool-name">{r.action_name || 'Action Validation Report'}</span>
          {r.outcome && (
            <span
              className={`badge badge-${outcomeClass[r.outcome] || 'secondary'}`}
              style={{ marginLeft: '8px' }}
            >
              {r.outcome}
            </span>
          )}
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

            {r.action_description && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Action Description</div>
                <p className="ia-assessment-body mb-0">{r.action_description}</p>
              </div>
            )}

            {r.commands_executed && r.commands_executed.length > 0 && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Commands Executed</div>
                <ul style={{ paddingLeft: '18px', marginBottom: '4px' }}>
                  {r.commands_executed.map((cmd, i) => (
                    <li key={i}>
                      <code>{cmd}</code>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {r.command_results && r.command_results.length > 0 && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Command Results</div>
                <table className="ia-ioc-table" style={{ tableLayout: 'fixed' }}>
                  <thead>
                    <tr>
                      <th style={{ width: '12%' }}>Container</th>
                      <th style={{ width: '28%' }}>Command</th>
                      <th style={{ width: '10%' }}>Exit Code</th>
                      <th style={{ width: '50%' }}>Output</th>
                    </tr>
                  </thead>
                  <tbody>
                    {r.command_results.map((cr, i) => (
                      <tr key={i}>
                        <td style={{ wordBreak: 'break-word' }}>{cr.container}</td>
                        <td style={{ overflowWrap: 'anywhere' }}>
                          <code>{cr.command}</code>
                        </td>
                        <td>
                          <span
                            className={`badge badge-${cr.exit_code === 0 ? 'success' : 'danger'}`}
                          >
                            {cr.exit_code}
                          </span>
                        </td>
                        <td>
                          {cr.output ? (
                            <pre
                              style={{
                                fontSize: '11px',
                                maxHeight: '120px',
                                overflow: 'auto',
                                marginBottom: 0,
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-word'
                              }}
                            >
                              {cr.output}
                            </pre>
                          ) : (
                            <span className="text-muted">(no output)</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {r.recommendations && r.recommendations.length > 0 && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Recommendations</div>
                <ul
                  style={{
                    fontSize: '13px',
                    paddingLeft: '20px',
                    marginBottom: 0
                  }}
                >
                  {r.recommendations.map((rec, i) => (
                    <li key={i}>{rec}</li>
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

export default ActionValidatorAgentReport
