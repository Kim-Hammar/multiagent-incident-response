import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../../contexts/AuthContext.jsx'
import {
  API_EXAMPLES_URL,
  API_AGENTS_CODE_MANAGER_STEP_URL,
  API_AGENTS_CODE_MANAGER_TOOL_URL,
  API_AGENTS_CODE_MANAGER_PROMPT_URL,
  API_AGENTS_CODE_PROMPT_URL,
  API_AGENTS_CODE_REVIEW_PROMPT_URL,
  API_LLM_URL,
  API_AGENTS_REPORTS_URL,
  API_DT_PYTHON_STOP_URL
} from '../Common/constants'
import ImageThumbnails from './shared/ImageThumbnails.jsx'
import AgentConfigTable from './shared/AgentConfigTable.jsx'
import ExampleSelector from './shared/ExampleSelector.jsx'
import AgentPlanningTab from './shared/AgentPlanningTab.jsx'
import AgentHistoryTab from './shared/AgentHistoryTab.jsx'
import { cleanConversationHistory, stripForBackend } from './shared/conversationUtils.js'
import { pollJobEvents } from './shared/pollJobEvents.js'
import { STREAMING_TOOLS, executeStreamingTool } from './shared/streamingToolExec.js'
import { CodeReportBody, ReviewReportBody } from './shared/ReportBodies.jsx'

/**
 * Render an orchestrator report entry.
 */
function OrchestratorReport({ entry, index, isExpanded, toggleEntry }) {
  const report = entry.orchestrator_report || {}

  const codeReport = entry.final_code_report || report.final_code_report || null

  return (
    <div className="card ia-entry ia-result-entry">
      <div className="card-body">
        <div className="ia-result-header" onClick={() => toggleEntry(index)}>
          <i className="fa fa-flag-checkered" aria-hidden="true" />
          <span className="ia-result-label">Code Manager Report</span>
          <span className="ia-toggle-hint">{isExpanded ? 'collapse' : 'expand'}</span>
        </div>
        {isExpanded && (
          <div style={{ whiteSpace: 'pre-wrap', marginTop: '10px' }}>
            {report.executive_summary && (
              <div className="mb-3">
                <strong>Summary:</strong>
                <p>{report.executive_summary}</p>
              </div>
            )}
            {report.code_report_summary && (
              <div className="mb-3">
                <strong>Code Report Summary:</strong>
                <p>{report.code_report_summary}</p>
              </div>
            )}
            {codeReport && (
              <div className="mb-3" style={{ whiteSpace: 'normal' }}>
                <strong>Final Code Report</strong>
                <CodeReportBody report={codeReport} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * CodeManagerAgent component — orchestrates CodeAgent + CodeReviewerAgent
 * in an automated generate-review-revise loop.
 */
function CodeManagerAgent() {
  const { token, logout } = useAuth()
  const [activeTab, setActiveTab] = useState('config')
  const [systemDescription, setSystemDescription] = useState('')
  const [incidentReport, setIncidentReport] = useState('')
  const [specification, setSpecification] = useState('')
  const [operatorFeedback, setOperatorFeedback] = useState('')
  const [systemDescriptionImages, setSystemDescriptionImages] = useState([])
  const [incidentReportImages, setIncidentReportImages] = useState([])
  const [conversationHistory, setConversationHistory] = useState([])
  const conversationHistoryRef = useRef([])
  const [running, setRunning] = useState(false)
  const [executingTool, setExecutingTool] = useState(null)
  const [pendingProposal, setPendingProposal] = useState(null)
  const [alert, setAlert] = useState(null)
  const [expandedEntries, setExpandedEntries] = useState({})
  const [autopilot, setAutopilot] = useState(true)
  const [hasNewActivity, setHasNewActivity] = useState(false)
  const [contextUsage, setContextUsage] = useState(null)
  const [dtStatus, setDtStatus] = useState(null)
  const [models, setModels] = useState([])
  const [maxIterations, setMaxIterations] = useState(1)
  const [managerModel, setManagerModel] = useState('')
  const [codeAgentModel, setCodeAgentModel] = useState('')
  const [reviewerAgentModel, setReviewerAgentModel] = useState('')
  const [compactionModel, setCompactionModel] = useState('')
  const [compactionThreshold, setCompactionThreshold] = useState(80)
  const [reportHistory, setReportHistory] = useState([])
  const [selectedIncidentId, setSelectedIncidentId] = useState(null)
  const logEndRef = useRef(null)
  const streamingTraceRef = useRef(null)
  const isNearBottomRef = useRef(true)
  const abortControllerRef = useRef(null)
  const lastHeartbeatRef = useRef(Date.now())
  const [livenessStatus, setLivenessStatus] = useState('alive')
  const [heartbeatStatus, setHeartbeatStatus] = useState('')
  const managerStartTimeRef = useRef(null)

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
    fetch(API_LLM_URL, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then((res) => (res.ok ? res.json() : { models: [] }))
      .then((data) => setModels(data.models || []))
      .catch(() => {})
  }, [token])

  conversationHistoryRef.current = conversationHistory

  useEffect(() => {
    if (autopilot && pendingProposal) {
      handleApprove()
    }
  }, [autopilot, pendingProposal])

  useEffect(() => {
    const nearBottom =
      document.documentElement.scrollHeight - window.scrollY - window.innerHeight < 120
    isNearBottomRef.current = nearBottom
    if (nearBottom) {
      window.scrollTo({ top: document.body.scrollHeight, behavior: 'auto' })
      setHasNewActivity(false)
    } else {
      setHasNewActivity(true)
    }
    if (streamingTraceRef.current) {
      streamingTraceRef.current.scrollTop = streamingTraceRef.current.scrollHeight
    }
  }, [conversationHistory])

  useEffect(() => {
    const onScroll = () => {
      const nearBottom =
        document.documentElement.scrollHeight - window.scrollY - window.innerHeight < 120
      isNearBottomRef.current = nearBottom
      if (nearBottom) setHasNewActivity(false)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const scrollToBottom = () => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
    setHasNewActivity(false)
  }

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    fetch(API_DT_PYTHON_STOP_URL, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` }
    }).catch(() => {})
    setRunning(false)
    setExecutingTool(null)
    setPendingProposal(null)
    setConversationHistory((prev) => {
      const cleaned = prev
        .map((entry) => {
          if (entry.type === 'streaming') {
            return entry.text ? { ...entry, type: 'reasoning', role: 'model' } : null
          }
          if (entry.type === 'tool_streaming') {
            return { ...entry, stopped: true }
          }
          return entry
        })
        .filter(Boolean)
      return [...cleaned, { role: 'system', type: 'error', message: 'Planning stopped by user.' }]
    })
  }

  const extractFinalReports = (history) => {
    let codeReport = null
    for (let i = history.length - 1; i >= 0; i--) {
      const h = history[i]
      if (!codeReport && h.type === 'tool_result' && h.tool_name === 'run_code_agent') {
        codeReport = h.result?.code_report || null
      }
      if (codeReport) break
    }
    return { codeReport }
  }

  const callStep = async (history) => {
    setRunning(true)
    const controller = new AbortController()
    abortControllerRef.current = controller
    const streamingEntry = { role: 'model', type: 'streaming', text: '' }
    const compactionEntries = []
    setConversationHistory([...history, streamingEntry])
    try {
      const res = await fetch(API_AGENTS_CODE_MANAGER_STEP_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          system_description: systemDescription,
          incident_report: incidentReport,
          specification: specification,
          operator_feedback: operatorFeedback,
          conversation_history: stripForBackend(history),
          images: [...systemDescriptionImages, ...incidentReportImages],
          model_name: managerModel || undefined,
          last_prompt_tokens: contextUsage?.prompt_tokens || 0,
          compaction_model: compactionModel || undefined,
          compaction_threshold: compactionThreshold / 100,
          max_iterations: maxIterations
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
        setConversationHistory([
          ...history,
          ...compactionEntries,
          { role: 'system', type: 'error', message: msg }
        ])
        return
      }

      const { job_id } = await res.json()
      let accumulated = ''
      let finalEntry = null

      setLivenessStatus('alive')
      lastHeartbeatRef.current = Date.now()
      await pollJobEvents({
        jobId: job_id,
        token,
        signal: controller.signal,
        onHeartbeat: (status) => {
          lastHeartbeatRef.current = Date.now()
          setHeartbeatStatus(status)
        },
        onStale: () => setLivenessStatus('stale'),
        onEvent: (event) => {
          lastHeartbeatRef.current = Date.now()
          setLivenessStatus('alive')
          if (event.type === 'text' || event.type === 'thinking') {
            accumulated += event.delta
            setConversationHistory([
              ...history,
              ...compactionEntries,
              { ...streamingEntry, text: accumulated }
            ])
          } else if (event.type === 'tool_proposal') {
            finalEntry = {
              role: 'model',
              type: 'tool_proposal',
              tool_name: event.tool_name,
              tool_args: event.tool_args,
              rationale: event.rationale,
              thinking_trace: event.thinking_trace || '',
              _model_parts: event._model_parts,
              _anthropic_content: event._anthropic_content,
              _tool_use_id: event._tool_use_id,
              _vendor: event._vendor
            }
          } else if (event.type === 'orchestrator_report') {
            finalEntry = {
              role: 'model',
              type: 'orchestrator_report',
              orchestrator_report: event.orchestrator_report,
              thinking_trace: event.thinking_trace || ''
            }
          } else if (event.type === 'dt_progress') {
            setDtStatus(event.message)
          } else if (event.type === 'context_usage') {
            setContextUsage(event)
          } else if (event.type === 'context_compaction') {
            compactionEntries.push({
              role: 'system',
              type: 'context_compaction',
              original_tokens: event.original_tokens,
              compacted_tokens: event.compacted_tokens,
              compaction_model: event.compaction_model
            })
            setConversationHistory([
              ...history,
              ...compactionEntries,
              { ...streamingEntry, text: accumulated }
            ])
          } else if (event.type === 'error') {
            const msg = event.message || 'Agent stream error'
            setAlert({ type: 'danger', message: msg })
            setConversationHistory([
              ...history,
              ...compactionEntries,
              { role: 'system', type: 'error', message: msg }
            ])
          }
        }
      })

      setDtStatus(null)
      if (finalEntry) {
        const entries = []
        const reasoningText = finalEntry.thinking_trace || accumulated
        if (reasoningText) {
          entries.push({ role: 'model', type: 'reasoning', text: reasoningText })
        }
        entries.push(finalEntry)
        const updated = [...history, ...compactionEntries, ...entries]
        setConversationHistory(updated)
        conversationHistoryRef.current = updated
        if (finalEntry.type === 'tool_proposal') {
          setPendingProposal(finalEntry)
        }
        if (finalEntry.type === 'orchestrator_report') {
          const { codeReport } = extractFinalReports(history)
          finalEntry.final_code_report = codeReport
          saveReport({
            ...finalEntry.orchestrator_report,
            final_code_report: codeReport
          })
        }
      } else if (accumulated) {
        let report
        try {
          report = JSON.parse(accumulated)
        } catch {
          report = {
            executive_summary: accumulated,
            code_report_summary: ''
          }
        }
        const { codeReport } = extractFinalReports(history)
        report.final_code_report = codeReport
        setConversationHistory([
          ...history,
          ...compactionEntries,
          {
            role: 'model',
            type: 'orchestrator_report',
            orchestrator_report: report,
            final_code_report: codeReport
          }
        ])
        saveReport(report)
      } else {
        setConversationHistory([
          ...history,
          ...compactionEntries,
          { role: 'system', type: 'error', message: 'Agent returned an empty response.' }
        ])
      }
    } catch (err) {
      if (err.name === 'AbortError') return
      setAlert({ type: 'danger', message: `Agent error: ${err.message}` })
      setConversationHistory([
        ...history,
        ...compactionEntries,
        { role: 'system', type: 'error', message: err.message }
      ])
    } finally {
      setRunning(false)
      setConversationHistory((prev) => {
        const hasStreaming = prev.some((e) => e.type === 'streaming')
        if (!hasStreaming) return prev
        return prev
          .map((e) =>
            e.type === 'streaming'
              ? e.text
                ? { ...e, type: 'reasoning', role: 'model' }
                : null
              : e
          )
          .filter(Boolean)
      })
    }
  }

  const handleRun = () => {
    setPendingProposal(null)
    setConversationHistory([])
    conversationHistoryRef.current = []
    setExpandedEntries({})
    setContextUsage(null)
    setActiveTab('planning')
    managerStartTimeRef.current = Date.now()
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
    const controller = new AbortController()
    abortControllerRef.current = controller

    if (STREAMING_TOOLS.has(proposal.tool_name)) {
      const subModel =
        proposal.tool_name === 'run_code_reviewer_agent' ? reviewerAgentModel : codeAgentModel
      const streamEntry = {
        type: 'tool_streaming',
        tool_name: proposal.tool_name,
        output: '',
        subEvents: [],
        _modelName: subModel || undefined,
        _startTime: managerStartTimeRef.current || Date.now()
      }
      const latestHistory = conversationHistoryRef.current
      const base = [...latestHistory, approvalEntry, streamEntry]
      setConversationHistory(base)
      try {
        const extraBody = {
          system_description: systemDescription,
          incident_report: incidentReport,
          specification: specification,
          operator_feedback: operatorFeedback,
          images: [...systemDescriptionImages, ...incidentReportImages],
          code_agent_model: codeAgentModel || undefined,
          reviewer_agent_model: reviewerAgentModel || undefined,
          conversation_history: stripForBackend(latestHistory),
          compaction_model: compactionModel || undefined,
          compaction_threshold: compactionThreshold / 100
        }
        const { result } = await executeStreamingTool({
          url: API_AGENTS_CODE_MANAGER_TOOL_URL,
          toolName: proposal.tool_name,
          toolArgs: proposal.tool_args,
          incidentId: selectedIncidentId,
          token,
          signal: controller.signal,
          onChunk: (text) => {
            streamEntry.output += text
            setConversationHistory([...base])
          },
          onSubEvent: (event) => {
            if (event.type === 'context_usage') {
              streamEntry.contextUsage = event
              setConversationHistory([...base])
              return
            }
            if (event.type === 'prompt') {
              streamEntry.prompt = event.text
              streamEntry.promptImages = event.images || []
              setConversationHistory([...base])
              return
            }
            if (event.type === 'thinking_delta') {
              const last = streamEntry.subEvents[streamEntry.subEvents.length - 1]
              if (last && last.type === 'reasoning') {
                last.text += event.text
              } else {
                streamEntry.subEvents.push({
                  type: 'reasoning',
                  text: event.text,
                  _startTime: Date.now()
                })
              }
            } else if (event.type === 'text_delta') {
              const last = streamEntry.subEvents[streamEntry.subEvents.length - 1]
              if (last && last.type === 'text') {
                last.text += event.text
              } else {
                streamEntry.subEvents.push({
                  type: 'text',
                  text: event.text,
                  _startTime: Date.now()
                })
              }
            } else {
              if (!event._startTime) event._startTime = Date.now()
              streamEntry.subEvents.push(event)
            }
            setConversationHistory([...base])
          },
          extraBody
        })
        streamEntry.stopped = true
        const resultEntry = {
          role: 'tool',
          type: 'tool_result',
          tool_name: proposal.tool_name,
          result
        }
        const updated = [...base, resultEntry]
        setConversationHistory(updated)
        conversationHistoryRef.current = updated
        setExecutingTool(null)
        await callStep(updated)
      } catch (err) {
        if (err.name === 'AbortError') return
        if (err.status === 401) {
          logout()
          return
        }
        setAlert({ type: 'danger', message: `Tool execution error: ${err.message}` })
        setExecutingTool(null)
      }
      return
    }

    try {
      const res = await fetch(API_AGENTS_CODE_MANAGER_TOOL_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        signal: controller.signal,
        body: JSON.stringify({
          tool_name: proposal.tool_name,
          tool_args: proposal.tool_args,
          incident_id: selectedIncidentId
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
      const updated = [...conversationHistoryRef.current, approvalEntry, resultEntry]
      setConversationHistory(updated)
      conversationHistoryRef.current = updated
      setExecutingTool(null)
      await callStep(updated)
    } catch (err) {
      if (err.name === 'AbortError') return
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
    const updated = [...conversationHistoryRef.current, denialEntry]
    setConversationHistory(updated)
    conversationHistoryRef.current = updated
    setPendingProposal(null)
    await callStep(updated)
  }

  const loadExample = async (incidentId) => {
    setSelectedIncidentId(incidentId)
    try {
      const res = await fetch(`${API_EXAMPLES_URL}/${incidentId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.status === 401) {
        logout()
        return
      }
      const data = await res.json()
      setSystemDescription(data.system_description || '')
      setIncidentReport(data.incident_report || '')
      setSpecification(data.specification || '')
      setOperatorFeedback('')
      setSystemDescriptionImages(data.system_description_images || [])

      const infoRes = await fetch(
        `${API_AGENTS_REPORTS_URL}?agent_type=report&incident_id=${incidentId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      if (infoRes.ok) {
        const infoReports = await infoRes.json()
        if (infoReports.length > 0) {
          const { attack_path_image, ...reportText } = infoReports[0].report || {}
          setIncidentReportImages(attack_path_image ? [attack_path_image] : [])
          setIncidentReport(JSON.stringify(reportText, null, 2))
        }
      }
    } catch (err) {
      setAlert({ type: 'danger', message: `Failed to load example: ${err.message}` })
    }
  }

  const handleClear = () => {
    setSystemDescription('')
    setIncidentReport('')
    setSpecification('')
    setOperatorFeedback('')
    setSystemDescriptionImages([])
    setIncidentReportImages([])
    setConversationHistory([])
    setPendingProposal(null)
    setExpandedEntries({})
    setSelectedIncidentId(null)
  }

  const getPromptText = async () => {
    const res = await fetch(API_AGENTS_CODE_MANAGER_PROMPT_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({
        system_description: systemDescription,
        incident_report: incidentReport,
        specification: specification,
        operator_feedback: operatorFeedback,
        max_iterations: maxIterations
      })
    })
    if (res.status === 401) {
      logout()
      return null
    }
    const data = await res.json()
    return {
      text: data.prompt || '',
      images: [...systemDescriptionImages, ...incidentReportImages]
    }
  }

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_AGENTS_REPORTS_URL}?agent_type=code_manager`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        setReportHistory(await res.json())
      }
    } catch {
      /* ignore */
    }
  }

  const saveReport = async (report) => {
    try {
      await fetch(API_AGENTS_REPORTS_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          agent_type: 'code_manager',
          report,
          incident_id: selectedIncidentId,
          conversation_history: cleanConversationHistory(conversationHistory),
          model_name: managerModel || undefined
        })
      })
      await fetchHistory()
    } catch {
      /* ignore */
    }
  }

  const deleteReport = async (id) => {
    try {
      await fetch(`${API_AGENTS_REPORTS_URL}/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })
      await fetchHistory()
    } catch {
      /* ignore */
    }
  }

  const deleteAllReports = async () => {
    try {
      await fetch(`${API_AGENTS_REPORTS_URL}?agent_type=code_manager`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })
      await fetchHistory()
    } catch {
      /* ignore */
    }
  }

  useEffect(() => {
    fetchHistory()
  }, [token])

  const toggleEntry = (index) => {
    setExpandedEntries((prev) => ({ ...prev, [index]: !prev[index] }))
  }

  const isAgentBusy = running || executingTool

  const renderFinalReport = (entry, index, isExpanded) => (
    <OrchestratorReport
      key={index}
      entry={entry}
      index={index}
      isExpanded={isExpanded}
      toggleEntry={toggleEntry}
    />
  )

  const renderToolResult = (entry) => {
    if (entry.tool_name === 'run_code_agent' && entry.result?.code_report) {
      const r = entry.result.code_report
      return <CodeReportBody report={r} />
    }
    if (entry.tool_name === 'run_code_reviewer_agent' && entry.result?.review_report) {
      const r = entry.result.review_report
      return <ReviewReportBody report={r} />
    }
    return null
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

      <ul className="nav nav-tabs ia-inner-tabs">
        <li className="nav-item">
          <button
            type="button"
            className={`nav-link${activeTab === 'config' ? ' active' : ''}`}
            onClick={() => setActiveTab('config')}
          >
            Configuration
          </button>
        </li>
        <li className="nav-item">
          <button
            type="button"
            className={`nav-link${activeTab === 'agents' ? ' active' : ''}`}
            onClick={() => setActiveTab('agents')}
          >
            Agents
          </button>
        </li>
        <li className="nav-item">
          <button
            type="button"
            className={`nav-link${activeTab === 'planning' ? ' active' : ''}`}
            onClick={() => setActiveTab('planning')}
          >
            <span className={`status-dot ${isAgentBusy ? 'active' : 'inactive'}`} />
            Planning process
          </button>
        </li>
        <li className="nav-item">
          <button
            type="button"
            className={`nav-link${activeTab === 'history' ? ' active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            History{reportHistory.length > 0 && ` (${reportHistory.length})`}
          </button>
        </li>
      </ul>

      {activeTab === 'config' && (
        <div style={{ marginTop: '16px' }}>
          <div className="ia-description">
            <p>
              This agent coordinates the CodeAgent and CodeReviewerAgent in an automated
              generate-review-revise loop to produce a Gymnasium MDP environment for computing
              optimal incident response policies.
            </p>
          </div>

          <div className="ia-section">
            <label htmlFor="cm-system-desc">System description</label>
            <p className="ia-hint">
              Describe the target system, its architecture, hosts, and services.
            </p>
            <textarea
              id="cm-system-desc"
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
            <label htmlFor="cm-incident-report">Incident report</label>
            <p className="ia-hint">
              Paste the incident report/assessment produced by the Report Agent.
            </p>
            <textarea
              id="cm-incident-report"
              className="form-control ia-textarea"
              rows="6"
              value={incidentReport}
              onChange={(e) => setIncidentReport(e.target.value)}
              disabled={isAgentBusy}
              placeholder="e.g., An SSH brute-force attack was detected on server 3, followed by SQL injection from server 6..."
            />
            <ImageThumbnails
              images={incidentReportImages}
              setImages={setIncidentReportImages}
              disabled={isAgentBusy}
            />
          </div>
          <div className="ia-section">
            <label htmlFor="cm-specification">Specification commands</label>
            <p className="ia-hint">
              JSON array of specification commands that define service-level requirements of the
              system.
            </p>
            <textarea
              id="cm-specification"
              className="form-control ia-textarea"
              rows="4"
              value={specification}
              onChange={(e) => setSpecification(e.target.value)}
              disabled={isAgentBusy}
              placeholder="Leave empty to use default specification commands from the digital twin config."
            />
          </div>
          <div className="ia-section">
            <label htmlFor="cm-operator-feedback">Operator feedback (optional)</label>
            <p className="ia-hint">
              Additional guidance or constraints for the MDP environment design.
            </p>
            <textarea
              id="cm-operator-feedback"
              className="form-control ia-textarea"
              rows="4"
              value={operatorFeedback}
              onChange={(e) => setOperatorFeedback(e.target.value)}
              disabled={isAgentBusy}
              placeholder="e.g., Focus on containment actions first. The firewall rules should be the first actions."
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
          <ExampleSelector onLoad={loadExample} disabled={isAgentBusy} />
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm ia-btn"
            onClick={handleClear}
            disabled={isAgentBusy}
          >
            <i className="fa fa-eraser" aria-hidden="true" /> Clear all
          </button>
          <div className="form-check form-check-inline ia-btn">
            <input
              className="form-check-input"
              type="checkbox"
              id="cm-autopilot"
              checked={autopilot}
              onChange={(e) => setAutopilot(e.target.checked)}
            />
            <label className="form-check-label" htmlFor="cm-autopilot">
              Autopilot <span className="ia-hint">(auto-approve all tool requests)</span>
            </label>
          </div>
        </div>
      )}

      {activeTab === 'agents' && (
        <AgentConfigTable
          models={models}
          isAgentBusy={isAgentBusy}
          token={token}
          getPromptBody={() => ({
            system_description: systemDescription,
            incident_report: incidentReport,
            specification: specification,
            operator_feedback: operatorFeedback
          })}
          rows={[
            {
              label: 'Code Manager',
              model: managerModel,
              setModel: setManagerModel,
              iteration: {
                min: 1,
                max: 10,
                value: maxIterations,
                set: setMaxIterations,
                suffix: 'iterations'
              },
              compaction: compactionThreshold,
              setCompaction: setCompactionThreshold,
              promptUrl: API_AGENTS_CODE_MANAGER_PROMPT_URL
            },
            {
              label: 'Code Agent',
              model: codeAgentModel,
              setModel: setCodeAgentModel,
              promptUrl: API_AGENTS_CODE_PROMPT_URL
            },
            {
              label: 'Code Reviewer',
              model: reviewerAgentModel,
              setModel: setReviewerAgentModel,
              promptUrl: API_AGENTS_CODE_REVIEW_PROMPT_URL
            },
            {
              label: 'Compaction LLM',
              model: compactionModel,
              setModel: setCompactionModel,
              defaultLabel: 'Default (same as agent)'
            }
          ]}
        />
      )}

      {activeTab === 'planning' && (
        <AgentPlanningTab
          running={running}
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
          renderToolResult={renderToolResult}
          onStop={handleStop}
          onViewPrompt={getPromptText}
          dtStatus={dtStatus}
          modelName={managerModel}
          livenessStatus={livenessStatus}
          lastHeartbeatTime={lastHeartbeatRef.current}
          heartbeatStatus={heartbeatStatus}
        />
      )}

      {activeTab === 'history' && (
        <AgentHistoryTab
          reportHistory={reportHistory}
          deleteReport={deleteReport}
          deleteAllReports={deleteAllReports}
          renderReport={(report) => (
            <OrchestratorReport
              entry={{ type: 'orchestrator_report', orchestrator_report: report }}
              index="history"
              isExpanded={true}
              toggleEntry={() => {}}
            />
          )}
          renderFinalReport={renderFinalReport}
          renderToolResult={renderToolResult}
          token={token}
          logout={logout}
        />
      )}
    </div>
  )
}

export default CodeManagerAgent
