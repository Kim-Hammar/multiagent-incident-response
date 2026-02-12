import ReactMarkdown from 'react-markdown'
import ElapsedTimer from './ElapsedTimer.jsx'
import { formatToolArgs, toolLabel, toolIcon } from './toolUtils.js'

const TERMINAL_TOOLS = new Set([
  'dt_exec',
  'pentest_exec',
  'python_exec',
  'dt_python_exec',
  'rl_train'
])

function renderTerminalResult(toolName, result) {
  if (!result || typeof result !== 'object') return null

  if (toolName === 'gym_verify' && 'valid' in result) {
    return (
      <div className="ia-terminal-result">
        <div className="ia-terminal-meta">
          <span className={`badge badge-${result.valid ? 'success' : 'danger'}`}>
            {result.valid ? 'Valid' : 'Invalid'}
          </span>
        </div>
        {result.checks && result.checks.length > 0 && (
          <ul className="ia-gym-checks">
            {result.checks.map((check, i) => (
              <li key={i} className={check.passed ? 'passed' : 'failed'}>
                {check.passed ? '\u2713' : '\u2717'} {check.name || check.description || check}
              </li>
            ))}
          </ul>
        )}
        {result.error && <pre className="ia-terminal-output error">{result.error}</pre>}
      </div>
    )
  }

  if (!TERMINAL_TOOLS.has(toolName) || !('exit_code' in result)) return null

  return (
    <div className="ia-terminal-result">
      <div className="ia-terminal-meta">
        {result.container && (
          <span className="ia-terminal-container">
            <i className="fa fa-server" aria-hidden="true" /> {result.container}
          </span>
        )}
        <span className={`badge badge-${result.exit_code === 0 ? 'success' : 'danger'}`}>
          exit {result.exit_code}
        </span>
      </div>
      {result.output != null && result.output !== '' ? (
        <pre className="ia-terminal-output">{result.output}</pre>
      ) : (
        <span className="ia-terminal-empty">(no output)</span>
      )}
    </div>
  )
}

/**
 * Shared activity log component for all agents.
 * Uses a render prop (renderFinalReport) for the agent-specific final report entry.
 */
function AgentActivityLog({
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
  return (
    <div style={{ marginTop: '28px' }}>
      <div className="ia-log-header">
        <p className="ia-log-title">Activity log</p>
        {contextUsage && (
          <span
            className={`ia-context-indicator${contextUsage.total_tokens / contextUsage.context_limit > 0.8 ? ' high-usage' : ''}`}
          >
            Context management: {contextUsage.total_tokens.toLocaleString()} /{' '}
            {contextUsage.context_limit.toLocaleString()} tokens (
            {Math.round((contextUsage.total_tokens / contextUsage.context_limit) * 100)}%)
          </span>
        )}
      </div>
      <div className="ia-log">
        {conversationHistory.map((entry, index) => {
          if (entry.type === 'streaming') {
            return (
              <div key={index} className="card ia-entry ia-streaming-entry">
                <div className="card-body">
                  <div className="ia-thinking-header">
                    <div className="spinner-border spinner-border-sm" role="status">
                      <span className="sr-only">Loading...</span>
                    </div>
                    <span className="ia-thinking-title">Agent is thinking...</span>
                    <ElapsedTimer />
                  </div>
                  {entry.text && (
                    <div className="ia-streaming-trace" ref={streamingTraceRef}>
                      <ReactMarkdown>{entry.text}</ReactMarkdown>
                    </div>
                  )}
                </div>
              </div>
            )
          }

          if (entry.type === 'reasoning') {
            const isExpanded = expandedEntries[index]
            return (
              <div key={index} className="card ia-entry ia-reasoning-entry">
                <div className="card-body">
                  <div className="ia-reasoning-header" onClick={() => toggleEntry(index)}>
                    <i className="fa fa-lightbulb-o" aria-hidden="true" />
                    <span className="ia-reasoning-label">Agent reasoning</span>
                    <span className="ia-toggle-hint">{isExpanded ? 'collapse' : 'expand'}</span>
                  </div>
                  {isExpanded && (
                    <div className="ia-thinking-trace">
                      <ReactMarkdown>{entry.text}</ReactMarkdown>
                    </div>
                  )}
                </div>
              </div>
            )
          }

          if (entry.type === 'tool_proposal') {
            const isCurrentPending = pendingProposal && index === conversationHistory.length - 1
            const isExpanded = isCurrentPending || expandedEntries[index]
            const argPairs = formatToolArgs(entry.tool_name, entry.tool_args)
            return (
              <div key={index} className="card ia-entry ia-proposal-entry">
                <div className="card-body">
                  <div
                    className="ia-proposal-header"
                    onClick={!isCurrentPending ? () => toggleEntry(index) : undefined}
                  >
                    <i className={`fa ${toolIcon(entry.tool_name)}`} aria-hidden="true" />
                    <span className="ia-proposal-label">
                      {isCurrentPending ? 'The agent wants to call tool' : 'Called tool'}
                    </span>
                    <span className="ia-proposal-tool-inline">{toolLabel(entry.tool_name)}</span>
                    {!isCurrentPending && (
                      <span className="ia-toggle-hint">{isExpanded ? 'collapse' : 'expand'}</span>
                    )}
                  </div>
                  {isExpanded && (
                    <div className="ia-proposal-details">
                      <div className="ia-proposal-tool">Tool: {toolLabel(entry.tool_name)}</div>
                      {argPairs.map(([label, value], i) => (
                        <div key={i} className="ia-proposal-arg-row">
                          <span className="ia-proposal-arg-label">{label}:</span>
                          <span className="ia-proposal-arg-value">{value}</span>
                        </div>
                      ))}
                      {isCurrentPending && (
                        <div className="ia-proposal-actions">
                          <button
                            type="button"
                            className="btn btn-dark btn-sm"
                            onClick={handleApprove}
                            disabled={executingTool}
                          >
                            {executingTool ? 'Executing...' : 'Approve'}
                          </button>
                          <button
                            type="button"
                            className="btn btn-outline-secondary btn-sm"
                            onClick={handleDeny}
                            disabled={executingTool}
                          >
                            Deny
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )
          }

          if (entry.type === 'tool_approval') {
            return (
              <div key={index} className="card ia-entry ia-approval-entry">
                <div className="card-body">
                  <div className="ia-entry-header">
                    <span className={`badge badge-${entry.approved ? 'success' : 'danger'}`}>
                      {entry.approved ? 'Approved' : 'Denied'}
                    </span>
                    <span className="ia-approval-tool">{toolLabel(entry.tool_name)}</span>
                  </div>
                </div>
              </div>
            )
          }

          if (entry.type === 'tool_result') {
            const isExpanded = expandedEntries[index]
            const hasImage = entry.result?.image
            const customRender = renderToolResult && renderToolResult(entry)
            const displayResult = hasImage
              ? { status: 'success', message: 'Attack path image generated successfully' }
              : entry.result
            return (
              <div key={index} className="card ia-entry ia-result-entry">
                <div className="card-body">
                  <div className="ia-result-header" onClick={() => toggleEntry(index)}>
                    <i className={`fa ${toolIcon(entry.tool_name)}`} aria-hidden="true" />
                    <span className="ia-result-label">{toolLabel(entry.tool_name)} result</span>
                    <span className="ia-toggle-hint">{isExpanded ? 'collapse' : 'expand'}</span>
                  </div>
                  {isExpanded &&
                    (customRender || renderTerminalResult(entry.tool_name, displayResult) || (
                      <>
                        <pre className="ia-result-data mb-0">
                          {JSON.stringify(displayResult, null, 2)}
                        </pre>
                        {hasImage && (
                          <img
                            src={entry.result.image}
                            alt="Generated attack path"
                            style={{
                              maxWidth: '100%',
                              border: '1px solid #dee2e6',
                              borderRadius: '4px',
                              marginTop: '8px'
                            }}
                          />
                        )}
                      </>
                    ))}
                </div>
              </div>
            )
          }

          if (entry.type === 'error') {
            return (
              <div key={index} className="card ia-entry border-danger">
                <div className="card-body">
                  <div className="ia-entry-header">
                    <span className="badge badge-danger">Error</span>
                    <span className="ia-tool-name">Agent step failed</span>
                  </div>
                  <p className="ia-error-message mb-0">{entry.message}</p>
                </div>
              </div>
            )
          }

          if (renderFinalReport) {
            return renderFinalReport(entry, index, expandedEntries[index] !== false)
          }

          return null
        })}
        {executingTool &&
          (renderExecutingTool && renderExecutingTool(executingTool) ? (
            renderExecutingTool(executingTool)
          ) : (
            <div className="card ia-entry ia-streaming-entry">
              <div className="card-body">
                <div className="ia-thinking-header">
                  <div className="spinner-border spinner-border-sm" role="status">
                    <span className="sr-only">Loading...</span>
                  </div>
                  <i className={`fa ${toolIcon(executingTool)}`} aria-hidden="true" />
                  <span className="ia-thinking-title">Executing {toolLabel(executingTool)}...</span>
                </div>
              </div>
            </div>
          ))}
        <div ref={logEndRef} />
        {hasNewActivity && (
          <button type="button" className="ia-new-activity-btn" onClick={scrollToBottom}>
            <i className="fa fa-arrow-down" aria-hidden="true" /> New activity
          </button>
        )}
      </div>
    </div>
  )
}

export default AgentActivityLog
