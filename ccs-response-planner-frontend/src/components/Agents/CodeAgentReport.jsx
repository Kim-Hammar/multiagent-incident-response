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

/**
 * Renders the final code generation report for the Code Agent.
 */
function CodeAgentReport({ entry, index, isExpanded, toggleEntry }) {
  if (entry.type !== 'code_report') return null

  const r = entry.code_report || {}
  const checks = r.verification_checks || []

  return (
    <div key={index} className="card ia-entry border-dark">
      <div className="card-body">
        <div className="ia-result-header" onClick={() => toggleEntry(index)}>
          <span className="badge badge-dark">Code Report</span>
          <span className="ia-tool-name">Gymnasium MDP Environment</span>
          <span className="ia-toggle-hint">{isExpanded ? 'collapse' : 'expand'}</span>
        </div>

        {isExpanded && (
          <div style={{ marginTop: '10px' }}>
            {(checks.length > 0 || r.verification_result) && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Verification</div>
                {checks.length > 0 ? (
                  <div
                    style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}
                  >
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
                    className={`badge badge-${
                      r.verification_result.toLowerCase().includes('pass') ? 'success' : 'warning'
                    }`}
                    style={{ fontSize: '12px', padding: '5px 8px' }}
                  >
                    {r.verification_result}
                  </span>
                )}
                {r.verification_result && checks.length > 0 && (
                  <p className="ia-assessment-body mb-0" style={{ marginTop: '6px' }}>
                    {r.verification_result}
                  </p>
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
                <div className="ia-assessment-label">Generated Code</div>
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
        )}
      </div>
    </div>
  )
}

export default CodeAgentReport
