import ImageThumbnails from './shared/ImageThumbnails.jsx'
import PromptModal from './shared/PromptModal.jsx'
import ExampleSelector from './shared/ExampleSelector.jsx'

/**
 * Configuration tab for the Code Agent.
 */
function CodeAgentConfigTab({
  systemDescription,
  setSystemDescription,
  incidentReport,
  setIncidentReport,
  specification,
  setSpecification,
  operatorFeedback,
  setOperatorFeedback,
  systemDescriptionImages,
  setSystemDescriptionImages,
  handlePaste,
  isAgentBusy,
  handleRun,
  loadExample,
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
          This agent generates a Gymnasium-standard RL environment (MDP) for computing optimal
          incident response plans. Its tasks are threefold:
          <ol>
            <li>
              Analyze the system description, incident report, and specification to design actions
              with realistic stochastic transitions and contingencies.
            </li>
            <li>
              Generate and iteratively test Python code implementing the Gymnasium environment in a
              sandbox.
            </li>
            <li>Verify the environment passes all Gymnasium checks and produce a code report.</li>
          </ol>
        </p>
      </div>

      <div className="ia-section">
        <label htmlFor="ca-system-desc">System description</label>
        <p className="ia-hint">
          Describe the target system, its architecture, hosts, and services.
        </p>
        <textarea
          id="ca-system-desc"
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
        <label htmlFor="ca-incident-report">Incident report</label>
        <p className="ia-hint">
          Paste the incident report/assessment produced by the Information Agent.
        </p>
        <textarea
          id="ca-incident-report"
          className="form-control ia-textarea"
          rows="6"
          value={incidentReport}
          onChange={(e) => setIncidentReport(e.target.value)}
          disabled={isAgentBusy}
          placeholder="e.g., An SSH brute-force attack was detected on server 3, followed by SQL injection from server 6..."
        />
      </div>
      <div className="ia-section">
        <label htmlFor="ca-specification">Specification commands</label>
        <p className="ia-hint">
          JSON array of specification commands that define service-level requirements of the system.
        </p>
        <textarea
          id="ca-specification"
          className="form-control ia-textarea"
          rows="4"
          value={specification}
          onChange={(e) => setSpecification(e.target.value)}
          disabled={isAgentBusy}
          placeholder="Leave empty to use default specification commands from the digital twin config."
        />
      </div>
      <div className="ia-section">
        <label htmlFor="ca-operator-feedback">Operator feedback (optional)</label>
        <p className="ia-hint">
          Additional guidance or constraints for the MDP environment design.
        </p>
        <textarea
          id="ca-operator-feedback"
          className="form-control ia-textarea"
          rows="4"
          value={operatorFeedback}
          onChange={(e) => setOperatorFeedback(e.target.value)}
          disabled={isAgentBusy}
          placeholder="e.g., Focus on containment actions first. The firewall rules should be the first actions."
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
          id="ca-autopilot"
          checked={autopilot}
          onChange={(e) => setAutopilot(e.target.checked)}
        />
        <label className="form-check-label" htmlFor="ca-autopilot">
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

export default CodeAgentConfigTab
