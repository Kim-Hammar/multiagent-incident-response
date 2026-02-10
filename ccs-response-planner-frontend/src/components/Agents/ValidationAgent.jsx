import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { useAuth } from '../../contexts/AuthContext.jsx'
import {
  API_EXAMPLE_URL,
  API_AGENTS_VALIDATION_STEP_URL,
  API_AGENTS_VALIDATION_TOOL_URL,
  API_AGENTS_VALIDATION_PROMPT_URL
} from '../Common/constants'

const TOOL_LABELS = {
  dt_exec: { label: 'DT Terminal', icon: 'fa-terminal' }
}

function formatToolArgs(toolName, args) {
  if (!args) return []
  switch (toolName) {
    case 'dt_exec':
      return [
        ['Container', args.container || ''],
        ['Command', args.command || '']
      ]
    default:
      return [['Arguments', JSON.stringify(args)]]
  }
}

/**
 * Renders a strip of image thumbnails with remove buttons.
 * Clicking a thumbnail opens a full-size lightbox overlay.
 */
function ImageThumbnails({ images, setImages, disabled }) {
  const [lightboxSrc, setLightboxSrc] = useState(null)

  if (images.length === 0) return null

  const removeImage = (index) => {
    if (disabled) return
    setImages((prev) => prev.filter((_, i) => i !== index))
  }

  return (
    <>
      <div className="ia-image-thumbnails">
        {images.map((src, index) => (
          <div key={index} className="ia-thumbnail-wrapper">
            <img
              src={src}
              alt={`Pasted ${index + 1}`}
              className="ia-thumbnail-img"
              onClick={() => setLightboxSrc(src)}
            />
            {!disabled && (
              <button
                type="button"
                className="ia-thumbnail-remove"
                onClick={() => removeImage(index)}
                aria-label="Remove image"
              >
                &times;
              </button>
            )}
          </div>
        ))}
      </div>
      {lightboxSrc && (
        <div className="lightbox-overlay" onClick={() => setLightboxSrc(null)}>
          <button
            type="button"
            className="lightbox-close"
            onClick={() => setLightboxSrc(null)}
            aria-label="Close preview"
          >
            &times;
          </button>
          <img
            src={lightboxSrc}
            alt="Full size preview"
            className="lightbox-img"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </>
  )
}

/**
 * Small component that displays elapsed seconds since mount.
 */
function ElapsedTimer() {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setSeconds((s) => s + 1), 1000)
    return () => clearInterval(id)
  }, [])
  return <span className="ia-elapsed">{seconds}s</span>
}

const RECOVERY_STATE_LABELS = {
  is_attack_contained: 'Attack Contained',
  is_attack_assessed: 'Attack Assessed',
  is_forensic_evidence_preserved: 'Forensic Evidence Preserved',
  is_attack_evicted: 'Attack Evicted',
  is_system_hardened: 'System Hardened',
  are_services_restored: 'Services Restored'
}

/**
 * Renders a recovery state object as colored badges.
 */
function RecoveryStateBadges({ state }) {
  if (!state) return null
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
      {Object.entries(RECOVERY_STATE_LABELS).map(([key, label]) => (
        <span key={key} className={`badge badge-${state[key] ? 'success' : 'secondary'}`}>
          {state[key] ? '\u2713' : '\u2717'} {label}
        </span>
      ))}
    </div>
  )
}

/**
 * ValidationAgent component — drives the validation agent loop with
 * human-in-the-loop tool approval.
 */
function ValidationAgent() {
  const { token, logout } = useAuth()
  const [systemDescription, setSystemDescription] = useState('')
  const [incidentReport, setIncidentReport] = useState('')
  const [responsePlan, setResponsePlan] = useState('')
  const [specification, setSpecification] = useState('')
  const [systemDescriptionImages, setSystemDescriptionImages] = useState([])
  const [conversationHistory, setConversationHistory] = useState([])
  const [running, setRunning] = useState(false)
  const [executingTool, setExecutingTool] = useState(null)
  const [pendingProposal, setPendingProposal] = useState(null)
  const [alert, setAlert] = useState(null)
  const [expandedEntries, setExpandedEntries] = useState({})
  const [showPromptModal, setShowPromptModal] = useState(false)
  const [promptText, setPromptText] = useState('')
  const [loadingPrompt, setLoadingPrompt] = useState(false)
  const [autopilot, setAutopilot] = useState(false)
  const [hasNewActivity, setHasNewActivity] = useState(false)
  const logEndRef = useRef(null)
  const logContainerRef = useRef(null)
  const streamingTraceRef = useRef(null)
  const isNearBottomRef = useRef(true)

  const handlePaste = (event) => {
    const items = event.clipboardData?.items
    if (!items) return
    for (const item of items) {
      if (item.type.startsWith('image/')) {
        event.preventDefault()
        const blob = item.getAsFile()
        const reader = new FileReader()
        reader.onload = () => {
          setSystemDescriptionImages((prev) => [...prev, reader.result])
        }
        reader.readAsDataURL(blob)
        return
      }
    }
  }

  useEffect(() => {
    if (!alert) return
    const timer = setTimeout(() => setAlert(null), 3000)
    return () => clearTimeout(timer)
  }, [alert])

  useEffect(() => {
    if (autopilot && pendingProposal) {
      handleApprove()
    }
  }, [autopilot, pendingProposal])

  useEffect(() => {
    if (isNearBottomRef.current) {
      if (logEndRef.current) {
        logEndRef.current.scrollIntoView({ behavior: 'smooth' })
      }
    } else {
      setHasNewActivity(true)
    }
    if (streamingTraceRef.current) {
      streamingTraceRef.current.scrollTop = streamingTraceRef.current.scrollHeight
    }
  }, [conversationHistory])

  const handleLogScroll = () => {
    const el = logContainerRef.current
    if (!el) return
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80
    isNearBottomRef.current = nearBottom
    if (nearBottom) setHasNewActivity(false)
  }

  const scrollToBottom = () => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
    setHasNewActivity(false)
  }

  const callStep = async (history) => {
    setRunning(true)
    const streamingIdx = history.length
    const streamingEntry = { role: 'model', type: 'streaming', text: '' }
    setConversationHistory([...history, streamingEntry])
    try {
      const res = await fetch(API_AGENTS_VALIDATION_STEP_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          system_description: systemDescription,
          incident_report: incidentReport,
          response_plan: responsePlan,
          specification: specification,
          conversation_history: history,
          images: systemDescriptionImages
        })
      })
      if (res.status === 401) {
        logout()
        return
      }
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        const msg = data.error || `Agent step failed (HTTP ${res.status})`
        setAlert({ type: 'danger', message: msg })
        setConversationHistory([...history, { role: 'system', type: 'error', message: msg }])
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
          if (event.type === 'text' || event.type === 'thinking') {
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
              rationale: event.rationale,
              thinking_trace: event.thinking_trace || '',
              _model_parts: event._model_parts
            }
          } else if (event.type === 'validation_report') {
            finalEntry = {
              role: 'model',
              type: 'validation_report',
              validation_report: event.validation_report,
              thinking_trace: event.thinking_trace || ''
            }
          } else if (event.type === 'error') {
            const msg = event.message || 'Agent stream error'
            setAlert({ type: 'danger', message: msg })
            setConversationHistory([...history, { role: 'system', type: 'error', message: msg }])
            return
          }
        }
      }

      if (finalEntry) {
        const entries = []
        if (finalEntry.thinking_trace) {
          entries.push({ role: 'model', type: 'reasoning', text: finalEntry.thinking_trace })
        }
        entries.push(finalEntry)
        const updated = [...history, ...entries]
        setConversationHistory(updated)
        if (finalEntry.type === 'tool_proposal') {
          setPendingProposal(finalEntry)
        }
      } else if (accumulated) {
        let report
        try {
          report = JSON.parse(accumulated)
        } catch {
          report = {
            executive_summary: accumulated,
            action_results: [],
            final_recovery_state: {
              is_attack_contained: false,
              is_attack_assessed: false,
              is_forensic_evidence_preserved: false,
              is_attack_evicted: false,
              is_system_hardened: false,
              are_services_restored: false
            },
            final_service_state: [],
            overall_result: 'Plan validation failed',
            recommendations: []
          }
        }
        setConversationHistory([
          ...history,
          { role: 'model', type: 'validation_report', validation_report: report }
        ])
      } else {
        setConversationHistory([
          ...history,
          { role: 'system', type: 'error', message: 'Agent returned an empty response.' }
        ])
      }
    } catch (err) {
      setAlert({ type: 'danger', message: `Agent error: ${err.message}` })
      setConversationHistory([...history, { role: 'system', type: 'error', message: err.message }])
    } finally {
      setRunning(false)
    }
  }

  const handleRun = () => {
    setPendingProposal(null)
    setConversationHistory([])
    setExpandedEntries({})
    callStep([])
  }

  const handleApprove = async () => {
    if (!pendingProposal) return
    const proposal = pendingProposal
    const approvalEntry = {
      role: 'user',
      type: 'tool_approval',
      tool_name: proposal.tool_name,
      approved: true
    }
    setPendingProposal(null)
    setExecutingTool(proposal.tool_name)
    try {
      const res = await fetch(API_AGENTS_VALIDATION_TOOL_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          tool_name: proposal.tool_name,
          tool_args: proposal.tool_args
        })
      })
      if (res.status === 401) {
        logout()
        return
      }
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        setAlert({
          type: 'danger',
          message: errData.error || `Tool execution failed (HTTP ${res.status})`
        })
        setExecutingTool(null)
        return
      }
      const data = await res.json()
      const resultEntry = {
        role: 'tool',
        type: 'tool_result',
        tool_name: proposal.tool_name,
        result: data.error ? { error: data.error } : data.result
      }
      const updated = [...conversationHistory, approvalEntry, resultEntry]
      setConversationHistory(updated)
      setExecutingTool(null)
      await callStep(updated)
    } catch (err) {
      setAlert({ type: 'danger', message: `Tool execution error: ${err.message}` })
      setExecutingTool(null)
    }
  }

  const handleDeny = async () => {
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
    await callStep(updated)
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
      setIncidentReport(data.incident_report || '')
      setResponsePlan(data.response_plan || '')
      setSpecification(data.specification || '')
      setSystemDescriptionImages(data.system_description_images || [])
    } catch (err) {
      setAlert({ type: 'danger', message: `Failed to fetch example: ${err.message}` })
    }
  }

  const handleClear = () => {
    setSystemDescription('')
    setIncidentReport('')
    setResponsePlan('')
    setSpecification('')
    setSystemDescriptionImages([])
    setConversationHistory([])
    setPendingProposal(null)
    setExpandedEntries({})
  }

  const fetchPrompt = async () => {
    setLoadingPrompt(true)
    try {
      const res = await fetch(API_AGENTS_VALIDATION_PROMPT_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          system_description: systemDescription,
          incident_report: incidentReport,
          response_plan: responsePlan,
          specification: specification
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

  const toggleEntry = (index) => {
    setExpandedEntries((prev) => ({ ...prev, [index]: !prev[index] }))
  }

  const toolLabel = (name) => (TOOL_LABELS[name] || { label: name, icon: 'fa-cog' }).label
  const toolIcon = (name) => (TOOL_LABELS[name] || { label: name, icon: 'fa-cog' }).icon

  const isAgentBusy = running || executingTool

  const overallResultClass = {
    'Plan fully validated': 'success',
    'Plan partially validated': 'warning',
    'Plan validation failed': 'danger'
  }

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
          This agent validates a response plan against the deployed digital twin. Its tasks are
          threefold:
          <ol>
            <li>
              Apply each response action sequentially on the digital twin containers using shell
              commands.
            </li>
            <li>
              After each action, check the recovery state (6 booleans) and service state
              (specification commands).
            </li>
            <li>
              Produce a structured validation report with per-action results and overall outcome.
            </li>
          </ol>
        </p>
      </div>

      <div className="ia-section">
        <label htmlFor="va-system-desc">System description</label>
        <p className="ia-hint">
          Describe the target system, its architecture, hosts, and services.
        </p>
        <textarea
          id="va-system-desc"
          className="form-control ia-textarea"
          rows="6"
          value={systemDescription}
          onChange={(e) => setSystemDescription(e.target.value)}
          onPaste={handlePaste}
          disabled={isAgentBusy}
          placeholder="e.g., The system consists of a web server, database server, and firewall..."
        />
        <ImageThumbnails
          images={systemDescriptionImages}
          setImages={setSystemDescriptionImages}
          disabled={isAgentBusy}
        />
      </div>
      <div className="ia-section">
        <label htmlFor="va-incident-report">Incident report</label>
        <p className="ia-hint">
          Paste the incident report/assessment produced by the Information Agent.
        </p>
        <textarea
          id="va-incident-report"
          className="form-control ia-textarea"
          rows="6"
          value={incidentReport}
          onChange={(e) => setIncidentReport(e.target.value)}
          disabled={isAgentBusy}
          placeholder="e.g., An SSH brute-force attack was detected on server 3, followed by SQL injection from server 6..."
        />
      </div>
      <div className="ia-section">
        <label htmlFor="va-response-plan">Response plan</label>
        <p className="ia-hint">Paste the response plan to validate against the digital twin.</p>
        <textarea
          id="va-response-plan"
          className="form-control ia-textarea"
          rows="6"
          value={responsePlan}
          onChange={(e) => setResponsePlan(e.target.value)}
          disabled={isAgentBusy}
          placeholder="e.g., 1. Block attacker IP on firewall. 2. Kill malicious processes on server 3. 3. Rotate credentials..."
        />
      </div>
      <div className="ia-section">
        <label htmlFor="va-specification">Specification commands (optional)</label>
        <p className="ia-hint">
          JSON array of specification commands. If left empty, the default digital twin
          specification will be used.
        </p>
        <textarea
          id="va-specification"
          className="form-control ia-textarea"
          rows="4"
          value={specification}
          onChange={(e) => setSpecification(e.target.value)}
          disabled={isAgentBusy}
          placeholder="Leave empty to use default specification commands from the digital twin config."
        />
      </div>
      <button
        type="button"
        className="btn btn-dark btn-sm ia-btn"
        onClick={handleRun}
        disabled={isAgentBusy || (!systemDescription && !incidentReport)}
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
        <i className="fa fa-download" aria-hidden="true" /> Fetch example
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
      <div className="form-check form-check-inline ia-btn">
        <input
          className="form-check-input"
          type="checkbox"
          id="va-autopilot"
          checked={autopilot}
          onChange={(e) => setAutopilot(e.target.checked)}
        />
        <label className="form-check-label" htmlFor="va-autopilot">
          Autopilot <span className="ia-hint">(auto-approve all tool requests)</span>
        </label>
      </div>

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
          <div className="ia-log" ref={logContainerRef} onScroll={handleLogScroll}>
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
                        <span className="ia-proposal-tool-inline">
                          {toolLabel(entry.tool_name)}
                        </span>
                        {!isCurrentPending && (
                          <span className="ia-toggle-hint">
                            {isExpanded ? 'collapse' : 'expand'}
                          </span>
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
                return (
                  <div key={index} className="card ia-entry ia-result-entry">
                    <div className="card-body">
                      <div className="ia-result-header" onClick={() => toggleEntry(index)}>
                        <i className={`fa ${toolIcon(entry.tool_name)}`} aria-hidden="true" />
                        <span className="ia-result-label">{toolLabel(entry.tool_name)} result</span>
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

              if (entry.type === 'validation_report') {
                const r = entry.validation_report || {}
                const isExpanded = expandedEntries[index] !== false
                return (
                  <div key={index} className="card ia-entry border-dark">
                    <div className="card-body">
                      <div
                        className="ia-result-header"
                        onClick={() =>
                          setExpandedEntries((prev) => ({
                            ...prev,
                            [index]: prev[index] === false
                          }))
                        }
                      >
                        <span className="badge badge-dark">Validation Report</span>
                        <span className="ia-tool-name">Response Plan Validation</span>
                        <span className="ia-toggle-hint">{isExpanded ? 'collapse' : 'expand'}</span>
                      </div>

                      {isExpanded && (
                        <div style={{ marginTop: '10px' }}>
                          {r.overall_result && (
                            <div className="ia-assessment-section">
                              <div className="ia-assessment-label">Overall Result</div>
                              <span
                                className={`badge ia-severity-badge badge-${overallResultClass[r.overall_result] || 'secondary'}`}
                              >
                                {r.overall_result}
                              </span>
                            </div>
                          )}

                          {r.executive_summary && (
                            <div className="ia-assessment-section">
                              <div className="ia-assessment-label">Executive Summary</div>
                              <p className="ia-assessment-body mb-0">{r.executive_summary}</p>
                            </div>
                          )}

                          {r.final_recovery_state && (
                            <div className="ia-assessment-section">
                              <div className="ia-assessment-label">Final Recovery State</div>
                              <RecoveryStateBadges state={r.final_recovery_state} />
                            </div>
                          )}

                          {r.final_service_state && r.final_service_state.length > 0 && (
                            <div className="ia-assessment-section">
                              <div className="ia-assessment-label">Final Service State</div>
                              <table className="ia-ioc-table">
                                <thead>
                                  <tr>
                                    <th>Check</th>
                                    <th>Result</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {r.final_service_state.map((s, i) => (
                                    <tr key={i}>
                                      <td>{s.description}</td>
                                      <td>
                                        <span
                                          className={`badge badge-${s.passed ? 'success' : 'danger'}`}
                                        >
                                          {s.passed ? 'Passed' : 'Failed'}
                                        </span>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}

                          {r.action_results && r.action_results.length > 0 && (
                            <div className="ia-assessment-section">
                              <div className="ia-assessment-label">Per-Action Results</div>
                              {r.action_results.map((ar, i) => (
                                <div key={i} className="card ia-attack-path mb-2">
                                  <div className="card-body" style={{ padding: '10px 14px' }}>
                                    <strong style={{ fontSize: '13px' }}>{ar.action_name}</strong>
                                    {ar.action_description && (
                                      <p
                                        className="ia-assessment-body mb-1"
                                        style={{ fontSize: '12px' }}
                                      >
                                        {ar.action_description}
                                      </p>
                                    )}
                                    {ar.outcome && (
                                      <p
                                        className="ia-assessment-body mb-1"
                                        style={{ fontSize: '12px' }}
                                      >
                                        <strong>Outcome:</strong> {ar.outcome}
                                      </p>
                                    )}
                                    {ar.commands_executed && ar.commands_executed.length > 0 && (
                                      <div style={{ fontSize: '12px', marginBottom: '4px' }}>
                                        <strong>Commands:</strong>
                                        <ul style={{ paddingLeft: '18px', marginBottom: '4px' }}>
                                          {ar.commands_executed.map((cmd, j) => (
                                            <li key={j}>
                                              <code>{cmd}</code>
                                            </li>
                                          ))}
                                        </ul>
                                      </div>
                                    )}
                                    {ar.recovery_state && (
                                      <div style={{ marginTop: '4px' }}>
                                        <RecoveryStateBadges state={ar.recovery_state} />
                                      </div>
                                    )}
                                    {ar.service_state && ar.service_state.length > 0 && (
                                      <div
                                        style={{
                                          marginTop: '4px',
                                          fontSize: '12px',
                                          display: 'flex',
                                          flexWrap: 'wrap',
                                          gap: '4px'
                                        }}
                                      >
                                        {ar.service_state.map((ss, j) => (
                                          <span
                                            key={j}
                                            className={`badge badge-${ss.passed ? 'success' : 'danger'}`}
                                          >
                                            {ss.passed ? '\u2713' : '\u2717'} {ss.description}
                                          </span>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}

                          {r.recommendations && r.recommendations.length > 0 && (
                            <div className="ia-assessment-section">
                              <div className="ia-assessment-label">Recommendations</div>
                              <ul
                                style={{
                                  fontSize: '13px',
                                  paddingLeft: '20px',
                                  marginBottom: 0
                                }}
                              >
                                {r.recommendations.map((rec, i) => (
                                  <li key={i}>{rec}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )
              }

              return null
            })}
            {executingTool && (
              <div className="card ia-entry ia-streaming-entry">
                <div className="card-body">
                  <div className="ia-thinking-header">
                    <div className="spinner-border spinner-border-sm" role="status">
                      <span className="sr-only">Loading...</span>
                    </div>
                    <i className={`fa ${toolIcon(executingTool)}`} aria-hidden="true" />
                    <span className="ia-thinking-title">
                      Executing {toolLabel(executingTool)}...
                    </span>
                  </div>
                </div>
              </div>
            )}
            <div ref={logEndRef} />
            {hasNewActivity && (
              <button type="button" className="ia-new-activity-btn" onClick={scrollToBottom}>
                <i className="fa fa-arrow-down" aria-hidden="true" /> New activity
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default ValidationAgent
