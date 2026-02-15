/**
 * Modal dialog that displays the system prompt text.
 */
function PromptModal({ show, promptText, promptImages, onClose }) {
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
          {promptImages?.length > 0 && (
            <div style={{ marginBottom: '12px' }}>
              <strong style={{ fontSize: '12px' }}>Attached Images ({promptImages.length})</strong>
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '8px',
                  marginTop: '6px'
                }}
              >
                {promptImages.map((src, i) => (
                  <img
                    key={i}
                    src={src}
                    alt={`Attached ${i + 1}`}
                    style={{
                      maxWidth: '200px',
                      maxHeight: '150px',
                      border: '1px solid #dee2e6',
                      borderRadius: '4px'
                    }}
                  />
                ))}
              </div>
            </div>
          )}
          <pre className="ia-prompt-text">{promptText}</pre>
        </div>
      </div>
    </div>
  )
}

export default PromptModal
