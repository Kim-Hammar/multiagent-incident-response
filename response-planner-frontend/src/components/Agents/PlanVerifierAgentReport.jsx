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
 * Renders the final verification report for the Plan Verifier Agent.
 */
function PlanVerifierAgentReport({ entry, index, isExpanded, toggleEntry }) {
  if (entry.type !== 'plan_verifier_report') return null

  const r = entry.plan_verifier_report || {}
  const overallResultClass = {
    'Plan fully validated': 'success',
    'Plan partially validated': 'warning',
    'Plan validation failed': 'danger'
  }

  return (
    <div key={index} className="card ia-entry border-dark">
      <div className="card-body">
        <div className="ia-result-header" onClick={() => toggleEntry(index)}>
          <span className="badge badge-dark">Plan Verifier Report</span>
          <span className="ia-tool-name">Response Plan Verification</span>
          <span className="ia-toggle-hint">{isExpanded ? 'collapse' : 'expand'}</span>
        </div>

        {isExpanded && (
          <div style={{ marginTop: '10px' }}>
            {r.overall_result && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Overall Result</div>
                <span
                  className={`badge ia-severity-badge badge-${overallResultClass[r.overall_result] || 'secondary'}`}
                >
                  {r.overall_result}
                </span>
              </div>
            )}

            {(r.actual_total_cost !== undefined || r.simulated_total_cost !== undefined) && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Cost Comparison</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  <span className="badge badge-secondary">
                    Simulated (MDP): {r.simulated_total_cost ?? 'N/A'}
                  </span>
                  <span className="badge badge-dark">
                    Actual (Digital Twin): {r.actual_total_cost ?? 'N/A'}
                  </span>
                  {r.actual_total_cost !== undefined && r.simulated_total_cost !== undefined && (
                    <span
                      className={`badge badge-${Math.abs(r.actual_total_cost - r.simulated_total_cost) < 1 ? 'success' : 'warning'}`}
                    >
                      Difference: {r.actual_total_cost - r.simulated_total_cost > 0 ? '+' : ''}
                      {(r.actual_total_cost - r.simulated_total_cost).toFixed(1)}
                    </span>
                  )}
                </div>
              </div>
            )}

            {r.executive_summary && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Executive Summary</div>
                <p className="ia-assessment-body mb-0">{r.executive_summary}</p>
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
                <table className="ia-ioc-table">
                  <thead>
                    <tr>
                      <th>Check</th>
                      <th>Result</th>
                    </tr>
                  </thead>
                  <tbody>
                    {r.final_service_state.map((s, i) => (
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

            {r.action_results && r.action_results.length > 0 && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Per-Action Results</div>
                {r.action_results.map((ar, i) => (
                  <div key={i} className="card ia-attack-path mb-2">
                    <div className="card-body" style={{ padding: '10px 14px' }}>
                      <strong style={{ fontSize: '13px' }}>{ar.action_name}</strong>
                      {ar.action_description && (
                        <p className="ia-assessment-body mb-1" style={{ fontSize: '12px' }}>
                          {ar.action_description}
                        </p>
                      )}
                      {ar.outcome && (
                        <p className="ia-assessment-body mb-1" style={{ fontSize: '12px' }}>
                          <strong>Outcome:</strong> {ar.outcome}
                        </p>
                      )}
                      {ar.commands_executed && ar.commands_executed.length > 0 && (
                        <div style={{ fontSize: '12px', marginBottom: '4px' }}>
                          <strong>Commands:</strong>
                          <ul style={{ paddingLeft: '18px', marginBottom: '4px' }}>
                            {ar.commands_executed.map((cmd, j) => (
                              <li key={j}>
                                <code>{cmd}</code>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {ar.recovery_state && (
                        <div style={{ marginTop: '4px' }}>
                          <RecoveryStateBadges state={ar.recovery_state} />
                        </div>
                      )}
                      {ar.service_state && ar.service_state.length > 0 && (
                        <div
                          style={{
                            marginTop: '4px',
                            fontSize: '12px',
                            display: 'flex',
                            flexWrap: 'wrap',
                            gap: '4px'
                          }}
                        >
                          {ar.service_state.map((ss, j) => (
                            <span
                              key={j}
                              className={`badge badge-${ss.passed ? 'success' : 'danger'}`}
                            >
                              {ss.passed ? '\u2713' : '\u2717'} {ss.description}
                            </span>
                          ))}
                        </div>
                      )}
                      {ar.actual_step_cost !== undefined && (
                        <div style={{ marginTop: '4px', fontSize: '12px' }}>
                          <strong>Step cost:</strong>{' '}
                          <span className="badge badge-dark">{ar.actual_step_cost}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
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

export default PlanVerifierAgentReport
