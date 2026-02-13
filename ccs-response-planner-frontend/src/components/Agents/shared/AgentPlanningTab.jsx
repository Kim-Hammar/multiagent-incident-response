import AgentActivityLog from './AgentActivityLog.jsx'

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
  dtStatus
}) {
  const isAgentBusy = running || !!executingTool

  if (conversationHistory.length === 0 && !running) {
    return (
      <p style={{ fontSize: '13px', color: '#6c757d', marginTop: '16px' }}>
        No activity yet. Configure and run the agent to see the planning process.
      </p>
    )
  }

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
      {isAgentBusy && onStop && (
        <div style={{ marginTop: '12px', marginBottom: '-16px', textAlign: 'right' }}>
          <button type="button" className="btn btn-outline-danger btn-sm" onClick={onStop}>
            <i className="fa fa-stop-circle" aria-hidden="true" /> Stop
          </button>
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
    </>
  )
}

export default AgentPlanningTab
