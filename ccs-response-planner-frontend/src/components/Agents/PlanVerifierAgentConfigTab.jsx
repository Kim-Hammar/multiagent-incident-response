import ImageThumbnails from './shared/ImageThumbnails.jsx'
import ExampleSelector from './shared/ExampleSelector.jsx'

/**
 * Configuration tab for the Plan Verifier Agent.
 */
function PlanVerifierAgentConfigTab({
  systemDescription,
  setSystemDescription,
  incidentReport,
  setIncidentReport,
  responsePlan,
  setResponsePlan,
  specificationCommands,
  setSpecificationCommands,
  codeReport,
  setCodeReport,
  plannerReport,
  setPlannerReport,
  systemDescriptionImages,
  setSystemDescriptionImages,
  incidentReportImages,
  setIncidentReportImages,
  handlePaste,
  isAgentBusy,
  handleRun,
  loadExample,
  handleClear,
  autopilot,
  setAutopilot,
  plannerReportId
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
          This agent validates a response plan against the deployed digital twin. Its tasks are
          threefold:
          <ol>
            <li>
              Apply each response action sequentially on the digital twin containers using shell
              commands.
            </li>
            <li>
              After each action, check the recovery state and service state (specification
              commands).
            </li>
            <li>
              Produce a structured validation report with per-action results and overall outcome.
            </li>
            <li>
              Compute actual cost from digital twin execution and compare with the simulated MDP
              cost from the planner report.
            </li>
          </ol>
        </p>
      </div>

      <div className="ia-section">
        <label htmlFor="va-system-desc">System description</label>
        <p className="ia-hint">
          Describe the target system, its architecture, hosts, and services.
        </p>
        <textarea
          id="va-system-desc"
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
        <label htmlFor="va-incident-report">Incident report</label>
        <p className="ia-hint">
          Paste the incident report/assessment produced by the Information Agent.
        </p>
        <textarea
          id="va-incident-report"
          className="form-control ia-textarea"
          rows="6"
          value={incidentReport}
          onChange={(e) => setIncidentReport(e.target.value)}
          disabled={isAgentBusy}
          placeholder="e.g., An SSH brute-force attack was detected on server 3, followed by SQL injection from server 6..."
        />
        <ImageThumbnails
          images={incidentReportImages}
          setImages={setIncidentReportImages}
          disabled={isAgentBusy}
        />
      </div>
      <div className="ia-section">
        <label htmlFor="va-response-plan">Response plan</label>
        <p className="ia-hint">Paste the response plan to validate against the digital twin.</p>
        <textarea
          id="va-response-plan"
          className="form-control ia-textarea"
          rows="6"
          value={responsePlan}
          onChange={(e) => setResponsePlan(e.target.value)}
          disabled={isAgentBusy}
          placeholder="e.g., 1. Block attacker IP on firewall. 2. Kill malicious processes on server 3. 3. Rotate credentials..."
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
        <label htmlFor="va-code-report">Code Agent report</label>
        <p className="ia-hint">
          JSON report from the Code Agent containing MDP environment code, actions, and state
          description.
        </p>
        <textarea
          id="va-code-report"
          className="form-control ia-textarea"
          rows="8"
          value={codeReport}
          onChange={(e) => setCodeReport(e.target.value)}
          disabled={isAgentBusy}
          style={{ fontFamily: 'monospace', fontSize: '12px' }}
          placeholder="Paste the Code Agent report JSON..."
        />
      </div>
      <div className="ia-section">
        <label htmlFor="va-planner-report">
          Planner Agent report
          {plannerReportId && (
            <span className="badge badge-success ml-2">
              <i className="fa fa-check" /> Policy available
            </span>
          )}
        </label>
        <p className="ia-hint">
          JSON report from the Planner Agent containing action sequence and expected total cost.
        </p>
        <textarea
          id="va-planner-report"
          className="form-control ia-textarea"
          rows="8"
          value={plannerReport}
          onChange={(e) => setPlannerReport(e.target.value)}
          disabled={isAgentBusy}
          style={{ fontFamily: 'monospace', fontSize: '12px' }}
          placeholder="Paste the Planner Agent report JSON..."
        />
      </div>
      <button
        type="button"
        className="btn btn-dark btn-sm ia-btn"
        onClick={handleRun}
        disabled={isAgentBusy || (!systemDescription && !incidentReport)}
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
          id="va-autopilot"
          checked={autopilot}
          onChange={(e) => setAutopilot(e.target.checked)}
        />
        <label className="form-check-label" htmlFor="va-autopilot">
          Autopilot <span className="ia-hint">(auto-approve all tool requests)</span>
        </label>
      </div>
    </div>
  )
}

export default PlanVerifierAgentConfigTab
