import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../../contexts/AuthContext.jsx'
import {
  API_EXAMPLES_URL,
  API_AGENTS_PLAN_MANAGER_STEP_URL,
  API_AGENTS_PLAN_MANAGER_TOOL_URL,
  API_AGENTS_PLAN_MANAGER_PROMPT_URL,
  API_LLM_URL,
  API_AGENTS_REPORTS_URL,
  API_DT_PYTHON_STOP_URL
} from '../Common/constants'
import ImageThumbnails from './shared/ImageThumbnails.jsx'
import PromptModal from './shared/PromptModal.jsx'
import ExampleSelector from './shared/ExampleSelector.jsx'
import AgentPlanningTab from './shared/AgentPlanningTab.jsx'
import AgentHistoryTab from './shared/AgentHistoryTab.jsx'
import { cleanConversationHistory } from './shared/conversationUtils.js'
import { STREAMING_TOOLS, executeStreamingTool } from './shared/streamingToolExec.js'

const VERDICT_STYLES = { pass: 'success', needs_revision: 'warning', major_issues: 'danger' }

/**
 * Helper to push a nested_event into the correct level of the subEvents tree.
 */
function handleNestedSubEvent(subEvents, innerEvent) {
  if (innerEvent.type === 'context_usage') {
    const lastToolCall = [...subEvents]
      .reverse()
      .find((e) => e.type === 'tool_call' && !e._completed)
    if (lastToolCall) lastToolCall._contextUsage = innerEvent
    return
  }
  if (innerEvent.type === 'thinking_delta') {
    const last = subEvents[subEvents.length - 1]
    if (last && last.type === 'reasoning') {
      last.text += innerEvent.text
    } else {
      subEvents.push({ type: 'reasoning', text: innerEvent.text })
    }
  } else if (innerEvent.type === 'text_delta') {
    const last = subEvents[subEvents.length - 1]
    if (last && last.type === 'text') {
      last.text += innerEvent.text
    } else {
      subEvents.push({ type: 'text', text: innerEvent.text })
    }
  } else if (innerEvent.type === 'nested_event') {
    const lastToolCall = [...subEvents]
      .reverse()
      .find((e) => e.type === 'tool_call' && !e._completed)
    if (lastToolCall) {
      if (innerEvent.event.type === 'prompt') {
        lastToolCall._prompt = innerEvent.event.text
      } else {
        if (!lastToolCall.subEvents) lastToolCall.subEvents = []
        handleNestedSubEvent(lastToolCall.subEvents, innerEvent.event)
      }
    }
  } else if (innerEvent.type === 'tool_result') {
    const lastCall = [...subEvents].reverse().find((e) => e.type === 'tool_call')
    if (lastCall) lastCall._completed = true
    subEvents.push({
      type: 'tool_result',
      tool_name: innerEvent.tool_name,
      result: innerEvent.result,
      subEvents: innerEvent.subEvents || []
    })
  } else {
    subEvents.push(innerEvent)
  }
}

/**
 * Render a plan manager report entry.
 */
function PlanManagerReport({ entry, index, isExpanded, toggleEntry }) {
  const report = entry.plan_manager_report || {}
  const verdictClass =
    report.final_verdict === 'pass'
      ? 'badge-success'
      : report.final_verdict === 'needs_revision'
        ? 'badge-warning'
        : 'badge-danger'

  return (
    <div className="card ia-entry ia-result-entry">
      <div className="card-body">
        <div className="ia-result-header" onClick={() => toggleEntry(index)}>
          <i className="fa fa-flag-checkered" aria-hidden="true" />
          <span className="ia-result-label">Plan Manager Report</span>
          {report.final_verdict && (
            <span className={`badge ${verdictClass} ml-2`}>{report.final_verdict}</span>
          )}
          {report.iterations != null && (
            <span className="badge badge-info ml-2">{report.iterations} iteration(s)</span>
          )}
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
            {report.code_manager_summary && (
              <div className="mb-3">
                <strong>Code Manager Summary:</strong>
                <p>{report.code_manager_summary}</p>
              </div>
            )}
            {report.rl_agent_summary && (
              <div className="mb-3">
                <strong>RL Agent Summary:</strong>
                <p>{report.rl_agent_summary}</p>
              </div>
            )}
            {report.validation_summary && (
              <div className="mb-3">
                <strong>Validation Summary:</strong>
                <p>{report.validation_summary}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * PlanManagerAgent component — orchestrates the full incident response pipeline:
 * CodeManager -> RL Agent -> Validation Agent with iterative revision.
 */
function PlanManagerAgent() {
  const { token, logout } = useAuth()
  const [activeTab, setActiveTab] = useState('config')
  const [systemDescription, setSystemDescription] = useState('')
  const [incidentReport, setIncidentReport] = useState('')
  const [specification, setSpecification] = useState('')
  const [operatorFeedback, setOperatorFeedback] = useState('')
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
  const [autopilot, setAutopilot] = useState(true)
  const [hasNewActivity, setHasNewActivity] = useState(false)
  const [contextUsage, setContextUsage] = useState(null)
  const [dtStatus, setDtStatus] = useState(null)
  const [models, setModels] = useState([])
  const [maxIterations, setMaxIterations] = useState(2)
  const [managerModel, setManagerModel] = useState('')
  const [codeManagerModel, setCodeManagerModel] = useState('')
  const [codeAgentModel, setCodeAgentModel] = useState('')
  const [reviewerAgentModel, setReviewerAgentModel] = useState('')
  const [rlAgentModel, setRlAgentModel] = useState('')
  const [validationAgentModel, setValidationAgentModel] = useState('')
  const [reportHistory, setReportHistory] = useState([])
  const [selectedIncidentId, setSelectedIncidentId] = useState(null)
  const logEndRef = useRef(null)
  const streamingTraceRef = useRef(null)
  const isNearBottomRef = useRef(true)
  const abortControllerRef = useRef(null)

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

  const callStep = async (history) => {
    setRunning(true)
    const controller = new AbortController()
    abortControllerRef.current = controller
    const streamingIdx = history.length
    const streamingEntry = { role: 'model', type: 'streaming', text: '' }
    setConversationHistory([...history, streamingEntry])
    try {
      const res = await fetch(API_AGENTS_PLAN_MANAGER_STEP_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        signal: controller.signal,
        body: JSON.stringify({
          system_description: systemDescription,
          incident_report: incidentReport,
          specification: specification,
          operator_feedback: operatorFeedback,
          conversation_history: history,
          images: systemDescriptionImages,
          model_name: managerModel || undefined,
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
              _model_parts: event._model_parts,
              _anthropic_content: event._anthropic_content,
              _tool_use_id: event._tool_use_id,
              _vendor: event._vendor
            }
          } else if (event.type === 'plan_manager_report') {
            finalEntry = {
              role: 'model',
              type: 'plan_manager_report',
              plan_manager_report: event.plan_manager_report,
              thinking_trace: event.thinking_trace || ''
            }
          } else if (event.type === 'dt_progress') {
            setDtStatus(event.message)
          } else if (event.type === 'context_usage') {
            setContextUsage(event)
          } else if (event.type === 'error') {
            const msg = event.message || 'Agent stream error'
            setAlert({ type: 'danger', message: msg })
            setConversationHistory([...history, { role: 'system', type: 'error', message: msg }])
            return
          }
        }
      }

      setDtStatus(null)
      if (finalEntry) {
        const entries = []
        const reasoningText = finalEntry.thinking_trace || accumulated
        if (reasoningText) {
          entries.push({ role: 'model', type: 'reasoning', text: reasoningText })
        }
        entries.push(finalEntry)
        const updated = [...history, ...entries]
        setConversationHistory(updated)
        if (finalEntry.type === 'tool_proposal') {
          setPendingProposal(finalEntry)
        }
        if (finalEntry.type === 'plan_manager_report') {
          saveReport(finalEntry.plan_manager_report)
        }
      } else if (accumulated) {
        let report
        try {
          report = JSON.parse(accumulated)
        } catch {
          report = {
            executive_summary: accumulated,
            iterations: 0,
            final_verdict: 'unknown',
            code_manager_summary: '',
            rl_agent_summary: '',
            validation_summary: ''
          }
        }
        setConversationHistory([
          ...history,
          {
            role: 'model',
            type: 'plan_manager_report',
            plan_manager_report: report
          }
        ])
        saveReport(report)
      } else {
        setConversationHistory([
          ...history,
          { role: 'system', type: 'error', message: 'Agent returned an empty response.' }
        ])
      }
    } catch (err) {
      if (err.name === 'AbortError') return
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
    setContextUsage(null)
    setActiveTab('planning')
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
      const streamEntry = {
        type: 'tool_streaming',
        tool_name: proposal.tool_name,
        output: '',
        subEvents: [],
        _startTime: Date.now()
      }
      const base = [...conversationHistory, approvalEntry, streamEntry]
      setConversationHistory(base)
      try {
        const extraBody = {
          system_description: systemDescription,
          incident_report: incidentReport,
          specification: specification,
          operator_feedback: operatorFeedback,
          images: systemDescriptionImages,
          conversation_history: conversationHistory,
          code_manager_model: codeManagerModel || undefined,
          code_agent_model: codeAgentModel || undefined,
          reviewer_agent_model: reviewerAgentModel || undefined,
          rl_agent_model: rlAgentModel || undefined,
          validation_agent_model: validationAgentModel || undefined
        }
        const { result } = await executeStreamingTool({
          url: API_AGENTS_PLAN_MANAGER_TOOL_URL,
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
              setConversationHistory([...base])
              return
            }
            if (event.type === 'thinking_delta') {
              const last = streamEntry.subEvents[streamEntry.subEvents.length - 1]
              if (last && last.type === 'reasoning') {
                last.text += event.text
              } else {
                streamEntry.subEvents.push({ type: 'reasoning', text: event.text })
              }
            } else if (event.type === 'text_delta') {
              const last = streamEntry.subEvents[streamEntry.subEvents.length - 1]
              if (last && last.type === 'text') {
                last.text += event.text
              } else {
                streamEntry.subEvents.push({ type: 'text', text: event.text })
              }
            } else if (event.type === 'nested_event') {
              const lastToolCall = [...streamEntry.subEvents]
                .reverse()
                .find((e) => e.type === 'tool_call' && !e._completed)
              if (lastToolCall) {
                if (event.event.type === 'prompt') {
                  lastToolCall._prompt = event.event.text
                } else {
                  if (!lastToolCall.subEvents) lastToolCall.subEvents = []
                  handleNestedSubEvent(lastToolCall.subEvents, event.event)
                }
              }
            } else if (event.type === 'tool_result') {
              const lastCall = [...streamEntry.subEvents]
                .reverse()
                .find((e) => e.type === 'tool_call')
              if (lastCall) lastCall._completed = true
              streamEntry.subEvents.push({
                type: 'tool_result',
                tool_name: event.tool_name,
                result: event.result,
                subEvents: event.subEvents || []
              })
            } else {
              streamEntry.subEvents.push(event)
            }
            setConversationHistory([...base])
          },
          extraBody
        })
        const resultEntry = {
          role: 'tool',
          type: 'tool_result',
          tool_name: proposal.tool_name,
          result,
          subEvents: streamEntry.subEvents,
          prompt: streamEntry.prompt,
          contextUsage: streamEntry.contextUsage
        }
        const updated = [...conversationHistory, approvalEntry, resultEntry]
        setConversationHistory(updated)
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
      const res = await fetch(API_AGENTS_PLAN_MANAGER_TOOL_URL, {
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
      const updated = [...conversationHistory, approvalEntry, resultEntry]
      setConversationHistory(updated)
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
    const updated = [...conversationHistory, denialEntry]
    setConversationHistory(updated)
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
        `${API_AGENTS_REPORTS_URL}?agent_type=information&incident_id=${incidentId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      if (infoRes.ok) {
        const infoReports = await infoRes.json()
        if (infoReports.length > 0) {
          const { attack_path_image, ...reportText } = infoReports[0].report || {}
          void attack_path_image
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
    setConversationHistory([])
    setPendingProposal(null)
    setExpandedEntries({})
    setSelectedIncidentId(null)
  }

  const getPromptText = async () => {
    const res = await fetch(API_AGENTS_PLAN_MANAGER_PROMPT_URL, {
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
    return data.prompt || ''
  }

  const fetchPrompt = async () => {
    setLoadingPrompt(true)
    try {
      const text = await getPromptText()
      if (text != null) {
        setPromptText(text)
        setShowPromptModal(true)
      }
    } catch (err) {
      setAlert({ type: 'danger', message: `Failed to fetch prompt: ${err.message}` })
    } finally {
      setLoadingPrompt(false)
    }
  }

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_AGENTS_REPORTS_URL}?agent_type=plan_manager`, {
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
          agent_type: 'plan_manager',
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

  useEffect(() => {
    fetchHistory()
  }, [token])

  const toggleEntry = (index) => {
    setExpandedEntries((prev) => ({ ...prev, [index]: !prev[index] }))
  }

  const isAgentBusy = running || executingTool

  const renderFinalReport = (entry, index, isExpanded) => (
    <PlanManagerReport
      key={index}
      entry={entry}
      index={index}
      isExpanded={isExpanded}
      toggleEntry={toggleEntry}
    />
  )

  const renderToolResult = (entry) => {
    if (entry.tool_name === 'run_code_manager' && entry.result) {
      const r = entry.result
      return (
        <div style={{ marginTop: '10px' }}>
          {r.orchestrator_report?.executive_summary && (
            <div className="ia-assessment-section">
              <div className="ia-assessment-label">Code Manager Summary</div>
              <p className="ia-assessment-body mb-0">{r.orchestrator_report.executive_summary}</p>
            </div>
          )}
          {r.orchestrator_report?.final_verdict && (
            <div className="ia-assessment-section">
              <div className="ia-assessment-label">Verdict</div>
              <span
                className={`badge badge-${VERDICT_STYLES[r.orchestrator_report.final_verdict] || 'secondary'}`}
                style={{ fontSize: '12px', padding: '5px 8px' }}
              >
                {r.orchestrator_report.final_verdict.replace(/_/g, ' ')}
              </span>
            </div>
          )}
        </div>
      )
    }
    if (entry.tool_name === 'run_rl_agent' && entry.result) {
      const r = entry.result
      return (
        <div style={{ marginTop: '10px' }}>
          {r.planner_report?.executive_summary && (
            <div className="ia-assessment-section">
              <div className="ia-assessment-label">RL Agent Summary</div>
              <p className="ia-assessment-body mb-0">{r.planner_report.executive_summary}</p>
            </div>
          )}
          {r.response_plan && (
            <div className="ia-assessment-section">
              <div className="ia-assessment-label">Response Plan</div>
              <pre
                style={{
                  background: '#f5f5f5',
                  padding: '12px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  maxHeight: '300px',
                  overflow: 'auto',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word'
                }}
              >
                {r.response_plan}
              </pre>
            </div>
          )}
        </div>
      )
    }
    if (entry.tool_name === 'run_validation_agent' && entry.result) {
      const r = entry.result
      return (
        <div style={{ marginTop: '10px' }}>
          {r.validation_report?.executive_summary && (
            <div className="ia-assessment-section">
              <div className="ia-assessment-label">Validation Summary</div>
              <p className="ia-assessment-body mb-0">{r.validation_report.executive_summary}</p>
            </div>
          )}
          {r.validation_report?.overall_verdict && (
            <div className="ia-assessment-section">
              <div className="ia-assessment-label">Verdict</div>
              <span
                className={`badge badge-${VERDICT_STYLES[r.validation_report.overall_verdict] || 'secondary'}`}
                style={{ fontSize: '12px', padding: '5px 8px' }}
              >
                {r.validation_report.overall_verdict.replace(/_/g, ' ')}
              </span>
            </div>
          )}
        </div>
      )
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
            className={`nav-link${activeTab === 'planning' ? ' active' : ''}`}
            onClick={() => setActiveTab('planning')}
          >
            <span className={`status-dot ${isAgentBusy ? 'active' : 'inactive'}`} />
            Pipeline process
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
              This agent orchestrates the full incident response pipeline: CodeManager (MDP
              generation) -&gt; RL Agent (policy training) -&gt; Validation Agent (digital twin
              testing). It iteratively revises the pipeline until the response plan passes
              validation or the iteration limit is reached.
            </p>
          </div>

          <div className="ia-section">
            <label htmlFor="pm-system-desc">System description</label>
            <p className="ia-hint">
              Describe the target system, its architecture, hosts, and services.
            </p>
            <textarea
              id="pm-system-desc"
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
            <label htmlFor="pm-incident-report">Incident report</label>
            <p className="ia-hint">
              Paste the incident report/assessment produced by the Information Agent.
            </p>
            <textarea
              id="pm-incident-report"
              className="form-control ia-textarea"
              rows="6"
              value={incidentReport}
              onChange={(e) => setIncidentReport(e.target.value)}
              disabled={isAgentBusy}
              placeholder="e.g., An SSH brute-force attack was detected on server 3..."
            />
          </div>
          <div className="ia-section">
            <label htmlFor="pm-specification">Specification commands</label>
            <p className="ia-hint">
              JSON array of specification commands that define service-level requirements.
            </p>
            <textarea
              id="pm-specification"
              className="form-control ia-textarea"
              rows="4"
              value={specification}
              onChange={(e) => setSpecification(e.target.value)}
              disabled={isAgentBusy}
              placeholder="Leave empty to use default specification commands from the digital twin config."
            />
          </div>
          <div className="ia-section">
            <label htmlFor="pm-operator-feedback">Operator feedback (optional)</label>
            <p className="ia-hint">Additional guidance or constraints for the pipeline.</p>
            <textarea
              id="pm-operator-feedback"
              className="form-control ia-textarea"
              rows="4"
              value={operatorFeedback}
              onChange={(e) => setOperatorFeedback(e.target.value)}
              disabled={isAgentBusy}
              placeholder="e.g., Focus on containment actions first."
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
          <button
            type="button"
            className="btn btn-outline-dark btn-sm ia-btn"
            onClick={fetchPrompt}
            disabled={loadingPrompt}
          >
            <i className="fa fa-file-text-o" aria-hidden="true" />{' '}
            {loadingPrompt ? 'Loading...' : 'Show prompt'}
          </button>
          <span className="ia-model-label">Max iterations:</span>
          <input
            type="number"
            className="form-control form-control-sm"
            style={{ width: '70px', display: 'inline-block' }}
            min={1}
            max={5}
            value={maxIterations}
            onChange={(e) => {
              const v = parseInt(e.target.value, 10)
              if (v >= 1 && v <= 5) setMaxIterations(v)
            }}
            disabled={isAgentBusy}
          />
          <span className="ia-model-label">Plan Manager LLM:</span>
          <select
            className="form-control form-control-sm ia-model-select"
            value={managerModel}
            onChange={(e) => setManagerModel(e.target.value)}
            disabled={isAgentBusy}
          >
            <option value="">Default (Gemini 3 Pro)</option>
            {models.map((m) => (
              <option key={m.name} value={m.name}>
                {m.display_name}
              </option>
            ))}
          </select>
          <span className="ia-model-label">Code Manager LLM:</span>
          <select
            className="form-control form-control-sm ia-model-select"
            value={codeManagerModel}
            onChange={(e) => setCodeManagerModel(e.target.value)}
            disabled={isAgentBusy}
          >
            <option value="">Default (Gemini 3 Pro)</option>
            {models.map((m) => (
              <option key={m.name} value={m.name}>
                {m.display_name}
              </option>
            ))}
          </select>
          <span className="ia-model-label">Code Agent LLM:</span>
          <select
            className="form-control form-control-sm ia-model-select"
            value={codeAgentModel}
            onChange={(e) => setCodeAgentModel(e.target.value)}
            disabled={isAgentBusy}
          >
            <option value="">Default (Gemini 3 Pro)</option>
            {models.map((m) => (
              <option key={m.name} value={m.name}>
                {m.display_name}
              </option>
            ))}
          </select>
          <span className="ia-model-label">Reviewer Agent LLM:</span>
          <select
            className="form-control form-control-sm ia-model-select"
            value={reviewerAgentModel}
            onChange={(e) => setReviewerAgentModel(e.target.value)}
            disabled={isAgentBusy}
          >
            <option value="">Default (Gemini 3 Pro)</option>
            {models.map((m) => (
              <option key={m.name} value={m.name}>
                {m.display_name}
              </option>
            ))}
          </select>
          <span className="ia-model-label">RL Agent LLM:</span>
          <select
            className="form-control form-control-sm ia-model-select"
            value={rlAgentModel}
            onChange={(e) => setRlAgentModel(e.target.value)}
            disabled={isAgentBusy}
          >
            <option value="">Default (Gemini 3 Pro)</option>
            {models.map((m) => (
              <option key={m.name} value={m.name}>
                {m.display_name}
              </option>
            ))}
          </select>
          <span className="ia-model-label">Validation Agent LLM:</span>
          <select
            className="form-control form-control-sm ia-model-select"
            value={validationAgentModel}
            onChange={(e) => setValidationAgentModel(e.target.value)}
            disabled={isAgentBusy}
          >
            <option value="">Default (Gemini 3 Pro)</option>
            {models.map((m) => (
              <option key={m.name} value={m.name}>
                {m.display_name}
              </option>
            ))}
          </select>
          <div className="form-check form-check-inline ia-btn">
            <input
              className="form-check-input"
              type="checkbox"
              id="pm-autopilot"
              checked={autopilot}
              onChange={(e) => setAutopilot(e.target.checked)}
            />
            <label className="form-check-label" htmlFor="pm-autopilot">
              Autopilot <span className="ia-hint">(auto-approve all tool requests)</span>
            </label>
          </div>

          <PromptModal
            show={showPromptModal}
            promptText={promptText}
            onClose={() => setShowPromptModal(false)}
          />
        </div>
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
        />
      )}

      {activeTab === 'history' && (
        <AgentHistoryTab
          reportHistory={reportHistory}
          deleteReport={deleteReport}
          renderReport={(report) => (
            <PlanManagerReport
              entry={{ type: 'plan_manager_report', plan_manager_report: report }}
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

export default PlanManagerAgent
