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
  logContainerRef,
  logEndRef,
  streamingTraceRef,
  handleLogScroll,
  renderFinalReport
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
      logContainerRef={logContainerRef}
      logEndRef={logEndRef}
      streamingTraceRef={streamingTraceRef}
      handleLogScroll={handleLogScroll}
      renderFinalReport={renderFinalReport}
    />
  )
}

export default AgentPlanningTab
