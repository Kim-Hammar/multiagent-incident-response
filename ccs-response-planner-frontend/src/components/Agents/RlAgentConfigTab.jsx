import ImageThumbnails from './shared/ImageThumbnails.jsx'
import PromptModal from './shared/PromptModal.jsx'
import ExampleSelector from './shared/ExampleSelector.jsx'

/**
 * Configuration tab for the RL Agent.
 */
function RlAgentConfigTab({
  systemDescription,
  setSystemDescription,
  incidentReport,
  setIncidentReport,
  specification,
  setSpecification,
  operatorFeedback,
  setOperatorFeedback,
  codeReport,
  setCodeReport,
  timeLimitMinutes,
  setTimeLimitMinutes,
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
        <label htmlFor="mdp-specification">Specification commands</label>
        <p className="ia-hint">
          JSON array of specification commands that define service-level requirements of the target
          system.
        </p>
        <textarea
          id="mdp-specification"
          className="form-control ia-textarea"
          rows="4"
          value={specification}
          onChange={(e) => setSpecification(e.target.value)}
          disabled={isAgentBusy}
          placeholder="Leave empty to use default specification commands from the digital twin config."
        />
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
      <div className="ia-section">
        <label htmlFor="mdp-time-limit">Training time limit (minutes)</label>
        <p className="ia-hint">
          Maximum wall-clock time for RL training. Training stops when this limit is reached.
        </p>
        <input
          id="mdp-time-limit"
          type="number"
          className="form-control form-control-sm"
          style={{ width: '120px' }}
          min="1"
          max="60"
          value={timeLimitMinutes}
          onChange={(e) => setTimeLimitMinutes(Math.max(1, Math.min(60, Number(e.target.value))))}
          disabled={isAgentBusy}
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
          id="mdp-autopilot"
          checked={autopilot}
          onChange={(e) => setAutopilot(e.target.checked)}
        />
        <label className="form-check-label" htmlFor="mdp-autopilot">
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

export default RlAgentConfigTab
