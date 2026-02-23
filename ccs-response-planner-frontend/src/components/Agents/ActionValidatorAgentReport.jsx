const RECOVERY_STATE_LABELS = {
  is_attack_contained: 'Attack Contained',
  is_attack_assessed: 'Attack Assessed',
  is_forensic_evidence_preserved: 'Forensic Evidence Preserved',
  is_attack_evicted: 'Attack Evicted',
  is_system_hardened: 'System Hardened',
  are_services_restored: 'Services Restored'
}

function RecoveryStateBadges({ state }) {
  if (!state) return null
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
      {Object.entries(RECOVERY_STATE_LABELS).map(([key, label]) => (
        <span key={key} className={`badge badge-${state[key] ? 'success' : 'secondary'}`}>
          {state[key] ? '\u2713' : '\u2717'} {label}
        </span>
      ))}
    </div>
  )
}

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

            {r.step_cost !== undefined && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Step Cost</div>
                <span className="badge badge-dark">{r.step_cost}</span>
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
                <table className="ia-ioc-table">
                  <thead>
                    <tr>
                      <th>Container</th>
                      <th>Command</th>
                      <th>Exit Code</th>
                      <th>Output</th>
                    </tr>
                  </thead>
                  <tbody>
                    {r.command_results.map((cr, i) => (
                      <tr key={i}>
                        <td>{cr.container}</td>
                        <td>
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
                                marginBottom: 0
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

            {r.recovery_state_before && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Recovery State Before</div>
                <RecoveryStateBadges state={r.recovery_state_before} />
              </div>
            )}

            {r.recovery_state_after && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Recovery State After</div>
                <RecoveryStateBadges state={r.recovery_state_after} />
              </div>
            )}

            {r.service_state && r.service_state.length > 0 && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Service State</div>
                <table className="ia-ioc-table">
                  <thead>
                    <tr>
                      <th>Check</th>
                      <th>Result</th>
                    </tr>
                  </thead>
                  <tbody>
                    {r.service_state.map((s, i) => (
                      <tr key={i}>
                        <td>{s.description}</td>
                        <td>
                          <span className={`badge badge-${s.passed ? 'success' : 'danger'}`}>
                            {s.passed ? 'Passed' : 'Failed'}
                          </span>
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
