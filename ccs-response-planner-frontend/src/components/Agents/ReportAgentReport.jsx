/**
 * Renders the final assessment report for the Report Agent.
 */
function ReportAgentReport({ entry, index, isExpanded, toggleEntry }) {
  if (entry.type !== 'assessment') return null

  const a = entry.assessment || {}
  const severityClass = {
    Critical: 'danger',
    High: 'warning',
    Medium: 'info',
    Low: 'success'
  }

  return (
    <div key={index} className="card ia-entry border-dark">
      <div className="card-body">
        <div className="ia-result-header" onClick={() => toggleEntry(index)}>
          <span className="badge badge-dark">Assessment</span>
          <span className="ia-tool-name">Final Incident Assessment</span>
          <span className="ia-toggle-hint">{isExpanded ? 'collapse' : 'expand'}</span>
        </div>

        {isExpanded && (
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

            {a.attack_path_image && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Attack Path Visualization</div>
                <img
                  src={a.attack_path_image}
                  alt="Attack path diagram"
                  style={{
                    maxWidth: '100%',
                    border: '1px solid #dee2e6',
                    borderRadius: '4px',
                    marginTop: '8px'
                  }}
                />
              </div>
            )}

            {a.severity && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Severity</div>
                <span
                  className={`badge ia-severity-badge badge-${severityClass[a.severity] || 'secondary'}`}
                >
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
          </div>
        )}
      </div>
    </div>
  )
}

export default ReportAgentReport
