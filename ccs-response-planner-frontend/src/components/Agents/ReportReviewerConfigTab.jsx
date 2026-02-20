import ImageThumbnails from './shared/ImageThumbnails.jsx'
import ExampleSelector from './shared/ExampleSelector.jsx'

/**
 * Configuration tab for the Report Reviewer Agent.
 */
function ReportReviewerConfigTab({
  systemDescription,
  setSystemDescription,
  securityAlerts,
  setSecurityAlerts,
  operatorFeedback,
  setOperatorFeedback,
  incidentReport,
  setIncidentReport,
  systemDescriptionImages,
  setSystemDescriptionImages,
  securityAlertsImages,
  setSecurityAlertsImages,
  operatorFeedbackImages,
  setOperatorFeedbackImages,
  handlePaste,
  isAgentBusy,
  handleRun,
  loadExample,
  handleClear,
  autopilot,
  setAutopilot
}) {
  return (
    <div style={{ marginTop: '16px' }}>
      <div className="ia-description">
        <p>
          This agent reviews an incident report produced by the Report Agent. It verifies claims
          using threat intelligence APIs and digital twin inspection, then produces a structured
          review identifying gaps, unsubstantiated claims, and missing elements.
          <ol>
            <li>Analyze the incident report for completeness, evidence quality, and accuracy.</li>
            <li>Verify claims using threat intel lookups and digital twin inspection.</li>
            <li>Produce a structured review with findings and recommendations.</li>
          </ol>
        </p>
      </div>

      <div className="ia-section">
        <label htmlFor="rr-system-desc">System description</label>
        <p className="ia-hint">
          Describe the target system, its architecture, hosts, and services.
        </p>
        <textarea
          id="rr-system-desc"
          className="form-control ia-textarea"
          rows="6"
          value={systemDescription}
          onChange={(e) => setSystemDescription(e.target.value)}
          onPaste={handlePaste(setSystemDescriptionImages)}
          disabled={isAgentBusy}
          placeholder="e.g., The system consists of a web server, database server, and firewall..."
        />
        <ImageThumbnails
          images={systemDescriptionImages}
          setImages={setSystemDescriptionImages}
          disabled={isAgentBusy}
        />
      </div>
      <div className="ia-section">
        <label htmlFor="rr-alerts">Security alerts and logs</label>
        <p className="ia-hint">
          Paste relevant security alerts, IDS logs, or other indicators of compromise.
        </p>
        <textarea
          id="rr-alerts"
          className="form-control ia-textarea"
          rows="6"
          value={securityAlerts}
          onChange={(e) => setSecurityAlerts(e.target.value)}
          onPaste={handlePaste(setSecurityAlertsImages)}
          disabled={isAgentBusy}
          placeholder="e.g., [ALERT] Brute-force SSH login detected on 10.0.0.1..."
        />
        <ImageThumbnails
          images={securityAlertsImages}
          setImages={setSecurityAlertsImages}
          disabled={isAgentBusy}
        />
      </div>
      <div className="ia-section">
        <label htmlFor="rr-feedback">Operator feedback (optional)</label>
        <p className="ia-hint">Additional guidance or constraints for the review.</p>
        <textarea
          id="rr-feedback"
          className="form-control ia-textarea"
          rows="4"
          value={operatorFeedback}
          onChange={(e) => setOperatorFeedback(e.target.value)}
          onPaste={handlePaste(setOperatorFeedbackImages)}
          disabled={isAgentBusy}
          placeholder="e.g., Pay special attention to the severity rating and IOC evidence."
        />
        <ImageThumbnails
          images={operatorFeedbackImages}
          setImages={setOperatorFeedbackImages}
          disabled={isAgentBusy}
        />
      </div>
      <div className="ia-section">
        <label htmlFor="rr-incident-report">Incident report (from Report Agent)</label>
        <p className="ia-hint">Paste the JSON assessment produced by the Report Agent.</p>
        <textarea
          id="rr-incident-report"
          className="form-control ia-textarea"
          rows="12"
          value={incidentReport}
          onChange={(e) => setIncidentReport(e.target.value)}
          disabled={isAgentBusy}
          placeholder='{"incident_summary": "...", "attack_vector_analysis": "...", ...}'
          style={{ fontFamily: 'monospace', fontSize: '12px' }}
        />
      </div>
      <button
        type="button"
        className="btn btn-dark btn-sm ia-btn"
        onClick={handleRun}
        disabled={isAgentBusy || !incidentReport}
      >
        <i className="fa fa-bolt" aria-hidden="true" />
        {isAgentBusy ? ' Running...' : ' Run agent'}
      </button>
      <ExampleSelector onLoad={loadExample} disabled={isAgentBusy} />
      <button
        type="button"
        className="btn btn-outline-secondary btn-sm ia-btn"
        onClick={handleClear}
        disabled={isAgentBusy}
      >
        <i className="fa fa-eraser" aria-hidden="true" /> Clear all
      </button>
      <div className="form-check form-check-inline ia-btn">
        <input
          className="form-check-input"
          type="checkbox"
          id="rr-autopilot"
          checked={autopilot}
          onChange={(e) => setAutopilot(e.target.checked)}
        />
        <label className="form-check-label" htmlFor="rr-autopilot">
          Autopilot <span className="ia-hint">(auto-approve all tool requests)</span>
        </label>
      </div>
    </div>
  )
}

export default ReportReviewerConfigTab
