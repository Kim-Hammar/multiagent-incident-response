import ImageThumbnails from './shared/ImageThumbnails.jsx'
import ExampleSelector from './shared/ExampleSelector.jsx'

/**
 * Configuration tab for the Action Validator Agent.
 */
function ActionValidatorAgentConfigTab({
  systemDescription,
  setSystemDescription,
  actionToValidate,
  setActionToValidate,
  operatorFeedback,
  setOperatorFeedback,
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
          This agent validates a <strong>single specific action</strong> from a response plan by
          executing it on the digital twin and assessing recovery and service state before and
          after. Its tasks are:
          <ol>
            <li>Assess the current digital twin state before applying the action.</li>
            <li>Execute the action&apos;s commands on the appropriate containers.</li>
            <li>Re-assess recovery and service state after the action.</li>
            <li>Compute the phase-weighted step cost and produce a validation report.</li>
          </ol>
        </p>
      </div>

      <div className="ia-section">
        <label htmlFor="av-system-desc">System description</label>
        <p className="ia-hint">
          Describe the target system, its architecture, hosts, and services.
        </p>
        <textarea
          id="av-system-desc"
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
        <label htmlFor="av-action">Action to validate</label>
        <p className="ia-hint">
          Describe the specific action to validate, including which containers, commands, the
          intended effect on the system, and the purpose of the action (e.g. block attacker access,
          restore a service).
        </p>
        <textarea
          id="av-action"
          className="form-control ia-textarea"
          rows="4"
          value={actionToValidate}
          onChange={(e) => setActionToValidate(e.target.value)}
          disabled={isAgentBusy}
          placeholder={
            'e.g., Action 1 — Block attacker at firewall\n' +
            'Intended effect: block the attacker\'s access to the internal network\n' +
            'Commands:\n' +
            '  iptables -I FORWARD -s 192.168.1.50 -j DROP on i1_firewall'
          }
        />
      </div>
      <div className="ia-section">
        <label htmlFor="av-feedback">Operator input</label>
        <p className="ia-hint">
          Optionally provide additional context or instructions for the agent.
        </p>
        <textarea
          id="av-feedback"
          className="form-control ia-textarea"
          rows="3"
          value={operatorFeedback}
          onChange={(e) => setOperatorFeedback(e.target.value)}
          disabled={isAgentBusy}
          placeholder="e.g., Focus on verifying that the firewall rule is applied correctly..."
        />
      </div>
      <button
        type="button"
        className="btn btn-dark btn-sm ia-btn"
        onClick={handleRun}
        disabled={isAgentBusy || (!systemDescription && !actionToValidate)}
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
          id="av-autopilot"
          checked={autopilot}
          onChange={(e) => setAutopilot(e.target.checked)}
        />
        <label className="form-check-label" htmlFor="av-autopilot">
          Autopilot <span className="ia-hint">(auto-approve all tool requests)</span>
        </label>
      </div>
    </div>
  )
}

export default ActionValidatorAgentConfigTab
