/**
 * Renders the final host analysis report for the Host Analyzer Agent.
 */
function HostAnalyzerAgentReport({ entry, index, isExpanded, toggleEntry }) {
  if (entry.type !== 'host_analysis') return null

  const a = entry.host_analysis || {}
  const statusClass = {
    'Confirmed Compromised': 'danger',
    'Likely Compromised': 'warning',
    'Possibly Compromised': 'info',
    'No Evidence of Compromise': 'success'
  }

  return (
    <div key={index} className="card ia-entry border-dark">
      <div className="card-body">
        <div className="ia-result-header" onClick={() => toggleEntry(index)}>
          <span className="badge badge-dark">Host Analysis</span>
          <span className="ia-tool-name">{a.host_name || 'Host Analysis Report'}</span>
          {a.compromise_status && (
            <span
              className={`badge badge-${statusClass[a.compromise_status] || 'secondary'}`}
              style={{ marginLeft: '8px' }}
            >
              {a.compromise_status}
            </span>
          )}
          <span className="ia-toggle-hint">{isExpanded ? 'collapse' : 'expand'}</span>
        </div>

        {isExpanded && (
          <div style={{ marginTop: '10px' }}>
            {a.executive_summary && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Executive Summary</div>
                <p className="ia-assessment-body mb-0">{a.executive_summary}</p>
              </div>
            )}

            {a.compromise_details && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Compromise Details</div>
                <p className="ia-assessment-body mb-0">{a.compromise_details}</p>
              </div>
            )}

            {a.security_posture && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Security Posture</div>
                <p className="ia-assessment-body mb-0">{a.security_posture}</p>
              </div>
            )}

            {a.attack_vectors && a.attack_vectors.length > 0 && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Attack Vectors</div>
                <table className="ia-ioc-table">
                  <thead>
                    <tr>
                      <th>Vector</th>
                      <th>Description</th>
                      <th>Evidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {a.attack_vectors.map((v, i) => (
                      <tr key={i}>
                        <td>{v.vector}</td>
                        <td>{v.description}</td>
                        <td>{v.evidence}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
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

            {a.affected_services && a.affected_services.length > 0 && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Affected Services</div>
                <table className="ia-asset-table">
                  <thead>
                    <tr>
                      <th>Service</th>
                      <th>Status</th>
                      <th>Impact</th>
                    </tr>
                  </thead>
                  <tbody>
                    {a.affected_services.map((svc, i) => (
                      <tr key={i}>
                        <td>{svc.service}</td>
                        <td>{svc.status}</td>
                        <td>{svc.impact}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {a.recommendations && a.recommendations.length > 0 && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Recommendations</div>
                <ol className="ia-assessment-body mb-0">
                  {a.recommendations.map((rec, i) => (
                    <li key={i}>{rec}</li>
                  ))}
                </ol>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default HostAnalyzerAgentReport
