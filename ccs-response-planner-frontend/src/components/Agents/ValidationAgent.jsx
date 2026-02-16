import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../../contexts/AuthContext.jsx'
import {
  API_EXAMPLES_URL,
  API_AGENTS_VALIDATION_STEP_URL,
  API_AGENTS_VALIDATION_TOOL_URL,
  API_AGENTS_VALIDATION_PROMPT_URL,
  API_LLM_URL,
  API_AGENTS_REPORTS_URL,
  API_DT_PYTHON_STOP_URL
} from '../Common/constants'
import ValidationAgentConfigTab from './ValidationAgentConfigTab.jsx'
import ValidationAgentReport from './ValidationAgentReport.jsx'
import AgentConfigTable from './shared/AgentConfigTable.jsx'
import AgentPlanningTab from './shared/AgentPlanningTab.jsx'
import AgentHistoryTab from './shared/AgentHistoryTab.jsx'
import { cleanConversationHistory } from './shared/conversationUtils.js'
import { STREAMING_TOOLS, executeStreamingTool } from './shared/streamingToolExec.js'

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
  const [codeReport, setCodeReport] = useState('')
  const [plannerReport, setPlannerReport] = useState('')
  const [systemDescriptionImages, setSystemDescriptionImages] = useState([])
  const [incidentReportImages, setIncidentReportImages] = useState([])
  const [conversationHistory, setConversationHistory] = useState([])
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
  const [selectedModel, setSelectedModel] = useState('')
  const [compactionModel, setCompactionModel] = useState('')
  const [compactionThreshold, setCompactionThreshold] = useState(80)
  const [reportHistory, setReportHistory] = useState([])
  const [selectedIncidentId, setSelectedIncidentId] = useState(null)
  const [plannerReportId, setPlannerReportId] = useState(null)
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
      return [
        ...cleaned,
        { role: 'system', type: 'error', message: 'Planning process stopped by user.' }
      ]
    })
  }

  const callStep = async (history) => {
    setRunning(true)
    const controller = new AbortController()
    abortControllerRef.current = controller
    const streamingEntry = { role: 'model', type: 'streaming', text: '' }
    const compactionEntries = []
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
          code_report: codeReport,
          planner_report: plannerReport,
          conversation_history: history,
          images: [...systemDescriptionImages, ...incidentReportImages],
          model_name: selectedModel || undefined,
          compaction_model: compactionModel || undefined,
          compaction_threshold: compactionThreshold / 100,
          last_prompt_tokens: contextUsage?.prompt_tokens || 0,
          planner_report_id: plannerReportId || undefined
        }),
        signal: controller.signal
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
          } else if (event.type === 'validation_report') {
            finalEntry = {
              role: 'model',
              type: 'validation_report',
              validation_report: event.validation_report,
              thinking_trace: event.thinking_trace || ''
            }
          } else if (event.type === 'dt_progress') {
            setDtStatus(event.message)
          } else if (event.type === 'policy_loaded') {
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
        const updated = [...history, ...compactionEntries, ...entries]
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
            recommendations: [],
            actual_total_cost: 0,
            simulated_total_cost: 0
          }
        }
        setConversationHistory([
          ...history,
          ...compactionEntries,
          { role: 'model', type: 'validation_report', validation_report: report }
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
      const streamEntry = { type: 'tool_streaming', tool_name: proposal.tool_name, output: '' }
      const base = [...conversationHistory, approvalEntry, streamEntry]
      setConversationHistory(base)
      try {
        const { result } = await executeStreamingTool({
          url: API_AGENTS_VALIDATION_TOOL_URL,
          toolName: proposal.tool_name,
          toolArgs: proposal.tool_args,
          incidentId: selectedIncidentId,
          token,
          signal: controller.signal,
          onChunk: (text) => {
            streamEntry.output += text
            setConversationHistory([...base])
          }
        })
        const resultEntry = {
          role: 'tool',
          type: 'tool_result',
          tool_name: proposal.tool_name,
          result
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
      const res = await fetch(API_AGENTS_VALIDATION_TOOL_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          tool_name: proposal.tool_name,
          tool_args: proposal.tool_args,
          incident_id: selectedIncidentId
        }),
        signal: controller.signal
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
      setResponsePlan(data.response_plan || '')
      setSpecification(data.specification || '')
      setSystemDescriptionImages(data.system_description_images || [])

      // Fetch latest Code Agent report for this incident
      const codeRes = await fetch(
        `${API_AGENTS_REPORTS_URL}?agent_type=code&incident_id=${incidentId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      if (codeRes.ok) {
        const codeReports = await codeRes.json()
        if (codeReports.length > 0) {
          setCodeReport(JSON.stringify(codeReports[0].report || {}, null, 2))
        }
      }

      // Fetch latest RL Agent report for this incident
      const plannerRes = await fetch(
        `${API_AGENTS_REPORTS_URL}?agent_type=rl&incident_id=${incidentId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      if (plannerRes.ok) {
        const plannerReports = await plannerRes.json()
        if (plannerReports.length > 0) {
          setPlannerReport(JSON.stringify(plannerReports[0].report || {}, null, 2))
          if (plannerReports[0].has_policy) {
            setPlannerReportId(plannerReports[0].id)
          } else {
            setPlannerReportId(null)
          }
        }
      }

      // Fetch latest Report Agent report for this incident
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
    setResponsePlan('')
    setSpecification('')
    setCodeReport('')
    setPlannerReport('')
    setSystemDescriptionImages([])
    setIncidentReportImages([])
    setConversationHistory([])
    setPendingProposal(null)
    setExpandedEntries({})
    setSelectedIncidentId(null)
    setPlannerReportId(null)
  }

  const getPromptText = async () => {
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
        specification: specification,
        code_report: codeReport,
        planner_report: plannerReport
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
        body: JSON.stringify({
          agent_type: 'validation',
          report,
          incident_id: selectedIncidentId,
          conversation_history: cleanConversationHistory(conversationHistory),
          model_name: selectedModel || undefined
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
      await fetch(`${API_AGENTS_REPORTS_URL}?agent_type=validation`, {
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
        <ValidationAgentConfigTab
          systemDescription={systemDescription}
          setSystemDescription={setSystemDescription}
          incidentReport={incidentReport}
          setIncidentReport={setIncidentReport}
          responsePlan={responsePlan}
          setResponsePlan={setResponsePlan}
          specification={specification}
          setSpecification={setSpecification}
          codeReport={codeReport}
          setCodeReport={setCodeReport}
          plannerReport={plannerReport}
          setPlannerReport={setPlannerReport}
          systemDescriptionImages={systemDescriptionImages}
          setSystemDescriptionImages={setSystemDescriptionImages}
          incidentReportImages={incidentReportImages}
          setIncidentReportImages={setIncidentReportImages}
          handlePaste={handlePaste}
          isAgentBusy={isAgentBusy}
          handleRun={handleRun}
          loadExample={loadExample}
          handleClear={handleClear}
          autopilot={autopilot}
          setAutopilot={setAutopilot}
          plannerReportId={plannerReportId}
        />
      )}

      {activeTab === 'agents' && (
        <AgentConfigTable
          models={models}
          isAgentBusy={isAgentBusy}
          token={token}
          getPromptBody={() => ({
            system_description: systemDescription,
            incident_report: incidentReport,
            response_plan: responsePlan,
            specification: specification,
            code_report: codeReport,
            planner_report: plannerReport
          })}
          rows={[
            {
              label: 'Validation Agent',
              model: selectedModel,
              setModel: setSelectedModel,
              promptUrl: API_AGENTS_VALIDATION_PROMPT_URL,
              iteration: null,
              compaction: compactionThreshold,
              setCompaction: setCompactionThreshold
            },
            {
              label: 'Compaction LLM',
              model: compactionModel,
              setModel: setCompactionModel,
              promptUrl: null,
              iteration: null,
              compaction: null,
              setCompaction: null,
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
          onStop={handleStop}
          onViewPrompt={getPromptText}
          dtStatus={dtStatus}
          modelName={selectedModel}
        />
      )}

      {activeTab === 'history' && (
        <AgentHistoryTab
          reportHistory={reportHistory}
          deleteReport={deleteReport}
          deleteAllReports={deleteAllReports}
          renderReport={(report) => (
            <ValidationAgentReport
              entry={{ type: 'validation_report', validation_report: report }}
              index="history"
              isExpanded={true}
              toggleEntry={() => {}}
            />
          )}
          renderFinalReport={renderFinalReport}
          token={token}
          logout={logout}
        />
      )}
    </div>
  )
}

export default ValidationAgent
