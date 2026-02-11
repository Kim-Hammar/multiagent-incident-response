import ImageThumbnails from './shared/ImageThumbnails.jsx'
import PromptModal from './shared/PromptModal.jsx'

/**
 * Configuration tab for the Information Agent.
 */
function InformationAgentConfigTab({
  systemDescription,
  setSystemDescription,
  securityAlerts,
  setSecurityAlerts,
  operatorFeedback,
  setOperatorFeedback,
  systemDescriptionImages,
  setSystemDescriptionImages,
  securityAlertsImages,
  setSecurityAlertsImages,
  operatorFeedbackImages,
  setOperatorFeedbackImages,
  handlePaste,
  isAgentBusy,
  handleRun,
  fetchExample,
  handleClear,
  fetchPrompt,
  loadingPrompt,
  models,
  selectedModel,
  setSelectedModel,
  autopilot,
  setAutopilot,
  showPromptModal,
  promptText,
  setShowPromptModal
}) {
  return (
    <div style={{ marginTop: '16px' }}>
      <div className="ia-description">
        <p>
          The tasks of this agent are threefold:
          <ol>
            <li>
              Analyze the available information about the incident and determine whether we have
              sufficient information to proceed with incident response planning.
            </li>
            <li>
              If we do not have sufficient information, select tools to call in order to collect the
              necessary information.{' '}
            </li>
            <li>
              Once sufficient information has been collected, produce an incident report/assessment.
            </li>
          </ol>
        </p>
      </div>

      <div className="ia-section">
        <label htmlFor="ia-system-desc">System description</label>
        <p className="ia-hint">
          Describe the target system, its architecture, hosts, and services.
        </p>
        <textarea
          id="ia-system-desc"
          className="form-control ia-textarea"
          rows="8"
          value={systemDescription}
          onChange={(e) => setSystemDescription(e.target.value)}
          onPaste={handlePaste(setSystemDescriptionImages)}
          disabled={isAgentBusy}
          placeholder="e.g., The system consists of a web server (Apache on 10.0.0.1), a database server (PostgreSQL on 10.0.0.2), and a firewall..."
        />
        <ImageThumbnails
          images={systemDescriptionImages}
          setImages={setSystemDescriptionImages}
          disabled={isAgentBusy}
        />
      </div>
      <div className="ia-section">
        <label htmlFor="ia-alerts">Security alerts and logs</label>
        <p className="ia-hint">
          Paste relevant security alerts, IDS logs, or other indicators of compromise.
        </p>
        <textarea
          id="ia-alerts"
          className="form-control ia-textarea"
          rows="8"
          value={securityAlerts}
          onChange={(e) => setSecurityAlerts(e.target.value)}
          onPaste={handlePaste(setSecurityAlertsImages)}
          disabled={isAgentBusy}
          placeholder="e.g., [ALERT] Brute-force SSH login detected on 10.0.0.1 from 192.168.1.50 (200 attempts in 5 min)..."
        />
        <ImageThumbnails
          images={securityAlertsImages}
          setImages={setSecurityAlertsImages}
          disabled={isAgentBusy}
        />
      </div>
      <div className="ia-section">
        <label htmlFor="ia-feedback">Operator input</label>
        <p className="ia-hint">
          Optionally provide additional context or instructions for the agent.
        </p>
        <textarea
          id="ia-feedback"
          className="form-control ia-textarea"
          rows="6"
          value={operatorFeedback}
          onChange={(e) => setOperatorFeedback(e.target.value)}
          onPaste={handlePaste(setOperatorFeedbackImages)}
          disabled={isAgentBusy}
          placeholder="e.g., The SSH brute force alert on server 3 likely led to a compromise, since the SQL injection originates from that host..."
        />
        <ImageThumbnails
          images={operatorFeedbackImages}
          setImages={setOperatorFeedbackImages}
          disabled={isAgentBusy}
        />
      </div>
      <button
        type="button"
        className="btn btn-dark btn-sm ia-btn"
        onClick={handleRun}
        disabled={isAgentBusy || (!systemDescription && !securityAlerts)}
      >
        <i className="fa fa-bolt" aria-hidden="true" />
        {isAgentBusy ? ' Running...' : ' Run agent'}
      </button>
      <button
        type="button"
        className="btn btn-outline-dark btn-sm ia-btn"
        onClick={fetchExample}
        disabled={isAgentBusy}
      >
        <i className="fa fa-download" aria-hidden="true" /> Fetch example incident
      </button>
      <button
        type="button"
        className="btn btn-outline-secondary btn-sm ia-btn"
        onClick={handleClear}
        disabled={isAgentBusy}
      >
        <i className="fa fa-eraser" aria-hidden="true" /> Clear all
      </button>
      <button
        type="button"
        className="btn btn-outline-dark btn-sm ia-btn"
        onClick={fetchPrompt}
        disabled={loadingPrompt}
      >
        <i className="fa fa-file-text-o" aria-hidden="true" />{' '}
        {loadingPrompt ? 'Loading...' : 'Show prompt'}
      </button>
      <span className="ia-model-label">LLM:</span>
      <select
        className="form-control form-control-sm ia-model-select"
        value={selectedModel}
        onChange={(e) => setSelectedModel(e.target.value)}
        disabled={isAgentBusy}
      >
        <option value="">Default (Gemini 3 Pro)</option>
        {models.map((m) => (
          <option key={m.name} value={m.name}>
            {m.display_name}
          </option>
        ))}
      </select>
      <div className="form-check form-check-inline ia-btn">
        <input
          className="form-check-input"
          type="checkbox"
          id="ia-autopilot"
          checked={autopilot}
          onChange={(e) => setAutopilot(e.target.checked)}
        />
        <label className="form-check-label" htmlFor="ia-autopilot">
          Autopilot <span className="ia-hint">(auto-approve all tool requests)</span>
        </label>
      </div>

      <PromptModal
        show={showPromptModal}
        promptText={promptText}
        onClose={() => setShowPromptModal(false)}
      />
    </div>
  )
}

export default InformationAgentConfigTab
