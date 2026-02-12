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
  renderToolResult
}) {
  if (conversationHistory.length === 0 && !running) {
    return (
      <p style={{ fontSize: '13px', color: '#6c757d', marginTop: '16px' }}>
        No activity yet. Configure and run the agent to see the planning process.
      </p>
    )
  }

  return (
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
  )
}

export default AgentPlanningTab
