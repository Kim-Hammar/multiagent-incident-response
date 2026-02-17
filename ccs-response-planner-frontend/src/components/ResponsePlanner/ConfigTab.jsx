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
  specificationCommands,
  setSpecificationCommands,
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
  const updateCommand = (index, field, value) => {
    setSpecificationCommands((prev) =>
      prev.map((cmd, i) => (i === index ? { ...cmd, [field]: value } : cmd))
    )
  }

  const removeCommand = (index) => {
    setSpecificationCommands((prev) => prev.filter((_, i) => i !== index))
  }

  const addCommand = () => {
    setSpecificationCommands((prev) => [...prev, { host: '', description: '', command: '' }])
  }

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

      <div className="ia-section">
        <label>Specification commands</label>
        <p className="ia-hint">
          Service-level requirements that must hold after recovery.
        </p>
        <div
          style={{
            border: '1px solid #dee2e6',
            borderRadius: '4px',
            padding: '10px 14px',
            fontSize: '12px',
            maxHeight: '300px',
            overflowY: 'auto'
          }}
        >
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #dee2e6', textAlign: 'left' }}>
                <th style={{ padding: '4px 8px 6px 0', fontWeight: 600 }}>Host</th>
                <th style={{ padding: '4px 8px 6px 0', fontWeight: 600 }}>Description</th>
                <th style={{ padding: '4px 8px 6px 0', fontWeight: 600 }}>Command</th>
                <th style={{ padding: '4px 0 6px 0', fontWeight: 600, width: '32px' }} />
              </tr>
            </thead>
            <tbody>
              {specificationCommands.map((cmd, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #f0f0f0' }}>
                  <td style={{ padding: '3px 6px 3px 0' }}>
                    <input
                      type="text"
                      className="form-control form-control-sm"
                      value={cmd.host}
                      onChange={(e) => updateCommand(i, 'host', e.target.value)}
                      disabled={isAgentBusy}
                      placeholder="hostname"
                      style={{ fontSize: '12px', fontFamily: 'monospace' }}
                    />
                  </td>
                  <td style={{ padding: '3px 6px 3px 0' }}>
                    <input
                      type="text"
                      className="form-control form-control-sm"
                      value={cmd.description}
                      onChange={(e) => updateCommand(i, 'description', e.target.value)}
                      disabled={isAgentBusy}
                      placeholder="what to verify"
                      style={{ fontSize: '12px' }}
                    />
                  </td>
                  <td style={{ padding: '3px 6px 3px 0' }}>
                    <input
                      type="text"
                      className="form-control form-control-sm"
                      value={cmd.command}
                      onChange={(e) => updateCommand(i, 'command', e.target.value)}
                      disabled={isAgentBusy}
                      placeholder="shell command"
                      style={{ fontSize: '12px', fontFamily: 'monospace' }}
                    />
                  </td>
                  <td style={{ padding: '3px 0', textAlign: 'center' }}>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-danger"
                      onClick={() => removeCommand(i)}
                      disabled={isAgentBusy}
                      title="Remove row"
                      style={{ padding: '1px 6px', fontSize: '11px', lineHeight: 1.4 }}
                    >
                      <i className="fa fa-times" aria-hidden="true" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {specificationCommands.length === 0 && (
            <p
              style={{
                textAlign: 'center',
                color: '#888',
                margin: '8px 0 4px',
                fontSize: '12px'
              }}
            >
              No specification commands. Add rows manually or load an example.
            </p>
          )}
          <button
            type="button"
            className="btn btn-sm btn-outline-secondary"
            onClick={addCommand}
            disabled={isAgentBusy}
            style={{ marginTop: '6px', fontSize: '11px' }}
          >
            <i className="fa fa-plus" aria-hidden="true" /> Add row
          </button>
        </div>
      </div>

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
