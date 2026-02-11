import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../../contexts/AuthContext.jsx'
import {
  API_EXAMPLE_URL,
  API_AGENTS_VALIDATION_STEP_URL,
  API_AGENTS_VALIDATION_TOOL_URL,
  API_AGENTS_VALIDATION_PROMPT_URL,
  API_LLM_URL,
  API_AGENTS_REPORTS_URL
} from '../Common/constants'
import ValidationAgentConfigTab from './ValidationAgentConfigTab.jsx'
import ValidationAgentReport from './ValidationAgentReport.jsx'
import AgentPlanningTab from './shared/AgentPlanningTab.jsx'
import AgentHistoryTab from './shared/AgentHistoryTab.jsx'

/**
 * ValidationAgent component — drives the validation agent loop with
 * human-in-the-loop tool approval. Renders 3 inner tabs.
 */
function ValidationAgent() {
  const { token, logout } = useAuth()
  const [activeTab, setActiveTab] = useState('config')
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
  const [autopilot, setAutopilot] = useState(true)
  const [hasNewActivity, setHasNewActivity] = useState(false)
  const [contextUsage, setContextUsage] = useState(null)
  const [models, setModels] = useState([])
  const [selectedModel, setSelectedModel] = useState('')
  const [reportHistory, setReportHistory] = useState([])
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
    const logEl = logContainerRef.current
    const logBottomVisible =
      logEl && logEl.getBoundingClientRect().bottom <= window.innerHeight + 80
    if (isNearBottomRef.current && logBottomVisible) {
      if (logEl) {
        logEl.scrollTop = logEl.scrollHeight
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
          images: systemDescriptionImages,
          model_name: selectedModel || undefined
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
        if (finalEntry.type === 'validation_report') {
          saveReport(finalEntry.validation_report)
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
        saveReport(report)
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

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_AGENTS_REPORTS_URL}?agent_type=validation`, {
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
        body: JSON.stringify({ agent_type: 'validation', report })
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
    <ValidationAgentReport
      key={index}
      entry={entry}
      index={index}
      isExpanded={isExpanded}
      toggleEntry={toggleEntry}
    />
  )

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
        <ValidationAgentConfigTab
          systemDescription={systemDescription}
          setSystemDescription={setSystemDescription}
          incidentReport={incidentReport}
          setIncidentReport={setIncidentReport}
          responsePlan={responsePlan}
          setResponsePlan={setResponsePlan}
          specification={specification}
          setSpecification={setSpecification}
          systemDescriptionImages={systemDescriptionImages}
          setSystemDescriptionImages={setSystemDescriptionImages}
          handlePaste={handlePaste}
          isAgentBusy={isAgentBusy}
          handleRun={handleRun}
          fetchExample={fetchExample}
          handleClear={handleClear}
          fetchPrompt={fetchPrompt}
          loadingPrompt={loadingPrompt}
          models={models}
          selectedModel={selectedModel}
          setSelectedModel={setSelectedModel}
          autopilot={autopilot}
          setAutopilot={setAutopilot}
          showPromptModal={showPromptModal}
          promptText={promptText}
          setShowPromptModal={setShowPromptModal}
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
          logContainerRef={logContainerRef}
          logEndRef={logEndRef}
          streamingTraceRef={streamingTraceRef}
          handleLogScroll={handleLogScroll}
          renderFinalReport={renderFinalReport}
        />
      )}

      {activeTab === 'history' && (
        <AgentHistoryTab reportHistory={reportHistory} deleteReport={deleteReport} />
      )}
    </div>
  )
}

export default ValidationAgent
