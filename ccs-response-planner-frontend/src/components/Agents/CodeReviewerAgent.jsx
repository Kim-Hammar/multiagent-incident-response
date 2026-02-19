import { useState, useEffect, useRef } from 'react'
import useTabWithHash from '../../hooks/useTabWithHash.js'
import { useAuth } from '../../contexts/AuthContext.jsx'
import {
  API_EXAMPLES_URL,
  API_AGENTS_CODE_REVIEW_STEP_URL,
  API_AGENTS_CODE_REVIEW_TOOL_URL,
  API_AGENTS_CODE_REVIEW_PROMPT_URL,
  API_LLM_URL,
  API_AGENTS_REPORTS_URL,
  API_DT_PYTHON_STOP_URL
} from '../Common/constants'
import CodeReviewerConfigTab from './CodeReviewerConfigTab.jsx'
import CodeReviewerReport from './CodeReviewerReport.jsx'
import AgentConfigTable from './shared/AgentConfigTable.jsx'
import AgentPlanningTab from './shared/AgentPlanningTab.jsx'
import AgentHistoryTab from './shared/AgentHistoryTab.jsx'
import JobsTab from './shared/JobsTab.jsx'
import { useAgentSession } from './shared/useAgentSession.js'
import { cleanConversationHistory } from './shared/conversationUtils.js'
import { STREAMING_TOOLS, executeStreamingTool } from './shared/streamingToolExec.js'
import { pollJobEvents } from './shared/pollJobEvents.js'

/**
 * CodeReviewerAgent component — drives the code review agent loop with
 * human-in-the-loop tool approval. Renders 3 inner tabs.
 */
function CodeReviewerAgent() {
  const { token, logout } = useAuth()
  const [activeTab, setActiveTab] = useTabWithHash('config')
  const [systemDescription, setSystemDescription] = useState('')
  const [incidentReport, setIncidentReport] = useState('')
  const [specification, setSpecification] = useState('')
  const [operatorFeedback, setOperatorFeedback] = useState('')
  const [codeReport, setCodeReport] = useState('')
  const [systemDescriptionImages, setSystemDescriptionImages] = useState([])
  const [incidentReportImages, setIncidentReportImages] = useState([])
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
  const logEndRef = useRef(null)
  const streamingTraceRef = useRef(null)
  const isNearBottomRef = useRef(true)
  const abortControllerRef = useRef(null)
  const [lastHeartbeatTime, setLastHeartbeatTime] = useState(Date.now())
  const [livenessStatus, setLivenessStatus] = useState('alive')
  const [heartbeatStatus, setHeartbeatStatus] = useState('')

  const {
    conversationHistory,
    setConversationHistory,
    conversationHistoryRef,
    sessionIdRef,
    isSourceTabRef,
    jobs,
    fetchJobs,
    cancelJob,
    removeJob,
    removeAllDoneJobs,
    createSession,
    clearSession,
    cancelRunningJob,
    markSessionCancelled,
    setPendingProposalRef,
    setContextUsageRef,
    setUiStateRef,
    pollingRef
  } = useAgentSession({
    agentType: 'code_review',
    token,
    logout,
    activeTab,
    onRestore: (session) => {
      const inputs = session.incident_inputs || {}
      setSystemDescription(inputs.systemDescription || '')
      setIncidentReport(inputs.incidentReport || '')
      setSpecification(inputs.specification || '')
      setOperatorFeedback(inputs.operatorFeedback || '')
      setCodeReport(inputs.codeReport || '')
      setSystemDescriptionImages(inputs.systemDescriptionImages || [])
      setIncidentReportImages(inputs.incidentReportImages || [])
      setSelectedIncidentId(inputs.selectedIncidentId || null)
      const config = session.agent_config || {}
      setSelectedModel(config.selectedModel || '')
      setCompactionModel(config.compactionModel || '')
      setCompactionThreshold(config.compactionThreshold || 80)
      setAutopilot(config.autopilot ?? true)
      setContextUsage(session.context_usage || null)
      setPendingProposal(session.pending_proposal || null)
      if (!window.location.hash) setActiveTab('planning')
    },
    onResumeJob: (jobId, session, toolName, originalStartTime) => {
      setContextUsage(session.context_usage || null)
      setPendingProposal(null)
      if (!window.location.hash) setActiveTab('planning')
      setRunning(true)
      if (toolName && STREAMING_TOOLS.has(toolName)) {
        setExecutingTool(toolName)
        resumeToolJob(jobId, toolName, originalStartTime)
      } else {
        callStep(conversationHistoryRef.current, jobId)
      }
    }
  })

  useEffect(() => {
    setPendingProposalRef(pendingProposal)
  }, [pendingProposal])
  useEffect(() => {
    setContextUsageRef(contextUsage)
  }, [contextUsage])
  useEffect(() => {
    setUiStateRef({ running, executingTool, dtStatus })
  }, [running, executingTool, dtStatus])

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
    if (autopilot && pendingProposal && isSourceTabRef.current) {
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
    cancelRunningJob()
    markSessionCancelled()
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

  const callStep = async (history, resumeJobId) => {
    setRunning(true)
    isSourceTabRef.current = true
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
    const controller = new AbortController()
    abortControllerRef.current = controller
    const streamingEntry = { role: 'model', type: 'streaming', text: '' }
    const compactionEntries = []
    setConversationHistory([...history, streamingEntry])
    try {
      let job_id = resumeJobId
      if (!job_id) {
        const res = await fetch(API_AGENTS_CODE_REVIEW_STEP_URL, {
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
            conversation_history: history,
            images: [...systemDescriptionImages, ...incidentReportImages],
            model_name: selectedModel || undefined,
            compaction_model: compactionModel || undefined,
            compaction_threshold: compactionThreshold / 100,
            last_prompt_tokens: contextUsage?.prompt_tokens || 0,
            session_id: sessionIdRef.current
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
        const resp = await res.json()
        job_id = resp.job_id
      }
      let accumulated = ''
      let finalEntry = null

      setLivenessStatus('alive')
      setLastHeartbeatTime(Date.now())
      await pollJobEvents({
        jobId: job_id,
        token,
        signal: controller.signal,
        onHeartbeat: (status) => {
          setLastHeartbeatTime(Date.now())
          setHeartbeatStatus(status)
        },
        onStale: () => setLivenessStatus('stale'),
        onEvent: (event) => {
          setLastHeartbeatTime(Date.now())
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
          } else if (event.type === 'review_report') {
            finalEntry = {
              role: 'model',
              type: 'review_report',
              review_report: event.review_report,
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
            throw new Error(event.message || 'Agent stream error')
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
        if (finalEntry.type === 'tool_proposal') {
          setPendingProposal(finalEntry)
        }
        if (finalEntry.type === 'review_report') {
          saveReport(finalEntry.review_report, updated)
        }
      } else if (accumulated) {
        let report
        try {
          report = JSON.parse(accumulated)
        } catch {
          report = {
            executive_summary: accumulated,
            findings: [],
            missing_actions: [],
            command_issues: [],
            strengths: [],
            overall_verdict: ''
          }
        }
        const fallbackHistory = [
          ...history,
          ...compactionEntries,
          { role: 'model', type: 'review_report', review_report: report }
        ]
        setConversationHistory(fallbackHistory)
        saveReport(report, fallbackHistory)
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

  const handleRun = async () => {
    setPendingProposal(null)
    setConversationHistory([])
    setExpandedEntries({})
    setContextUsage(null)
    setActiveTab('planning')
    await createSession(
      {
        systemDescription,
        incidentReport,
        specification,
        operatorFeedback,
        codeReport,
        systemDescriptionImages,
        incidentReportImages,
        selectedIncidentId
      },
      {
        selectedModel,
        compactionModel,
        compactionThreshold,
        autopilot
      }
    )
    callStep([])
  }

  const handleApprove = async () => {
    if (!pendingProposal) return
    const proposal = pendingProposal
    const approvalEntry = {
      role: 'user',
      type: 'tool_approval',
      tool_name: proposal.tool_name,
      tool_args: proposal.tool_args,
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
          url: API_AGENTS_CODE_REVIEW_TOOL_URL,
          toolName: proposal.tool_name,
          toolArgs: proposal.tool_args,
          incidentId: selectedIncidentId,
          token,
          signal: controller.signal,
          extraBody: { session_id: sessionIdRef.current },
          onChunk: (text) => {
            streamEntry.output += text
            setConversationHistory([...base])
          },
          onHeartbeat: (status) => {
            setLastHeartbeatTime(Date.now())
            setHeartbeatStatus(status)
            setLivenessStatus('alive')
          },
          onStale: () => setLivenessStatus('stale')
        })
        const resultEntry = {
          role: 'tool',
          type: 'tool_result',
          tool_name: proposal.tool_name,
          result
        }
        let updated
        setConversationHistory((prev) => {
          const stripped = prev.filter((e) => e.type !== 'streaming' && e.type !== 'tool_streaming')
          updated = [...stripped, resultEntry]
          return updated
        })
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
        setRunning(false)
        setLivenessStatus('error')
        setConversationHistory((prev) =>
          prev
            .map((e) => {
              if (e.type === 'streaming')
                return e.text ? { ...e, type: 'reasoning', role: 'model' } : null
              if (e.type === 'tool_streaming') return { ...e, stopped: true }
              return e
            })
            .filter(Boolean)
            .concat([{ role: 'system', type: 'error', message: err.message }])
        )
      }
      return
    }

    try {
      const res = await fetch(API_AGENTS_CODE_REVIEW_TOOL_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          tool_name: proposal.tool_name,
          tool_args: proposal.tool_args,
          incident_id: selectedIncidentId,
          session_id: sessionIdRef.current
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
      let updated
      setConversationHistory((prev) => {
        const stripped = prev.filter((e) => e.type !== 'streaming' && e.type !== 'tool_streaming')
        updated = [...stripped, approvalEntry, resultEntry]
        return updated
      })
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
      tool_args: pendingProposal.tool_args,
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
    setCodeReport('')
    setSystemDescriptionImages([])
    setIncidentReportImages([])
    setConversationHistory([])
    setPendingProposal(null)
    setExpandedEntries({})
    setSelectedIncidentId(null)
    clearSession()
  }

  const resumeToolJob = async (jobId, toolName, startTime) => {
    const streamEntry = {
      type: 'tool_streaming',
      tool_name: toolName,
      output: '',
      _startTime: startTime || Date.now()
    }
    setConversationHistory((prev) => [...prev, streamEntry])
    setExecutingTool(toolName)
    const controller = new AbortController()
    abortControllerRef.current = controller
    try {
      const { result } = await executeStreamingTool({
        url: API_AGENTS_CODE_REVIEW_TOOL_URL,
        toolName,
        toolArgs: {},
        incidentId: selectedIncidentId,
        token,
        signal: controller.signal,
        resumeJobId: jobId,
        extraBody: { session_id: sessionIdRef.current },
        onChunk: (text) => {
          streamEntry.output += text
          setConversationHistory((prev) => [...prev])
        },
        onHeartbeat: (status) => {
          setLastHeartbeatTime(Date.now())
          setHeartbeatStatus(status)
          setLivenessStatus('alive')
        },
        onStale: () => setLivenessStatus('stale')
      })
      const resultEntry = {
        role: 'tool',
        type: 'tool_result',
        tool_name: toolName,
        result
      }
      let updated
      setConversationHistory((prev) => {
        const stripped = prev.filter((e) => e.type !== 'streaming' && e.type !== 'tool_streaming')
        updated = [...stripped, resultEntry]
        return updated
      })
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
      setRunning(false)
      setLivenessStatus('error')
      setConversationHistory((prev) =>
        prev
          .map((e) => {
            if (e.type === 'streaming')
              return e.text ? { ...e, type: 'reasoning', role: 'model' } : null
            if (e.type === 'tool_streaming') return { ...e, stopped: true }
            return e
          })
          .filter(Boolean)
          .concat([{ role: 'system', type: 'error', message: err.message }])
      )
    }
  }

  const getPromptText = async () => {
    const res = await fetch(API_AGENTS_CODE_REVIEW_PROMPT_URL, {
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
        code_report: codeReport
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
      const res = await fetch(`${API_AGENTS_REPORTS_URL}?agent_type=code_review`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        setReportHistory(await res.json())
      }
    } catch {
      /* ignore */
    }
  }

  const saveReport = async (report, historyToSave) => {
    try {
      await fetch(API_AGENTS_REPORTS_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          agent_type: 'code_review',
          report,
          incident_id: selectedIncidentId,
          conversation_history: cleanConversationHistory(historyToSave),
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
      await fetch(`${API_AGENTS_REPORTS_URL}?agent_type=code_reviewer`, {
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
    <CodeReviewerReport
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
            Review process
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
        <li className="nav-item">
          <button
            type="button"
            className={`nav-link${activeTab === 'jobs' ? ' active' : ''}`}
            onClick={() => setActiveTab('jobs')}
          >
            Jobs
          </button>
        </li>
      </ul>

      {activeTab === 'config' && (
        <CodeReviewerConfigTab
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
            specification: specification,
            operator_feedback: operatorFeedback,
            code_report: codeReport
          })}
          rows={[
            {
              label: 'Code Reviewer',
              model: selectedModel,
              setModel: setSelectedModel,
              promptUrl: API_AGENTS_CODE_REVIEW_PROMPT_URL,
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
          livenessStatus={livenessStatus}
          lastHeartbeatTime={lastHeartbeatTime}
          heartbeatStatus={heartbeatStatus}
        />
      )}

      {activeTab === 'history' && (
        <AgentHistoryTab
          reportHistory={reportHistory}
          deleteReport={deleteReport}
          deleteAllReports={deleteAllReports}
          renderReport={(report) => (
            <CodeReviewerReport
              entry={{ type: 'review_report', review_report: report }}
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

      {activeTab === 'jobs' && (
        <JobsTab
          jobs={jobs}
          fetchJobs={fetchJobs}
          cancelJob={cancelJob}
          removeJob={removeJob}
          removeAllDoneJobs={removeAllDoneJobs}
        />
      )}
    </div>
  )
}

export default CodeReviewerAgent
