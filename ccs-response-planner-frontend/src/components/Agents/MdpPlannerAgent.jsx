import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../../contexts/AuthContext.jsx'
import {
  API_EXAMPLES_URL,
  API_AGENTS_MDP_PLANNER_STEP_URL,
  API_AGENTS_MDP_PLANNER_TOOL_URL,
  API_AGENTS_MDP_PLANNER_PROMPT_URL,
  API_LLM_URL,
  API_AGENTS_REPORTS_URL
} from '../Common/constants'
import MdpPlannerConfigTab from './MdpPlannerConfigTab.jsx'
import MdpPlannerReport from './MdpPlannerReport.jsx'
import RewardChart from './RewardChart.jsx'
import RlTrainResult from './RlTrainResult.jsx'
import AgentPlanningTab from './shared/AgentPlanningTab.jsx'
import AgentHistoryTab from './shared/AgentHistoryTab.jsx'

/**
 * MdpPlannerAgent component — drives the MDP planner agent loop with
 * human-in-the-loop tool approval and live RL training visualization.
 */
function MdpPlannerAgent() {
  const { token, logout } = useAuth()
  const [activeTab, setActiveTab] = useState('config')
  const [systemDescription, setSystemDescription] = useState('')
  const [incidentReport, setIncidentReport] = useState('')
  const [specification, setSpecification] = useState('')
  const [operatorFeedback, setOperatorFeedback] = useState('')
  const [codeReport, setCodeReport] = useState('')
  const [timeLimitMinutes, setTimeLimitMinutes] = useState(5)
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
  const [trainingData, setTrainingData] = useState([])
  const [trainingMeta, setTrainingMeta] = useState({ algorithm: '', hyperparameters: '' })
  const [trainingStartTime, setTrainingStartTime] = useState(null)
  const [selectedIncidentId, setSelectedIncidentId] = useState(null)
  const logEndRef = useRef(null)
  const streamingTraceRef = useRef(null)
  const isNearBottomRef = useRef(true)
  const trainingRunsRef = useRef({})
  const runIdCounterRef = useRef(0)
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
    if (isNearBottomRef.current) {
      window.scrollTo({ top: document.body.scrollHeight, behavior: 'auto' })
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
    setRunning(false)
    setExecutingTool(null)
    setPendingProposal(null)
    setTrainingStartTime(null)
    setConversationHistory((prev) => [
      ...prev,
      { role: 'system', type: 'error', message: 'Planning process stopped by user.' }
    ])
  }

  const callStep = async (history) => {
    setRunning(true)
    const streamingIdx = history.length
    const streamingEntry = { role: 'model', type: 'streaming', text: '' }
    setConversationHistory([...history, streamingEntry])
    const controller = new AbortController()
    abortControllerRef.current = controller
    try {
      const res = await fetch(API_AGENTS_MDP_PLANNER_STEP_URL, {
        method: 'POST',
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          system_description: systemDescription,
          incident_report: incidentReport,
          specification: specification,
          operator_feedback: operatorFeedback,
          code_report: codeReport,
          conversation_history: history.map((e) =>
            e._runId != null
              ? Object.fromEntries(Object.entries(e).filter(([k]) => k !== '_runId'))
              : e
          ),
          images: systemDescriptionImages,
          model_name: selectedModel || undefined,
          time_limit_minutes: timeLimitMinutes
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
          } else if (event.type === 'planner_report') {
            finalEntry = {
              role: 'model',
              type: 'planner_report',
              planner_report: event.planner_report,
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
        if (finalEntry.type === 'planner_report') {
          saveReport(finalEntry.planner_report)
        }
      } else if (accumulated) {
        let report
        try {
          report = JSON.parse(accumulated)
        } catch {
          report = {
            executive_summary: accumulated,
            algorithm: '',
            hyperparameters: '',
            training_summary: '',
            action_sequence: [],
            contingencies: [],
            expected_total_cost: 0,
            risks: []
          }
        }
        setConversationHistory([
          ...history,
          { role: 'model', type: 'planner_report', planner_report: report }
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
    setTrainingData([])
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

    if (proposal.tool_name === 'rl_train') {
      setTrainingData([])
      setTrainingStartTime(Date.now())
      setTrainingMeta({
        algorithm: proposal.tool_args.algorithm || '',
        hyperparameters: proposal.tool_args.hyperparameters || ''
      })
      const controller = new AbortController()
      abortControllerRef.current = controller
      try {
        const res = await fetch(API_AGENTS_MDP_PLANNER_TOOL_URL, {
          method: 'POST',
          signal: controller.signal,
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

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        const progressEvents = []
        let resultEvent = null
        let doneEvent = null

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop()
          for (const line of lines) {
            if (!line.trim()) continue
            try {
              const event = JSON.parse(line)
              if (event.type === 'progress') {
                progressEvents.push(event)
                setTrainingData((prev) => [...prev, event])
              } else if (event.type === 'result') {
                resultEvent = event
              } else if (event.type === 'done' || event.type === 'timeout') {
                doneEvent = event
              } else if (event.type === 'error') {
                setAlert({ type: 'danger', message: event.message || 'Training error' })
              }
            } catch {
              /* skip non-JSON lines */
            }
          }
        }

        setTrainingStartTime(null)
        const runId = ++runIdCounterRef.current
        trainingRunsRef.current[runId] = {
          data: [...progressEvents],
          meta: {
            algorithm: proposal.tool_args.algorithm || '',
            hyperparameters: proposal.tool_args.hyperparameters || ''
          }
        }
        const toolResult = {
          progress_episodes: progressEvents.length,
          result: resultEvent,
          done: doneEvent
        }
        const resultEntry = {
          role: 'tool',
          type: 'tool_result',
          tool_name: proposal.tool_name,
          result: toolResult,
          _runId: runId
        }
        const updated = [...conversationHistory, approvalEntry, resultEntry]
        setConversationHistory(updated)
        setExecutingTool(null)
        await callStep(updated)
      } catch (err) {
        if (err.name === 'AbortError') return
        setAlert({ type: 'danger', message: `Tool execution error: ${err.message}` })
        setTrainingStartTime(null)
        setExecutingTool(null)
      }
    } else {
      const controller = new AbortController()
      abortControllerRef.current = controller
      try {
        const res = await fetch(API_AGENTS_MDP_PLANNER_TOOL_URL, {
          method: 'POST',
          signal: controller.signal,
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
        if (err.name === 'AbortError') return
        setAlert({ type: 'danger', message: `Tool execution error: ${err.message}` })
        setExecutingTool(null)
      }
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
      const exampleRes = await fetch(`${API_EXAMPLES_URL}/${incidentId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (exampleRes.status === 401) {
        logout()
        return
      }
      const exampleData = await exampleRes.json()
      setSystemDescription(exampleData.system_description || '')
      setIncidentReport(exampleData.incident_report || '')
      setSpecification(exampleData.specification || '')
      setOperatorFeedback('')
      setSystemDescriptionImages(exampleData.system_description_images || [])

      const reportsRes = await fetch(
        `${API_AGENTS_REPORTS_URL}?agent_type=code&incident_id=${incidentId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      if (reportsRes.ok) {
        const reports = await reportsRes.json()
        if (reports.length > 0) {
          const latest = reports[0]
          const report = latest.report || {}
          setCodeReport(JSON.stringify(report, null, 2))
        }
      }

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
    setCodeReport('')
    setTimeLimitMinutes(5)
    setSystemDescriptionImages([])
    setConversationHistory([])
    setPendingProposal(null)
    setExpandedEntries({})
    setTrainingData([])
    setTrainingMeta({ algorithm: '', hyperparameters: '' })
    setTrainingStartTime(null)
    trainingRunsRef.current = {}
    runIdCounterRef.current = 0
    setSelectedIncidentId(null)
  }

  const fetchPrompt = async () => {
    setLoadingPrompt(true)
    try {
      const res = await fetch(API_AGENTS_MDP_PLANNER_PROMPT_URL, {
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
          code_report: codeReport,
          time_limit_minutes: timeLimitMinutes
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
      const res = await fetch(`${API_AGENTS_REPORTS_URL}?agent_type=mdp_planner`, {
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
        body: JSON.stringify({ agent_type: 'mdp_planner', report, incident_id: selectedIncidentId })
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
    <MdpPlannerReport
      key={index}
      entry={entry}
      index={index}
      isExpanded={isExpanded}
      toggleEntry={toggleEntry}
    />
  )

  const renderToolResult = (entry) => {
    if (entry.tool_name === 'rl_train') {
      const run = entry._runId ? trainingRunsRef.current[entry._runId] : null
      return (
        <RlTrainResult
          trainingData={run ? run.data : trainingData}
          trainingMeta={run ? run.meta : trainingMeta}
          result={entry.result}
        />
      )
    }
    return null
  }

  const renderExecutingTool = (toolName) => {
    if (toolName === 'rl_train') {
      return (
        <RewardChart
          data={trainingData}
          algorithm={trainingMeta.algorithm}
          hyperparameters={trainingMeta.hyperparameters}
          trainingStartTime={trainingStartTime}
        />
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
        <MdpPlannerConfigTab
          systemDescription={systemDescription}
          setSystemDescription={setSystemDescription}
          incidentReport={incidentReport}
          setIncidentReport={setIncidentReport}
          specification={specification}
          setSpecification={setSpecification}
          operatorFeedback={operatorFeedback}
          setOperatorFeedback={setOperatorFeedback}
          codeReport={codeReport}
          setCodeReport={setCodeReport}
          timeLimitMinutes={timeLimitMinutes}
          setTimeLimitMinutes={setTimeLimitMinutes}
          systemDescriptionImages={systemDescriptionImages}
          setSystemDescriptionImages={setSystemDescriptionImages}
          handlePaste={handlePaste}
          isAgentBusy={isAgentBusy}
          handleRun={handleRun}
          loadExample={loadExample}
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
          logEndRef={logEndRef}
          streamingTraceRef={streamingTraceRef}
          renderFinalReport={renderFinalReport}
          renderExecutingTool={renderExecutingTool}
          renderToolResult={renderToolResult}
          onStop={handleStop}
        />
      )}

      {activeTab === 'history' && (
        <AgentHistoryTab
          reportHistory={reportHistory}
          deleteReport={deleteReport}
          renderReport={(report) => (
            <MdpPlannerReport
              entry={{ type: 'planner_report', planner_report: report }}
              index="history"
              isExpanded={true}
              toggleEntry={() => {}}
            />
          )}
        />
      )}
    </div>
  )
}

export default MdpPlannerAgent
