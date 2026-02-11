/**
 * Modal dialog that displays the system prompt text.
 */
function PromptModal({ show, promptText, onClose }) {
  if (!show) return null

  return (
    <div className="ia-modal-backdrop" onClick={onClose}>
      <div className="ia-modal" onClick={(e) => e.stopPropagation()}>
        <div className="ia-modal-header">
          <span className="ia-modal-title">System Prompt</span>
          <button type="button" className="close" aria-label="Close" onClick={onClose}>
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <div className="ia-modal-body">
          <pre className="ia-prompt-text">{promptText}</pre>
        </div>
      </div>
    </div>
  )
}

export default PromptModal
