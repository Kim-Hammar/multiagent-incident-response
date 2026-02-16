import ImageThumbnails from './shared/ImageThumbnails.jsx'
import ExampleSelector from './shared/ExampleSelector.jsx'

/**
 * Configuration tab for the Validation Agent.
 */
function ValidationAgentConfigTab({
  systemDescription,
  setSystemDescription,
  incidentReport,
  setIncidentReport,
  responsePlan,
  setResponsePlan,
  specification,
  setSpecification,
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
        <label htmlFor="va-specification">Specification commands</label>
        <p className="ia-hint">
          JSON array of specification commands used to verify service state after each action.
        </p>
        <textarea
          id="va-specification"
          className="form-control ia-textarea"
          rows="4"
          value={specification}
          onChange={(e) => setSpecification(e.target.value)}
          disabled={isAgentBusy}
          placeholder='[{"host": "server_1", "command": "...", "description": "..."}]'
        />
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
          RL Agent report
          {plannerReportId && (
            <span className="badge badge-success ml-2">
              <i className="fa fa-check" /> Policy available
            </span>
          )}
        </label>
        <p className="ia-hint">
          JSON report from the RL Agent containing action sequence and expected total cost.
        </p>
        <textarea
          id="va-planner-report"
          className="form-control ia-textarea"
          rows="8"
          value={plannerReport}
          onChange={(e) => setPlannerReport(e.target.value)}
          disabled={isAgentBusy}
          style={{ fontFamily: 'monospace', fontSize: '12px' }}
          placeholder="Paste the RL Agent report JSON..."
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

export default ValidationAgentConfigTab
