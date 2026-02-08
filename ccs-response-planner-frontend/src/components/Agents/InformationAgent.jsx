import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../../contexts/AuthContext.jsx'
import {
  API_EXAMPLE_URL,
  API_AGENTS_INFO_STEP_URL,
  API_AGENTS_INFO_TOOL_URL,
  API_AGENTS_INFO_PROMPT_URL
} from '../Common/constants'

/**
 * InformationAgent component — drives the agent loop with
 * human-in-the-loop tool approval.
 */
function InformationAgent() {
  const { token, logout } = useAuth()
  const [systemDescription, setSystemDescription] = useState('')
  const [securityAlerts, setSecurityAlerts] = useState('')
  const [operatorFeedback, setOperatorFeedback] = useState('')
  const [recoveryContext, setRecoveryContext] = useState('')
  const [conversationHistory, setConversationHistory] = useState([])
  const [running, setRunning] = useState(false)
  const [executingTool, setExecutingTool] = useState(false)
  const [pendingProposal, setPendingProposal] = useState(null)
  const [alert, setAlert] = useState(null)
  const [expandedResults, setExpandedResults] = useState({})
  const [showPromptModal, setShowPromptModal] = useState(false)
  const [promptText, setPromptText] = useState('')
  const [loadingPrompt, setLoadingPrompt] = useState(false)
  const logEndRef = useRef(null)

  useEffect(() => {
    if (!alert) return
    const timer = setTimeout(() => setAlert(null), 3000)
    return () => clearTimeout(timer)
  }, [alert])

  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [conversationHistory])

  const callStep = async (history) => {
    setRunning(true)
    const streamingIdx = history.length
    const streamingEntry = { role: 'model', type: 'streaming', text: '' }
    setConversationHistory([...history, streamingEntry])
    try {
      const res = await fetch(API_AGENTS_INFO_STEP_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          system_description: systemDescription,
          security_alerts: securityAlerts,
          operator_feedback: operatorFeedback,
          recovery_context: recoveryContext,
          conversation_history: history
        })
      })
      if (res.status === 401) {
        logout()
        return
      }
      if (!res.ok) {
        const data = await res.json()
        setAlert({ type: 'danger', message: data.error || 'Agent step failed' })
        setConversationHistory(history)
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let accumulated = ''
      let finalEntry = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()
        for (const line of lines) {
          if (!line.trim()) continue
          const event = JSON.parse(line)
          if (event.type === 'text') {
            accumulated += event.delta
            setConversationHistory((prev) => {
              const next = [...prev]
              next[streamingIdx] = { ...next[streamingIdx], text: accumulated }
              return next
            })
          } else if (event.type === 'tool_proposal') {
            finalEntry = {
              role: 'model',
              type: 'tool_proposal',
              tool_name: event.tool_name,
              tool_args: event.tool_args,
              rationale: event.rationale
            }
          } else if (event.type === 'assessment') {
            finalEntry = { role: 'model', type: 'assessment', content: event.content }
          } else if (event.type === 'error') {
            setAlert({ type: 'danger', message: event.message || 'Agent stream error' })
            setConversationHistory(history)
            return
          }
        }
      }

      if (finalEntry) {
        const updated = [...history, finalEntry]
        setConversationHistory(updated)
        if (finalEntry.type === 'tool_proposal') {
          setPendingProposal(finalEntry)
        }
      } else if (accumulated) {
        setConversationHistory([
          ...history,
          { role: 'model', type: 'assessment', content: accumulated }
        ])
      } else {
        setConversationHistory(history)
      }
    } catch (err) {
      setAlert({ type: 'danger', message: `Agent error: ${err.message}` })
      setConversationHistory(history)
    } finally {
      setRunning(false)
    }
  }

  const handleRun = () => {
    setPendingProposal(null)
    setConversationHistory([])
    callStep([])
  }

  const handleApprove = async () => {
    if (!pendingProposal) return
    const approvalEntry = {
      role: 'user',
      type: 'tool_approval',
      tool_name: pendingProposal.tool_name,
      approved: true
    }
    setPendingProposal(null)
    setExecutingTool(true)
    try {
      const res = await fetch(API_AGENTS_INFO_TOOL_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          tool_name: pendingProposal.tool_name,
          tool_args: pendingProposal.tool_args
        })
      })
      if (res.status === 401) {
        logout()
        return
      }
      const data = await res.json()
      const resultEntry = {
        role: 'tool',
        type: 'tool_result',
        tool_name: pendingProposal.tool_name,
        result: data.error ? { error: data.error } : data.result
      }
      const updated = [...conversationHistory, approvalEntry, resultEntry]
      setConversationHistory(updated)
      setExecutingTool(false)
      callStep(updated)
    } catch (err) {
      setAlert({ type: 'danger', message: `Tool execution error: ${err.message}` })
      setExecutingTool(false)
    }
  }

  const handleDeny = () => {
    if (!pendingProposal) return
    const denialEntry = {
      role: 'user',
      type: 'tool_approval',
      tool_name: pendingProposal.tool_name,
      approved: false
    }
    const updated = [...conversationHistory, denialEntry]
    setConversationHistory(updated)
    setPendingProposal(null)
    callStep(updated)
  }

  const fetchExample = async () => {
    try {
      const res = await fetch(API_EXAMPLE_URL, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.status === 401) {
        logout()
        return
      }
      const data = await res.json()
      setSystemDescription(data.system_description || '')
      setSecurityAlerts(data.security_alerts || '')
      setOperatorFeedback(data.operator_feedback || '')
    } catch (err) {
      setAlert({ type: 'danger', message: `Failed to fetch example: ${err.message}` })
    }
  }

  const handleClear = () => {
    setSystemDescription('')
    setSecurityAlerts('')
    setOperatorFeedback('')
    setRecoveryContext('')
    setConversationHistory([])
    setPendingProposal(null)
  }

  const fetchPrompt = async () => {
    setLoadingPrompt(true)
    try {
      const res = await fetch(API_AGENTS_INFO_PROMPT_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          system_description: systemDescription,
          security_alerts: securityAlerts,
          operator_feedback: operatorFeedback,
          recovery_context: recoveryContext
        })
      })
      if (res.status === 401) {
        logout()
        return
      }
      const data = await res.json()
      setPromptText(data.prompt || '')
      setShowPromptModal(true)
    } catch (err) {
      setAlert({ type: 'danger', message: `Failed to fetch prompt: ${err.message}` })
    } finally {
      setLoadingPrompt(false)
    }
  }

  const toggleResult = (index) => {
    setExpandedResults((prev) => ({ ...prev, [index]: !prev[index] }))
  }

  const isAgentBusy = running || executingTool

  return (
    <div>
      {alert && (
        <div className={`alert alert-${alert.type} alert-dismissible`} role="alert">
          {alert.message}
          <button type="button" className="close" aria-label="Close" onClick={() => setAlert(null)}>
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
      )}

      <div className="ia-description">
        <p>
          The Information Agent uses an LLM (Gemini) with function calling to autonomously gather
          and analyze information about a security incident. It has access to tools for threat
          intelligence, vulnerability lookups, and indicator-of-compromise analysis. The agent
          analyzes the incident context you provide, then proposes tool calls one at a time. Before
          each tool is executed you can approve or deny it. After gathering sufficient information
          the agent produces a structured incident assessment.
        </p>
      </div>

      <div className="ia-section">
        <label htmlFor="ia-system-desc">System description</label>
        <p className="ia-hint">
          Describe the target system, its architecture, hosts, and services.
        </p>
        <textarea
          id="ia-system-desc"
          className="form-control ia-textarea"
          rows="8"
          value={systemDescription}
          onChange={(e) => setSystemDescription(e.target.value)}
          disabled={isAgentBusy}
          placeholder="e.g., The system consists of a web server (Apache on 10.0.0.1), a database server (PostgreSQL on 10.0.0.2), and a firewall..."
        />
      </div>
      <div className="ia-section">
        <label htmlFor="ia-alerts">Security alerts and logs</label>
        <p className="ia-hint">
          Paste relevant security alerts, IDS logs, or other indicators of compromise.
        </p>
        <textarea
          id="ia-alerts"
          className="form-control ia-textarea"
          rows="8"
          value={securityAlerts}
          onChange={(e) => setSecurityAlerts(e.target.value)}
          disabled={isAgentBusy}
          placeholder="e.g., [ALERT] Brute-force SSH login detected on 10.0.0.1 from 192.168.1.50 (200 attempts in 5 min)..."
        />
      </div>
      <div className="ia-section">
        <label htmlFor="ia-feedback">Operator input</label>
        <p className="ia-hint">
          Optionally provide additional context or instructions for the agent.
        </p>
        <textarea
          id="ia-feedback"
          className="form-control ia-textarea"
          rows="6"
          value={operatorFeedback}
          onChange={(e) => setOperatorFeedback(e.target.value)}
          disabled={isAgentBusy}
          placeholder="e.g., The SSH brute force alert on server 3 likely led to a compromise, since the SQL injection originates from that host..."
        />
      </div>
      <div className="ia-section">
        <label htmlFor="ia-recovery">Recovery context</label>
        <p className="ia-hint">
          Define recovery constraints, SLAs, or critical services that must remain available.
        </p>
        <textarea
          id="ia-recovery"
          className="form-control ia-textarea"
          rows="4"
          value={recoveryContext}
          onChange={(e) => setRecoveryContext(e.target.value)}
          disabled={isAgentBusy}
          placeholder="e.g., Server 6 PostgreSQL must not be taken offline (all services depend on it)..."
        />
      </div>

      <button
        type="button"
        className="btn btn-dark btn-sm ia-btn"
        onClick={handleRun}
        disabled={isAgentBusy || (!systemDescription && !securityAlerts)}
      >
        <i className="fa fa-bolt" aria-hidden="true" />
        {isAgentBusy ? ' Running...' : ' Run agent'}
      </button>
      <button
        type="button"
        className="btn btn-outline-dark btn-sm ia-btn"
        onClick={fetchExample}
        disabled={isAgentBusy}
      >
        <i className="fa fa-download" aria-hidden="true" /> Fetch example incident
      </button>
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

      {showPromptModal && (
        <div className="ia-modal-backdrop" onClick={() => setShowPromptModal(false)}>
          <div className="ia-modal" onClick={(e) => e.stopPropagation()}>
            <div className="ia-modal-header">
              <span className="ia-modal-title">System Prompt</span>
              <button
                type="button"
                className="close"
                aria-label="Close"
                onClick={() => setShowPromptModal(false)}
              >
                <span aria-hidden="true">&times;</span>
              </button>
            </div>
            <div className="ia-modal-body">
              <pre className="ia-prompt-text">{promptText}</pre>
            </div>
          </div>
        </div>
      )}

      {conversationHistory.length > 0 && (
        <div style={{ marginTop: '28px' }}>
          <p className="ia-log-title">Activity log</p>
          <div className="ia-log">
            {conversationHistory.map((entry, index) => {
              if (entry.type === 'tool_proposal') {
                const isCurrentPending = pendingProposal && index === conversationHistory.length - 1
                return (
                  <div key={index} className="card ia-entry border-warning">
                    <div className="card-body">
                      <div className="ia-entry-header">
                        <span className="badge badge-warning">Tool Call</span>
                        <span className="ia-tool-name">{entry.tool_name}</span>
                      </div>
                      {entry.rationale && <p className="ia-rationale mb-0">{entry.rationale}</p>}
                      <pre className="ia-args mb-0">{JSON.stringify(entry.tool_args, null, 2)}</pre>
                      {isCurrentPending && (
                        <div>
                          <button
                            type="button"
                            className="btn btn-outline-success btn-sm ia-action-btn"
                            onClick={handleApprove}
                            disabled={executingTool}
                          >
                            {executingTool ? 'Executing...' : 'Approve'}
                          </button>
                          <button
                            type="button"
                            className="btn btn-outline-danger btn-sm ia-action-btn"
                            onClick={handleDeny}
                            disabled={executingTool}
                          >
                            Deny
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                )
              }

              if (entry.type === 'tool_approval') {
                return (
                  <div key={index} className="mb-2">
                    <span
                      className={`badge ia-approval-badge badge-${entry.approved ? 'success' : 'danger'}`}
                    >
                      {entry.approved ? 'Approved' : 'Denied'}: {entry.tool_name}
                    </span>
                  </div>
                )
              }

              if (entry.type === 'tool_result') {
                const isExpanded = expandedResults[index]
                return (
                  <div key={index} className="card ia-entry border-light">
                    <div className="card-body">
                      <div
                        className="ia-entry-header ia-result-toggle"
                        onClick={() => toggleResult(index)}
                      >
                        <span className="badge badge-secondary">Result</span>
                        <span className="ia-tool-name">{entry.tool_name}</span>
                        <span className="ia-toggle-hint">{isExpanded ? 'collapse' : 'expand'}</span>
                      </div>
                      {isExpanded && (
                        <pre className="ia-result-data mb-0">
                          {JSON.stringify(entry.result, null, 2)}
                        </pre>
                      )}
                    </div>
                  </div>
                )
              }

              if (entry.type === 'streaming') {
                return (
                  <div key={index} className="card ia-entry ia-streaming-entry">
                    <div className="card-body">
                      <div className="ia-entry-header mb-2">
                        <span className="badge badge-info">Thinking</span>
                      </div>
                      {entry.text && <div className="ia-assessment-body">{entry.text}</div>}
                      <span className="ia-typing-indicator">
                        <span className="ia-typing-dot" />
                        <span className="ia-typing-dot" />
                        <span className="ia-typing-dot" />
                      </span>
                    </div>
                  </div>
                )
              }

              if (entry.type === 'assessment') {
                return (
                  <div key={index} className="card ia-entry border-dark">
                    <div className="card-body">
                      <div className="ia-entry-header mb-2">
                        <span className="badge badge-dark">Assessment</span>
                        <span className="ia-tool-name">Final Incident Assessment</span>
                      </div>
                      <div className="ia-assessment-body">{entry.content}</div>
                    </div>
                  </div>
                )
              }

              return null
            })}
            {isAgentBusy && (
              <div className="ia-spinner">
                <div className="spinner-border" role="status">
                  <span className="sr-only">Loading...</span>
                </div>
                {executingTool ? 'Executing tool...' : 'Agent is thinking...'}
              </div>
            )}
            <div ref={logEndRef} />
          </div>
        </div>
      )}
    </div>
  )
}

export default InformationAgent
