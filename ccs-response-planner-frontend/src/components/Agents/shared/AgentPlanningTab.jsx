import { useState } from 'react'
import AgentActivityLog from './AgentActivityLog.jsx'
import PromptModal from './PromptModal.jsx'

/**
 * Planning process tab — wraps AgentActivityLog.
 * Shows a placeholder when no conversation exists and the agent isn't running.
 */
function AgentPlanningTab({
  running,
  conversationHistory,
  expandedEntries,
  toggleEntry,
  pendingProposal,
  executingTool,
  handleApprove,
  handleDeny,
  contextUsage,
  hasNewActivity,
  scrollToBottom,
  logEndRef,
  streamingTraceRef,
  renderFinalReport,
  renderExecutingTool,
  renderToolResult,
  onStop,
  onViewPrompt,
  dtStatus,
  modelName
}) {
  const isAgentBusy = running || !!executingTool
  const [promptText, setPromptText] = useState('')
  const [showPrompt, setShowPrompt] = useState(false)
  const [loadingPrompt, setLoadingPrompt] = useState(false)

  const handleViewPrompt = async () => {
    if (!onViewPrompt) return
    setLoadingPrompt(true)
    try {
      const text = await onViewPrompt()
      if (text) {
        setPromptText(text)
        setShowPrompt(true)
      }
    } catch {
      /* ignore */
    } finally {
      setLoadingPrompt(false)
    }
  }

  if (conversationHistory.length === 0 && !running) {
    return (
      <p style={{ fontSize: '13px', color: '#6c757d', marginTop: '16px' }}>
        No activity yet. Configure and run the agent to see the planning process.
      </p>
    )
  }

  const showToolbar = isAgentBusy || onViewPrompt || modelName

  return (
    <>
      {dtStatus && running && conversationHistory.length === 0 && (
        <div
          style={{
            marginTop: '16px',
            padding: '10px 14px',
            background: '#f0f4ff',
            border: '1px solid #b8d0ff',
            borderRadius: '6px',
            fontSize: '13px',
            color: '#2c5282'
          }}
        >
          <i className="fa fa-refresh fa-spin" style={{ marginRight: '8px' }} />
          {dtStatus}
        </div>
      )}
      {showToolbar && (
        <div
          style={{
            marginTop: '12px',
            marginBottom: '-16px',
            textAlign: 'right',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            gap: '8px'
          }}
        >
          {modelName && (
            <span
              style={{
                fontSize: '11px',
                color: '#6c757d',
                marginRight: 'auto'
              }}
            >
              <i className="fa fa-microchip" aria-hidden="true" style={{ marginRight: '4px' }} />
              LLM: {modelName}
            </span>
          )}
          {onViewPrompt && (
            <button
              type="button"
              className="btn btn-outline-dark btn-sm"
              onClick={handleViewPrompt}
              disabled={loadingPrompt}
            >
              <i className="fa fa-file-text-o" aria-hidden="true" />{' '}
              {loadingPrompt ? 'Loading...' : 'Prompt'}
            </button>
          )}
          {isAgentBusy && onStop && (
            <button type="button" className="btn btn-outline-danger btn-sm" onClick={onStop}>
              <i className="fa fa-stop-circle" aria-hidden="true" /> Stop
            </button>
          )}
        </div>
      )}
      <AgentActivityLog
        conversationHistory={conversationHistory}
        expandedEntries={expandedEntries}
        toggleEntry={toggleEntry}
        pendingProposal={pendingProposal}
        executingTool={executingTool}
        handleApprove={handleApprove}
        handleDeny={handleDeny}
        contextUsage={contextUsage}
        hasNewActivity={hasNewActivity}
        scrollToBottom={scrollToBottom}
        logEndRef={logEndRef}
        streamingTraceRef={streamingTraceRef}
        renderFinalReport={renderFinalReport}
        renderExecutingTool={renderExecutingTool}
        renderToolResult={renderToolResult}
      />
      <PromptModal show={showPrompt} promptText={promptText} onClose={() => setShowPrompt(false)} />
    </>
  )
}

export default AgentPlanningTab
