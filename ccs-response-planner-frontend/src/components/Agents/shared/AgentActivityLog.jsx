import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import ElapsedTimer from './ElapsedTimer.jsx'
import PromptModal from './PromptModal.jsx'
import { formatToolArgs, toolLabel, toolIcon } from './toolUtils.js'

const ORCHESTRATOR_TOOLS = new Set([
  'run_code_agent',
  'run_code_reviewer_agent',
  'produce_orchestrator_report'
])

/**
 * A collapsible section with a clickable header.
 */
function CollapsibleSection({ label, icon, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="ia-collapsible-section">
      <div className="ia-collapsible-header" onClick={() => setOpen(!open)}>
        <i className={`fa ${open ? 'fa-chevron-down' : 'fa-chevron-right'}`} aria-hidden="true" />
        {icon && <i className={`fa ${icon}`} aria-hidden="true" />}
        <span>{label}</span>
        <span className="ia-toggle-hint">{open ? 'collapse' : 'expand'}</span>
      </div>
      {open && <div className="ia-collapsible-content">{children}</div>}
    </div>
  )
}

/**
 * Render structured, collapsible args for orchestrator sub-agent tools.
 */
function renderOrchestratorArgs(toolName, args) {
  if (toolName === 'run_code_agent') {
    if (!args?.previous_code && !args?.review_feedback) {
      return (
        <div className="ia-orchestrator-args">
          <div className="ia-orchestrator-note">
            <i className="fa fa-info-circle" aria-hidden="true" />
            <span>Initial code generation — no prior code or review feedback</span>
          </div>
        </div>
      )
    }
    return (
      <div className="ia-orchestrator-args">
        {args.review_feedback && (
          <CollapsibleSection label="Review Feedback" icon="fa-comments">
            <div className="ia-arg-markdown">
              <ReactMarkdown>{args.review_feedback}</ReactMarkdown>
            </div>
          </CollapsibleSection>
        )}
        {args.previous_code && (
          <CollapsibleSection label="Previous Code" icon="fa-code">
            <pre className="ia-arg-code">{args.previous_code}</pre>
          </CollapsibleSection>
        )}
      </div>
    )
  }

  if (toolName === 'run_code_reviewer_agent') {
    return (
      <div className="ia-orchestrator-args">
        <div className="ia-orchestrator-note">
          <i className="fa fa-info-circle" aria-hidden="true" />
          <span>Code report extracted from conversation history</span>
        </div>
      </div>
    )
  }

  if (toolName === 'produce_orchestrator_report') {
    return (
      <div className="ia-orchestrator-args">
        {args.final_verdict && (
          <div className="ia-orchestrator-verdict-row">
            <span className="ia-proposal-arg-label">Verdict:</span>
            <span
              className={`badge badge-${args.final_verdict === 'pass' ? 'success' : args.final_verdict === 'major_issues' ? 'danger' : 'warning'}`}
            >
              {args.final_verdict}
            </span>
          </div>
        )}
        {args.iterations != null && (
          <div className="ia-orchestrator-verdict-row">
            <span className="ia-proposal-arg-label">Iterations:</span>
            <span className="ia-proposal-arg-value">{args.iterations}</span>
          </div>
        )}
        {args.executive_summary && (
          <CollapsibleSection label="Executive Summary" icon="fa-file-text" defaultOpen>
            <div className="ia-arg-markdown">
              <ReactMarkdown>{args.executive_summary}</ReactMarkdown>
            </div>
          </CollapsibleSection>
        )}
        {args.code_report_summary && (
          <CollapsibleSection label="Code Report Summary" icon="fa-code">
            <div className="ia-arg-markdown">
              <ReactMarkdown>{args.code_report_summary}</ReactMarkdown>
            </div>
          </CollapsibleSection>
        )}
        {args.review_report_summary && (
          <CollapsibleSection label="Review Report Summary" icon="fa-search">
            <div className="ia-arg-markdown">
              <ReactMarkdown>{args.review_report_summary}</ReactMarkdown>
            </div>
          </CollapsibleSection>
        )}
      </div>
    )
  }

  return null
}

const TERMINAL_TOOLS = new Set([
  'dt_exec',
  'pentest_exec',
  'python_exec',
  'dt_python_exec',
  'rl_train',
  'dp_solve'
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
                {check.passed ? '\u2713' : '\u2717'}{' '}
                {check.name ||
                  check.description ||
                  check.check ||
                  check.detail ||
                  (typeof check === 'string' ? check : JSON.stringify(check))}
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
 * Render sub-agent activity events inside a nested container.
 */
function SubAgentLog({ subEvents, agentLabel, active, modelName }) {
  const [expanded, setExpanded] = useState({})
  const toggle = (i) => setExpanded((prev) => ({ ...prev, [i]: !prev[i] }))

  if (!subEvents || subEvents.length === 0) return null

  const lastIndex = subEvents.length - 1

  return (
    <div className="ia-sub-agent-log">
      <div className="ia-sub-agent-header">
        <i className="fa fa-sitemap" aria-hidden="true" />
        <span>{agentLabel} activity</span>
        {modelName && (
          <span style={{ fontSize: '10px', color: '#888', marginLeft: '8px' }}>
            <i className="fa fa-microchip" aria-hidden="true" /> {modelName}
          </span>
        )}
      </div>
      {subEvents.map((ev, i) => {
        const isLast = active && i === lastIndex
        if (ev.type === 'reasoning') {
          const isOpen = !!expanded[i]
          return (
            <div key={i} className="ia-sub-entry ia-sub-reasoning">
              <div className="ia-sub-entry-header" onClick={() => toggle(i)}>
                {isLast && (
                  <>
                    <div className="spinner-border spinner-border-sm" role="status">
                      <span className="sr-only">Loading...</span>
                    </div>
                    <ElapsedTimer />
                  </>
                )}
                <i className="fa fa-lightbulb-o" aria-hidden="true" />
                <span>Agent reasoning</span>
                <span className="ia-toggle-hint">{isOpen ? 'collapse' : 'expand'}</span>
              </div>
              {isOpen && (
                <div className="ia-thinking-trace">
                  <ReactMarkdown>{ev.text}</ReactMarkdown>
                </div>
              )}
            </div>
          )
        }
        if (ev.type === 'text') {
          const isOpen = !!expanded[i]
          return (
            <div key={i} className="ia-sub-entry ia-sub-text">
              <div className="ia-sub-entry-header" onClick={() => toggle(i)}>
                {isLast && (
                  <>
                    <div className="spinner-border spinner-border-sm" role="status">
                      <span className="sr-only">Loading...</span>
                    </div>
                    <ElapsedTimer />
                  </>
                )}
                <i className="fa fa-comment-o" aria-hidden="true" />
                <span>Agent output</span>
                <span className="ia-toggle-hint">{isOpen ? 'collapse' : 'expand'}</span>
              </div>
              {isOpen && (
                <div className="ia-thinking-trace">
                  <ReactMarkdown>{ev.text}</ReactMarkdown>
                </div>
              )}
            </div>
          )
        }
        if (ev.type === 'tool_call') {
          const isOpen = !!expanded[i]
          const argPairs = formatToolArgs(ev.tool_name, ev.tool_args)
          return (
            <div key={i} className="ia-sub-entry ia-sub-tool-call">
              <div className="ia-sub-entry-header" onClick={() => toggle(i)}>
                {isLast && (
                  <>
                    <div className="spinner-border spinner-border-sm" role="status">
                      <span className="sr-only">Loading...</span>
                    </div>
                    <ElapsedTimer />
                  </>
                )}
                <i className={`fa ${toolIcon(ev.tool_name)}`} aria-hidden="true" />
                <span>Running {toolLabel(ev.tool_name)}</span>
                <span className="ia-toggle-hint">{isOpen ? 'collapse' : 'expand'}</span>
              </div>
              {isOpen && (
                <div className="ia-proposal-details">
                  {argPairs.map(([label, value], j) => (
                    <div key={j} className="ia-proposal-arg-row">
                      <span className="ia-proposal-arg-label">{label}:</span>
                      <span className="ia-proposal-arg-value">{value}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        }
        if (ev.type === 'tool_result') {
          const isOpen = !!expanded[i]
          const terminal = renderTerminalResult(ev.tool_name, ev.result)
          return (
            <div key={i} className="ia-sub-entry ia-sub-tool-result">
              <div className="ia-sub-entry-header" onClick={() => toggle(i)}>
                <i className={`fa ${toolIcon(ev.tool_name)}`} aria-hidden="true" />
                <span>{toolLabel(ev.tool_name)} result</span>
                {ev.result && 'exit_code' in ev.result && (
                  <span
                    className={`badge badge-${ev.result.exit_code === 0 ? 'success' : 'danger'} ml-2`}
                  >
                    exit {ev.result.exit_code}
                  </span>
                )}
                <span className="ia-toggle-hint">{isOpen ? 'collapse' : 'expand'}</span>
              </div>
              {isOpen &&
                (terminal || (
                  <pre className="ia-result-data mb-0">{JSON.stringify(ev.result, null, 2)}</pre>
                ))}
            </div>
          )
        }
        if (ev.type === 'report') {
          return (
            <div key={i} className="ia-sub-entry ia-sub-report">
              <i className="fa fa-check-circle" aria-hidden="true" />
              <span>Report produced</span>
            </div>
          )
        }
        return null
      })}
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
  const [promptModalText, setPromptModalText] = useState(null)
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
            const isOrchTool = ORCHESTRATOR_TOOLS.has(entry.tool_name)
            const argPairs = isOrchTool ? null : formatToolArgs(entry.tool_name, entry.tool_args)
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
                      {isOrchTool
                        ? renderOrchestratorArgs(entry.tool_name, entry.tool_args)
                        : argPairs.map(([label, value], i) => (
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

          if (entry.type === 'tool_streaming') {
            const hasSubEvents = entry.subEvents && entry.subEvents.length > 0
            const isOpen = !!expandedEntries[index]
            const agentLabel =
              entry.tool_name === 'run_code_reviewer_agent' ? 'Code Reviewer Agent' : 'Code Agent'
            return (
              <div
                key={index}
                className={`card ia-entry ${entry.stopped ? 'ia-result-entry' : 'ia-streaming-entry'}`}
              >
                <div className="card-body">
                  <div
                    className="ia-thinking-header"
                    style={{ cursor: 'pointer' }}
                    onClick={() => toggleEntry(index)}
                  >
                    {entry.stopped ? (
                      <span className="badge badge-secondary">Stopped</span>
                    ) : (
                      <>
                        <div className="spinner-border spinner-border-sm" role="status">
                          <span className="sr-only">Loading...</span>
                        </div>
                        <ElapsedTimer />
                      </>
                    )}
                    <i className={`fa ${toolIcon(entry.tool_name)}`} aria-hidden="true" />
                    <span className="ia-thinking-title">
                      {entry.stopped
                        ? toolLabel(entry.tool_name)
                        : `Executing ${toolLabel(entry.tool_name)}...`}
                    </span>
                    {entry._modelName && (
                      <span style={{ fontSize: '10px', color: '#888', marginLeft: '6px' }}>
                        <i className="fa fa-microchip" aria-hidden="true" /> {entry._modelName}
                      </span>
                    )}
                    <span className="ia-toggle-hint">{isOpen ? 'collapse' : 'expand'}</span>
                  </div>
                  {isOpen && (
                    <>
                      {entry.prompt && (
                        <button
                          type="button"
                          className="btn btn-outline-dark btn-sm"
                          style={{ fontSize: '11px', padding: '2px 10px', marginTop: '8px' }}
                          onClick={(e) => {
                            e.stopPropagation()
                            setPromptModalText(entry.prompt)
                          }}
                        >
                          <i className="fa fa-file-text-o" aria-hidden="true" /> View prompt
                        </button>
                      )}
                      {hasSubEvents ? (
                        <SubAgentLog
                          subEvents={entry.subEvents}
                          agentLabel={agentLabel}
                          active={!entry.stopped}
                          modelName={entry._modelName}
                        />
                      ) : (
                        entry.output && (
                          <pre
                            className="ia-terminal-output"
                            style={{ maxHeight: '400px', overflow: 'auto' }}
                          >
                            {entry.output}
                          </pre>
                        )
                      )}
                    </>
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
            const hasSubEvents = entry.subEvents && entry.subEvents.length > 0
            const agentLabel =
              entry.tool_name === 'run_code_reviewer_agent'
                ? 'Code Reviewer Agent'
                : entry.tool_name === 'run_code_agent'
                  ? 'Code Agent'
                  : null
            return (
              <div key={index} className="card ia-entry ia-result-entry">
                <div className="card-body">
                  <div className="ia-result-header" onClick={() => toggleEntry(index)}>
                    <i className={`fa ${toolIcon(entry.tool_name)}`} aria-hidden="true" />
                    <span className="ia-result-label">{toolLabel(entry.tool_name)} result</span>
                    {entry._modelName && (
                      <span style={{ fontSize: '10px', color: '#888', marginLeft: '6px' }}>
                        <i className="fa fa-microchip" aria-hidden="true" /> {entry._modelName}
                      </span>
                    )}
                    <span className="ia-toggle-hint">{isExpanded ? 'collapse' : 'expand'}</span>
                  </div>
                  {isExpanded && (
                    <>
                      {customRender || renderTerminalResult(entry.tool_name, displayResult) || (
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
                      )}
                      {hasSubEvents && (
                        <CollapsibleSection
                          label={`${agentLabel || 'Agent'} planning process`}
                          icon="fa-sitemap"
                        >
                          {entry.prompt && (
                            <button
                              type="button"
                              className="btn btn-outline-dark btn-sm"
                              style={{
                                fontSize: '11px',
                                padding: '2px 10px',
                                marginBottom: '8px'
                              }}
                              onClick={() => setPromptModalText(entry.prompt)}
                            >
                              <i className="fa fa-file-text-o" aria-hidden="true" /> View prompt
                            </button>
                          )}
                          <SubAgentLog
                            subEvents={entry.subEvents}
                            agentLabel={agentLabel}
                            modelName={entry._modelName}
                          />
                        </CollapsibleSection>
                      )}
                    </>
                  )}
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
            return renderFinalReport(entry, index, !!expandedEntries[index])
          }

          return null
        })}
        {executingTool &&
          !conversationHistory.some((e) => e.type === 'tool_streaming') &&
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
                  <ElapsedTimer />
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
      <PromptModal
        show={!!promptModalText}
        promptText={promptModalText || ''}
        onClose={() => setPromptModalText(null)}
      />
    </div>
  )
}

export default AgentActivityLog
