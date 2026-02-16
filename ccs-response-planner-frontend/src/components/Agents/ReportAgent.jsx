import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../../contexts/AuthContext.jsx'
import {
  API_EXAMPLES_URL,
  API_AGENTS_REPORT_STEP_URL,
  API_AGENTS_REPORT_TOOL_URL,
  API_AGENTS_REPORT_PROMPT_URL,
  API_LLM_URL,
  API_AGENTS_REPORTS_URL,
  API_DT_PYTHON_STOP_URL
} from '../Common/constants'
import ReportAgentConfigTab from './ReportAgentConfigTab.jsx'
import ReportAgentReport from './ReportAgentReport.jsx'
import AgentConfigTable from './shared/AgentConfigTable.jsx'
import AgentPlanningTab from './shared/AgentPlanningTab.jsx'
import AgentHistoryTab from './shared/AgentHistoryTab.jsx'
import { cleanConversationHistory } from './shared/conversationUtils.js'
import { STREAMING_TOOLS, executeStreamingTool } from './shared/streamingToolExec.js'

/**
 * ReportAgent component — drives the agent loop with
 * human-in-the-loop tool approval. Renders 3 inner tabs.
 */
function ReportAgent() {
  const { token, logout } = useAuth()
  const [activeTab, setActiveTab] = useState('config')
  const [systemDescription, setSystemDescription] = useState('')
  const [securityAlerts, setSecurityAlerts] = useState('')
  const [operatorFeedback, setOperatorFeedback] = useState('')
  const [systemDescriptionImages, setSystemDescriptionImages] = useState([])
  const [securityAlertsImages, setSecurityAlertsImages] = useState([])
  const [operatorFeedbackImages, setOperatorFeedbackImages] = useState([])
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
  const attackPathImageRef = useRef(null)
  const logEndRef = useRef(null)
  const streamingTraceRef = useRef(null)
  const isNearBottomRef = useRef(true)
  const abortControllerRef = useRef(null)

  const handlePaste = (setImages) => (event) => {
    const items = event.clipboardData?.items
    if (!items) return
    for (const item of items) {
      if (item.type.startsWith('image/')) {
        event.preventDefault()
        const file = item.getAsFile()
        const reader = new FileReader()
        reader.onload = (e) => {
          setImages((prev) => [...prev, e.target.result])
        }
        reader.readAsDataURL(file)
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

  const stripImagesFromHistory = (history) =>
    history.map((entry) => {
      if (entry.type === 'tool_result' && entry.result?.image) {
        return {
          ...entry,
          result: { status: 'success', message: 'Attack path image generated successfully' }
        }
      }
      return entry
    })

  const callStep = async (history) => {
    setRunning(true)
    const controller = new AbortController()
    abortControllerRef.current = controller
    const streamingEntry = { role: 'model', type: 'streaming', text: '' }
    const compactionEntries = []
    setConversationHistory([...history, streamingEntry])
    try {
      const res = await fetch(API_AGENTS_REPORT_STEP_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          system_description: systemDescription,
          security_alerts: securityAlerts,
          operator_feedback: operatorFeedback,
          conversation_history: stripImagesFromHistory(history),
          images: [...systemDescriptionImages, ...securityAlertsImages, ...operatorFeedbackImages],
          model_name: selectedModel || undefined,
          compaction_model: compactionModel || undefined,
          compaction_threshold: compactionThreshold / 100,
          last_prompt_tokens: contextUsage?.prompt_tokens || 0
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
          } else if (event.type === 'assessment') {
            finalEntry = {
              role: 'model',
              type: 'assessment',
              assessment: event.assessment,
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
        if (finalEntry.type === 'assessment') {
          if (attackPathImageRef.current) {
            finalEntry.assessment.attack_path_image = attackPathImageRef.current
          }
          saveReport(finalEntry.assessment)
        }
      } else if (accumulated) {
        let assessment
        try {
          assessment = JSON.parse(accumulated)
        } catch {
          assessment = {
            incident_summary: accumulated,
            attack_vector_analysis: '',
            indicators_of_compromise: [],
            severity: 'Unknown',
            severity_justification: '',
            affected_assets: []
          }
        }
        if (attackPathImageRef.current) {
          assessment.attack_path_image = attackPathImageRef.current
        }
        setConversationHistory([
          ...history,
          ...compactionEntries,
          { role: 'model', type: 'assessment', assessment }
        ])
        saveReport(assessment)
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
    attackPathImageRef.current = null
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
          url: API_AGENTS_REPORT_TOOL_URL,
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
      const res = await fetch(API_AGENTS_REPORT_TOOL_URL, {
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
      let resultForHistory = data.error ? { error: data.error } : data.result

      if (proposal.tool_name === 'generate_attack_image' && resultForHistory?.image) {
        attackPathImageRef.current = resultForHistory.image
      }

      const resultEntry = {
        role: 'tool',
        type: 'tool_result',
        tool_name: proposal.tool_name,
        result: resultForHistory
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
      setSecurityAlerts(data.security_alerts || '')
      setOperatorFeedback(data.operator_feedback || '')
      setSystemDescriptionImages(data.system_description_images || [])
      setSecurityAlertsImages([])
      setOperatorFeedbackImages([])
    } catch (err) {
      setAlert({ type: 'danger', message: `Failed to load example: ${err.message}` })
    }
  }

  const handleClear = () => {
    setSystemDescription('')
    setSecurityAlerts('')
    setOperatorFeedback('')
    setSystemDescriptionImages([])
    setSecurityAlertsImages([])
    setOperatorFeedbackImages([])
    setConversationHistory([])
    setPendingProposal(null)
    setExpandedEntries({})
    setSelectedIncidentId(null)
    attackPathImageRef.current = null
  }

  const getPromptText = async () => {
    const res = await fetch(API_AGENTS_REPORT_PROMPT_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({
        system_description: systemDescription,
        security_alerts: securityAlerts,
        operator_feedback: operatorFeedback
      })
    })
    if (res.status === 401) {
      logout()
      return null
    }
    const data = await res.json()
    return {
      text: data.prompt || '',
      images: [...systemDescriptionImages, ...securityAlertsImages, ...operatorFeedbackImages]
    }
  }

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_AGENTS_REPORTS_URL}?agent_type=report`, {
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
    if (attackPathImageRef.current) {
      report.attack_path_image = attackPathImageRef.current
    }
    try {
      await fetch(API_AGENTS_REPORTS_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          agent_type: 'report',
          report,
          incident_id: selectedIncidentId,
          conversation_history: cleanConversationHistory(
            stripImagesFromHistory(conversationHistory)
          ),
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
      await fetch(`${API_AGENTS_REPORTS_URL}?agent_type=report`, {
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
    <ReportAgentReport
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
        <ReportAgentConfigTab
          systemDescription={systemDescription}
          setSystemDescription={setSystemDescription}
          securityAlerts={securityAlerts}
          setSecurityAlerts={setSecurityAlerts}
          operatorFeedback={operatorFeedback}
          setOperatorFeedback={setOperatorFeedback}
          systemDescriptionImages={systemDescriptionImages}
          setSystemDescriptionImages={setSystemDescriptionImages}
          securityAlertsImages={securityAlertsImages}
          setSecurityAlertsImages={setSecurityAlertsImages}
          operatorFeedbackImages={operatorFeedbackImages}
          setOperatorFeedbackImages={setOperatorFeedbackImages}
          handlePaste={handlePaste}
          isAgentBusy={isAgentBusy}
          handleRun={handleRun}
          loadExample={loadExample}
          handleClear={handleClear}
          autopilot={autopilot}
          setAutopilot={setAutopilot}
        />
      )}

      {activeTab === 'agents' && (
        <AgentConfigTable
          models={models}
          isAgentBusy={isAgentBusy}
          token={token}
          getPromptBody={() => ({
            system_description: systemDescription,
            security_alerts: securityAlerts,
            operator_feedback: operatorFeedback
          })}
          rows={[
            {
              label: 'Report Agent',
              model: selectedModel,
              setModel: setSelectedModel,
              promptUrl: API_AGENTS_REPORT_PROMPT_URL,
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
          modelName={selectedModel}
          dtStatus={dtStatus}
        />
      )}

      {activeTab === 'history' && (
        <AgentHistoryTab
          reportHistory={reportHistory}
          deleteReport={deleteReport}
          deleteAllReports={deleteAllReports}
          renderReport={(report) => (
            <ReportAgentReport
              entry={{ type: 'assessment', assessment: report }}
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

export default ReportAgent
