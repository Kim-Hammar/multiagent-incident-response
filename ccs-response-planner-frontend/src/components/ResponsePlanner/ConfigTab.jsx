import ExampleSelector from '../Agents/shared/ExampleSelector.jsx'
import ImageThumbnails from '../Agents/shared/ImageThumbnails.jsx'

/**
 * Incident description tab for the response planner — input form with
 * system description, security alerts, operator feedback, specification
 * commands, action buttons, and inline controls.
 */
function ConfigTab({
  systemDescription,
  setSystemDescription,
  securityAlerts,
  setSecurityAlerts,
  operatorFeedback,
  setOperatorFeedback,
  specification,
  systemDescriptionImages,
  setSystemDescriptionImages,
  securityAlertsImages,
  setSecurityAlertsImages,
  handlePaste,
  loadExample,
  onRun,
  onClear,
  isAgentBusy,
  autopilot,
  setAutopilot
}) {
  return (
    <div style={{ marginTop: '16px' }}>
      <div className="ia-section">
        <label htmlFor="rp-system-desc">System description</label>
        <p className="ia-hint">
          Describe the target system, its architecture, hosts, and services.
        </p>
        <textarea
          id="rp-system-desc"
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
        <label htmlFor="rp-security-alerts">Security alerts</label>
        <p className="ia-hint">Paste the security alerts/logs that triggered incident response.</p>
        <textarea
          id="rp-security-alerts"
          className="form-control ia-textarea"
          rows="6"
          value={securityAlerts}
          onChange={(e) => setSecurityAlerts(e.target.value)}
          onPaste={handlePaste(setSecurityAlertsImages)}
          disabled={isAgentBusy}
          placeholder="e.g., IDS alert: SSH brute-force detected from 10.0.0.2 targeting server 3..."
        />
        <ImageThumbnails
          images={securityAlertsImages}
          setImages={setSecurityAlertsImages}
          disabled={isAgentBusy}
        />
      </div>
      <div className="ia-section">
        <label htmlFor="rp-operator-feedback">Operator feedback (optional)</label>
        <p className="ia-hint">Additional guidance or constraints for the pipeline.</p>
        <textarea
          id="rp-operator-feedback"
          className="form-control ia-textarea"
          rows="4"
          value={operatorFeedback}
          onChange={(e) => setOperatorFeedback(e.target.value)}
          disabled={isAgentBusy}
          placeholder="e.g., Focus on containment actions first."
        />
      </div>
      {specification && (
        <div className="ia-section">
          <label htmlFor="rp-specification">Specification commands</label>
          <p className="ia-hint">
            Service-level requirements that must be satisfied after recovery. These are loaded from
            the selected example and used by the planning agents.
          </p>
          <textarea
            id="rp-specification"
            className="form-control ia-textarea"
            rows="4"
            value={specification}
            readOnly
            style={{ backgroundColor: '#f8f9fa' }}
          />
        </div>
      )}

      <button
        type="button"
        className="btn btn-dark btn-sm ia-btn"
        onClick={onRun}
        disabled={isAgentBusy || (!systemDescription && !securityAlerts)}
      >
        <i className="fa fa-bolt" aria-hidden="true" />
        {isAgentBusy ? ' Running...' : ' Run agent'}
      </button>
      <ExampleSelector onLoad={loadExample} disabled={isAgentBusy} />
      <button
        type="button"
        className="btn btn-outline-secondary btn-sm ia-btn"
        onClick={onClear}
        disabled={isAgentBusy}
      >
        <i className="fa fa-eraser" aria-hidden="true" /> Clear all
      </button>
      <div className="form-check form-check-inline ia-btn">
        <input
          className="form-check-input"
          type="checkbox"
          id="rp-autopilot"
          checked={autopilot}
          onChange={(e) => setAutopilot(e.target.checked)}
        />
        <label className="form-check-label" htmlFor="rp-autopilot">
          Autopilot <span className="ia-hint">(auto-approve all tool requests)</span>
        </label>
      </div>
    </div>
  )
}

export default ConfigTab
