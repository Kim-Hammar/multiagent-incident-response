import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { useAuth } from '../../contexts/AuthContext.jsx'
import {
  API_EXAMPLE_URL,
  API_AGENTS_PENTEST_STEP_URL,
  API_AGENTS_PENTEST_TOOL_URL,
  API_AGENTS_PENTEST_PROMPT_URL
} from '../Common/constants'

const TOOL_LABELS = {
  pentest_exec: { label: 'Attacker Terminal', icon: 'fa-terminal' }
}

function formatToolArgs(toolName, args) {
  if (!args) return []
  switch (toolName) {
    case 'pentest_exec':
      return [['Command', args.command || '']]
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

/**
 * PenetrationTestAgent component — drives the pentest agent loop with
 * human-in-the-loop tool approval.
 */
function PenetrationTestAgent() {
  const { token, logout } = useAuth()
  const [systemDescription, setSystemDescription] = useState('')
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
  const logEndRef = useRef(null)
  const streamingTraceRef = useRef(null)

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
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
    if (streamingTraceRef.current) {
      streamingTraceRef.current.scrollTop = streamingTraceRef.current.scrollHeight
    }
  }, [conversationHistory])

  const callStep = async (history) => {
    setRunning(true)
    const streamingIdx = history.length
    const streamingEntry = { role: 'model', type: 'streaming', text: '' }
    setConversationHistory([...history, streamingEntry])
    try {
      const res = await fetch(API_AGENTS_PENTEST_STEP_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          system_description: systemDescription,
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
          } else if (event.type === 'report') {
            finalEntry = {
              role: 'model',
              type: 'report',
              report: event.report,
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
            attack_paths: [],
            vulnerabilities_found: [],
            compromised_servers: [],
            recommendations: []
          }
        }
        setConversationHistory([...history, { role: 'model', type: 'report', report }])
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
      const res = await fetch(API_AGENTS_PENTEST_TOOL_URL, {
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
      setSystemDescriptionImages(data.system_description_images || [])
    } catch (err) {
      setAlert({ type: 'danger', message: `Failed to fetch example: ${err.message}` })
    }
  }

  const handleClear = () => {
    setSystemDescription('')
    setSystemDescriptionImages([])
    setConversationHistory([])
    setPendingProposal(null)
    setExpandedEntries({})
  }

  const fetchPrompt = async () => {
    setLoadingPrompt(true)
    try {
      const res = await fetch(API_AGENTS_PENTEST_PROMPT_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          system_description: systemDescription
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

  const severityClass = {
    Critical: 'danger',
    High: 'warning',
    Medium: 'info',
    Low: 'success'
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
          This agent performs a grey-box penetration test from an external attacker machine. Its
          tasks are threefold:
          <ol>
            <li>
              Probe reachable hosts from the perimeter network using the provided system description
              and topology.
            </li>
            <li>
              Attempt exploitation and lateral movement to identify attack paths through the
              network.
            </li>
            <li>
              Produce a structured penetration test report with attack paths, vulnerabilities, and
              remediation recommendations.
            </li>
          </ol>
        </p>
      </div>

      <div className="ia-section">
        <label htmlFor="pt-system-desc">System description</label>
        <p className="ia-hint">
          Describe the target system, its architecture, hosts, and services.
        </p>
        <textarea
          id="pt-system-desc"
          className="form-control ia-textarea"
          rows="8"
          value={systemDescription}
          onChange={(e) => setSystemDescription(e.target.value)}
          onPaste={handlePaste}
          disabled={isAgentBusy}
          placeholder="e.g., The system consists of a web server (Apache on 10.0.0.1), a database server (PostgreSQL on 10.0.0.2), and a firewall..."
        />
        <ImageThumbnails
          images={systemDescriptionImages}
          setImages={setSystemDescriptionImages}
          disabled={isAgentBusy}
        />
      </div>
      <button
        type="button"
        className="btn btn-dark btn-sm ia-btn"
        onClick={handleRun}
        disabled={isAgentBusy || !systemDescription}
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
          id="pt-autopilot"
          checked={autopilot}
          onChange={(e) => setAutopilot(e.target.checked)}
        />
        <label className="form-check-label" htmlFor="pt-autopilot">
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

              if (entry.type === 'report') {
                const r = entry.report || {}
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
                        <span className="badge badge-dark">Report</span>
                        <span className="ia-tool-name">Penetration Test Report</span>
                        <span className="ia-toggle-hint">{isExpanded ? 'collapse' : 'expand'}</span>
                      </div>

                      {isExpanded && (
                        <div style={{ marginTop: '10px' }}>
                          {r.executive_summary && (
                            <div className="ia-assessment-section">
                              <div className="ia-assessment-label">Executive Summary</div>
                              <p className="ia-assessment-body mb-0">{r.executive_summary}</p>
                            </div>
                          )}

                          {r.compromised_servers && r.compromised_servers.length > 0 && (
                            <div className="ia-assessment-section">
                              <div className="ia-assessment-label">Compromised Servers</div>
                              <div>
                                {r.compromised_servers.map((server, i) => (
                                  <span key={i} className="badge badge-danger mr-1 mb-1">
                                    {server}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {r.attack_paths && r.attack_paths.length > 0 && (
                            <div className="ia-assessment-section">
                              <div className="ia-assessment-label">Attack Paths</div>
                              {r.attack_paths.map((path, i) => (
                                <div key={i} className="card ia-attack-path mb-2">
                                  <div className="card-body" style={{ padding: '10px 14px' }}>
                                    <div
                                      style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '8px',
                                        marginBottom: '6px'
                                      }}
                                    >
                                      <strong style={{ fontSize: '13px' }}>{path.name}</strong>
                                      <span
                                        className={`badge ia-severity-badge badge-${severityClass[path.severity] || 'secondary'}`}
                                      >
                                        {path.severity}
                                      </span>
                                    </div>
                                    <p
                                      className="ia-assessment-body mb-1"
                                      style={{ fontSize: '12px' }}
                                    >
                                      {path.description}
                                    </p>
                                    {path.steps && path.steps.length > 0 && (
                                      <ol
                                        style={{
                                          fontSize: '12px',
                                          paddingLeft: '18px',
                                          marginBottom: '6px'
                                        }}
                                      >
                                        {path.steps.map((step, j) => (
                                          <li key={j}>{step}</li>
                                        ))}
                                      </ol>
                                    )}
                                    {path.compromised_assets &&
                                      path.compromised_assets.length > 0 && (
                                        <div style={{ fontSize: '12px' }}>
                                          <span style={{ fontWeight: 600, color: '#495057' }}>
                                            Compromised:{' '}
                                          </span>
                                          {path.compromised_assets.map((asset, j) => (
                                            <span key={j} className="badge badge-secondary mr-1">
                                              {asset}
                                            </span>
                                          ))}
                                        </div>
                                      )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}

                          {r.vulnerabilities_found && r.vulnerabilities_found.length > 0 && (
                            <div className="ia-assessment-section">
                              <div className="ia-assessment-label">Vulnerabilities Found</div>
                              <table className="ia-ioc-table">
                                <thead>
                                  <tr>
                                    <th>Vulnerability</th>
                                    <th>Affected Asset</th>
                                    <th>Severity</th>
                                    <th>Remediation</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {r.vulnerabilities_found.map((v, i) => (
                                    <tr key={i}>
                                      <td>{v.vulnerability}</td>
                                      <td>{v.affected_asset}</td>
                                      <td>
                                        <span
                                          className={`badge badge-${severityClass[v.severity] || 'secondary'}`}
                                        >
                                          {v.severity}
                                        </span>
                                      </td>
                                      <td>{v.remediation}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
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
          </div>
        </div>
      )}
    </div>
  )
}

export default PenetrationTestAgent
