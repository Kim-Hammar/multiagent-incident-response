import { useState } from 'react'
import AgentActivityLog from './AgentActivityLog.jsx'
import ContextModal from './ContextModal.jsx'
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
  onClear,
  onViewPrompt,
  dtStatus,
  modelName,
  livenessStatus,
  lastHeartbeatTime,
  heartbeatStatus
}) {
  const isAgentBusy = running || !!executingTool
  const [promptText, setPromptText] = useState('')
  const [promptImages, setPromptImages] = useState([])
  const [showPrompt, setShowPrompt] = useState(false)
  const [showContext, setShowContext] = useState(false)
  const [loadingPrompt, setLoadingPrompt] = useState(false)

  const handleViewPrompt = async () => {
    if (!onViewPrompt) return
    setLoadingPrompt(true)
    try {
      const result = await onViewPrompt()
      if (result) {
        if (typeof result === 'object' && result.text !== undefined) {
          setPromptText(result.text)
          setPromptImages(result.images || [])
        } else {
          setPromptText(result)
          setPromptImages([])
        }
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

  const showToolbar = isAgentBusy || onViewPrompt || modelName || conversationHistory.length > 0

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
          {conversationHistory.length > 0 && (
            <button
              type="button"
              className="btn btn-outline-dark btn-sm"
              onClick={() => setShowContext(true)}
            >
              <i className="fa fa-database" aria-hidden="true" /> Context
            </button>
          )}
          {isAgentBusy && onStop && (
            <button type="button" className="btn btn-outline-danger btn-sm" onClick={onStop}>
              <i className="fa fa-stop-circle" aria-hidden="true" /> Stop
            </button>
          )}
          {!isAgentBusy && conversationHistory.length > 0 && onClear && (
            <button type="button" className="btn btn-outline-secondary btn-sm" onClick={onClear}>
              <i className="fa fa-eraser" aria-hidden="true" /> Clear
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
        livenessStatus={livenessStatus}
        lastHeartbeatTime={lastHeartbeatTime}
        heartbeatStatus={heartbeatStatus}
      />
      <PromptModal
        show={showPrompt}
        promptText={promptText}
        promptImages={promptImages}
        onClose={() => setShowPrompt(false)}
      />
      <ContextModal
        show={showContext}
        conversationHistory={conversationHistory
          .filter((e) => e.type !== 'tool_streaming')
          .map((e) => {
            if (e.type === 'tool_result' && e.result?.image) {
              return {
                role: e.role,
                type: e.type,
                tool_name: e.tool_name,
                result: { status: 'success', message: 'Image generated (excluded from context)' }
              }
            }
            if (e.type === 'tool_result') {
              return { role: e.role, type: e.type, tool_name: e.tool_name, result: e.result }
            }
            return e
          })}
        onClose={() => setShowContext(false)}
      />
    </>
  )
}

export default AgentPlanningTab
