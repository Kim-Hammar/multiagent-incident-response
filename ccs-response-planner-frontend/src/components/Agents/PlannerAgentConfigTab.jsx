import ImageThumbnails from './shared/ImageThumbnails.jsx'
import ExampleSelector from './shared/ExampleSelector.jsx'

/**
 * Configuration tab for the Planner Agent.
 */
function PlannerAgentConfigTab({
  systemDescription,
  setSystemDescription,
  incidentReport,
  setIncidentReport,
  specificationCommands,
  setSpecificationCommands,
  operatorFeedback,
  setOperatorFeedback,
  codeReport,
  setCodeReport,
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
      <div className="ia-description">
        <p>
          This agent trains a reinforcement learning policy on a Gymnasium MDP environment generated
          by the Code Agent. It learns an optimal incident response strategy and produces an
          actionable plan based on the learned policy.
          <ol>
            <li>Analyze the MDP code to understand state space, actions, and transitions.</li>
            <li>Train an RL policy (PPO) with live reward curve streaming.</li>
            <li>Evaluate the learned policy and produce a structured incident response plan.</li>
          </ol>
        </p>
      </div>

      <div className="ia-section">
        <label htmlFor="mdp-system-desc">System description</label>
        <p className="ia-hint">
          Describe the target system, its architecture, hosts, and services.
        </p>
        <textarea
          id="mdp-system-desc"
          className="form-control ia-textarea"
          rows="6"
          value={systemDescription}
          onChange={(e) => setSystemDescription(e.target.value)}
          onPaste={handlePaste}
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
        <label htmlFor="mdp-incident-report">Incident report</label>
        <p className="ia-hint">
          Paste the incident report/assessment produced by the Information Agent.
        </p>
        <textarea
          id="mdp-incident-report"
          className="form-control ia-textarea"
          rows="6"
          value={incidentReport}
          onChange={(e) => setIncidentReport(e.target.value)}
          disabled={isAgentBusy}
          placeholder="e.g., An SSH brute-force attack was detected on server 3..."
        />
      </div>
      <div className="ia-section">
        <label>Specification commands</label>
        <p className="ia-hint">Service-level requirements that must hold after recovery.</p>
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
      <div className="ia-section">
        <label htmlFor="mdp-operator-feedback">Operator feedback (optional)</label>
        <p className="ia-hint">Additional guidance or constraints for the planner.</p>
        <textarea
          id="mdp-operator-feedback"
          className="form-control ia-textarea"
          rows="4"
          value={operatorFeedback}
          onChange={(e) => setOperatorFeedback(e.target.value)}
          disabled={isAgentBusy}
          placeholder="e.g., Prioritize containment actions and minimize service downtime."
        />
      </div>
      <div className="ia-section">
        <label htmlFor="mdp-code-report">Code Agent report</label>
        <p className="ia-hint">Paste the JSON code report produced by the Code Agent.</p>
        <textarea
          id="mdp-code-report"
          className="form-control ia-textarea"
          rows="12"
          value={codeReport}
          onChange={(e) => setCodeReport(e.target.value)}
          disabled={isAgentBusy}
          placeholder='{"executive_summary": "...", "generated_code": "...", "actions": [...], ...}'
          style={{ fontFamily: 'monospace', fontSize: '12px' }}
        />
      </div>
      <button
        type="button"
        className="btn btn-dark btn-sm ia-btn"
        onClick={handleRun}
        disabled={isAgentBusy || !codeReport}
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
          id="mdp-autopilot"
          checked={autopilot}
          onChange={(e) => setAutopilot(e.target.checked)}
        />
        <label className="form-check-label" htmlFor="mdp-autopilot">
          Autopilot <span className="ia-hint">(auto-approve all tool requests)</span>
        </label>
      </div>
    </div>
  )
}

export default PlannerAgentConfigTab
