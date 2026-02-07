/**
 * Planning process tab — shows spinner during generation,
 * the plan result when available, or a placeholder message.
 */
function PlanningTab({ planResult, generating }) {
  if (generating) {
    return (
      <div className="planning-spinner">
        <div className="spinner-border spinner-border-sm" role="status">
          <span className="sr-only">Loading...</span>
        </div>
        <span className="ml-2">Generating plan...</span>
      </div>
    )
  }

  if (planResult) {
    const severityColors = {
      low: 'success',
      medium: 'warning',
      high: 'danger',
      critical: 'danger'
    }
    const badgeColor = severityColors[planResult.severity] || 'secondary'

    return (
      <div className="planning-result">
        <div className="planning-meta">
          <span className={`badge badge-${badgeColor} mr-2`}>Severity: {planResult.severity}</span>
          <span className="badge badge-info">Status: {planResult.status}</span>
        </div>
        <h5 className="mt-3 mb-2">Response steps</h5>
        <ol className="planning-steps">
          {planResult.steps.map((step, i) => (
            <li key={i}>{step.replace(/^\d+\.\s*/, '')}</li>
          ))}
        </ol>
        <h5 className="mt-3 mb-2">Incident description</h5>
        <p className="planning-description">{planResult.incident_description}</p>
      </div>
    )
  }

  return (
    <p className="planning-placeholder">
      Click &quot;Generate plan&quot; on the Configuration tab to start.
    </p>
  )
}

export default PlanningTab
