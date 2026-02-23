import ImageThumbnails from './shared/ImageThumbnails.jsx'
import ExampleSelector from './shared/ExampleSelector.jsx'

/**
 * Configuration tab for the Host Analyzer Agent.
 */
function HostAnalyzerAgentConfigTab({
  systemDescription,
  setSystemDescription,
  securityAlerts,
  setSecurityAlerts,
  operatorFeedback,
  setOperatorFeedback,
  hostDescription,
  setHostDescription,
  systemDescriptionImages,
  setSystemDescriptionImages,
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
          This agent performs a deep analysis of a single specific host within the context of a
          security incident. Its tasks are:
          <ol>
            <li>
              Investigate the specified host using available tools (log analysis, threat
              intelligence, digital twin inspection).
            </li>
            <li>
              Determine the host&apos;s compromise status, identify attack vectors, and collect
              indicators of compromise.
            </li>
            <li>
              Produce a structured host analysis report with compromise status, affected services,
              and recommendations.
            </li>
          </ol>
        </p>
      </div>

      <div className="ia-section">
        <label htmlFor="ha-system-desc">System description</label>
        <p className="ia-hint">
          Describe the target system, its architecture, hosts, and services.
        </p>
        <textarea
          id="ha-system-desc"
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
        <label htmlFor="ha-alerts">Security alerts and logs</label>
        <p className="ia-hint">
          Paste relevant security alerts, IDS logs, or other indicators of compromise.
        </p>
        <textarea
          id="ha-alerts"
          className="form-control ia-textarea"
          rows="6"
          value={securityAlerts}
          onChange={(e) => setSecurityAlerts(e.target.value)}
          disabled={isAgentBusy}
          placeholder="e.g., [ALERT] Brute-force SSH login detected on 10.0.0.1 from 192.168.1.50..."
        />
      </div>
      <div className="ia-section">
        <label htmlFor="ha-feedback">Operator input</label>
        <p className="ia-hint">
          Optionally provide additional context or instructions for the agent.
        </p>
        <textarea
          id="ha-feedback"
          className="form-control ia-textarea"
          rows="4"
          value={operatorFeedback}
          onChange={(e) => setOperatorFeedback(e.target.value)}
          disabled={isAgentBusy}
          placeholder="e.g., Focus on lateral movement indicators and check for persistence mechanisms..."
        />
      </div>
      <div className="ia-section">
        <label htmlFor="ha-host-desc">Host to analyze</label>
        <p className="ia-hint">
          Describe the specific host to analyze, including its name, IP, role, and why it is
          suspected.
        </p>
        <textarea
          id="ha-host-desc"
          className="form-control ia-textarea"
          rows="4"
          value={hostDescription}
          onChange={(e) => setHostDescription(e.target.value)}
          disabled={isAgentBusy}
          placeholder={
            'e.g., Server 3 (10.0.3.3, Ubuntu 20) — SSH server, CI/CD build pipeline.\n' +
            'Suspected compromised via SSH brute-force from external attacker 192.168.1.50.'
          }
        />
      </div>
      <button
        type="button"
        className="btn btn-dark btn-sm ia-btn"
        onClick={handleRun}
        disabled={isAgentBusy || (!systemDescription && !hostDescription)}
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
          id="ha-autopilot"
          checked={autopilot}
          onChange={(e) => setAutopilot(e.target.checked)}
        />
        <label className="form-check-label" htmlFor="ha-autopilot">
          Autopilot <span className="ia-hint">(auto-approve all tool requests)</span>
        </label>
      </div>
    </div>
  )
}

export default HostAnalyzerAgentConfigTab
