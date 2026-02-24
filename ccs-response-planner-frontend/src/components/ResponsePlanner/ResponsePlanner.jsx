import { useState, useEffect, useRef } from 'react'
import useTabWithHash from '../../hooks/useTabWithHash.js'
import { useAuth } from '../../contexts/AuthContext.jsx'
import {
  API_EXAMPLES_URL,
  API_AGENTS_ORCHESTRATOR_STEP_URL,
  API_AGENTS_ORCHESTRATOR_TOOL_URL,
  API_AGENTS_ORCHESTRATOR_PROMPT_URL,
  API_LLM_URL,
  API_AGENTS_REPORTS_URL,
  API_DT_PYTHON_STOP_URL,
  API_AGENTS_SESSIONS_ACTIVE_URL,
  API_AGENTS_SESSIONS_URL,
  apiJobCancelUrl,
  apiJobStatusUrl,
  API_AGENTS_JOBS_URL
} from '../Common/constants'
import AgentPlanningTab from '../Agents/shared/AgentPlanningTab.jsx'
import AgentHistoryTab from '../Agents/shared/AgentHistoryTab.jsx'
import { cleanConversationHistory } from '../Agents/shared/conversationUtils.js'
import { handleDtEvent as sharedHandleDtEvent } from '../Agents/shared/dtEventHandler.js'
import { STREAMING_TOOLS, executeStreamingTool } from '../Agents/shared/streamingToolExec.js'
import { pollJobEvents } from '../Agents/shared/pollJobEvents.js'
import {
  AssessmentBody,
  CodeReportBody,
  PlannerReportInline,
  PlanManagerReportBody
} from '../Agents/shared/ReportBodies.jsx'
import JobsTab from '../Agents/shared/JobsTab.jsx'
import ConfigTab from './ConfigTab.jsx'
import SubAgentsTab from './SubAgentsTab.jsx'
import '../Agents/Agents.css'
import './ResponsePlanner.css'

/**
 * Helper to push a nested_event into the correct level of the subEvents tree.
 */
function handleNestedSubEvent(subEvents, innerEvent, ts) {
  const now = ts || Date.now()
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
      subEvents.push({ type: 'reasoning', text: innerEvent.text, _startTime: now })
    }
  } else if (innerEvent.type === 'text_delta') {
    const last = subEvents[subEvents.length - 1]
    if (last && last.type === 'text') {
      last.text += innerEvent.text
    } else {
      subEvents.push({ type: 'text', text: innerEvent.text, _startTime: now })
    }
  } else if (innerEvent.type === 'nested_event') {
    const lastToolCall = [...subEvents]
      .reverse()
      .find((e) => e.type === 'tool_call' && !e._completed)
    if (lastToolCall) {
      if (innerEvent.event.type === 'prompt') {
        lastToolCall._prompt = innerEvent.event.text
        lastToolCall._promptImages = innerEvent.event.images || []
      } else if (innerEvent.event.type === 'context_usage') {
        lastToolCall._contextUsage = innerEvent.event
      } else {
        if (!lastToolCall.subEvents) lastToolCall.subEvents = []
        handleNestedSubEvent(lastToolCall.subEvents, innerEvent.event, now)
      }
    }
  } else if (innerEvent.type === 'tool_result') {
    const lastCall = [...subEvents].reverse().find((e) => e.type === 'tool_call')
    if (lastCall) lastCall._completed = true
    const streamSubs = innerEvent.subEvents || []
    subEvents.push({
      type: 'tool_result',
      tool_name: innerEvent.tool_name,
      result: innerEvent.result,
      subEvents: streamSubs.length > 0 ? streamSubs : lastCall?.subEvents || []
    })
  } else {
    if (!innerEvent._startTime) innerEvent._startTime = now
    subEvents.push(innerEvent)
  }
}

/**
 * Extract sub-agent data from conversation history and merge into the report.
 */
function enrichOrchestratorReport(report, history) {
  const rmResult =
    [...history]
      .reverse()
      .find((e) => e.type === 'tool_result' && e.tool_name === 'run_report_manager')?.result || {}
  const pmResult =
    [...history]
      .reverse()
      .find((e) => e.type === 'tool_result' && e.tool_name === 'run_plan_manager')?.result || {}
  const assessment = rmResult.assessment ? { ...rmResult.assessment } : {}
  if (rmResult.attack_path_image) {
    assessment.attack_path_image = rmResult.attack_path_image
  }
  return {
    ...report,
    assessment,
    code_report: pmResult.code_report || {},
    planner_report: pmResult.planner_report || {},
    validation_report: pmResult.validation_report || {},
    response_plan: pmResult.response_plan || ''
  }
}

/**
 * Render an orchestrator agent report entry.
 */
function OrchestratorAgentReportView({ entry, index, isExpanded, toggleEntry }) {
  const report = entry.orchestrator_agent_report || {}

  return (
    <div className="card ia-entry ia-result-entry">
      <div className="card-body">
        <div className="ia-result-header" onClick={() => toggleEntry(index)}>
          <i className="fa fa-flag-checkered" aria-hidden="true" />
          <span className="ia-result-label">Final Response Plan</span>
          <span className="ia-toggle-hint">{isExpanded ? 'collapse' : 'expand'}</span>
        </div>
        {isExpanded && (
          <div style={{ marginTop: '10px' }}>
            {report.executive_summary && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Summary</div>
                <p className="ia-assessment-body mb-0">{report.executive_summary}</p>
              </div>
            )}
            {report.assessment && Object.keys(report.assessment).length > 0 && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Incident Report</div>
                <AssessmentBody report={report.assessment} />
              </div>
            )}
            {report.code_report && Object.keys(report.code_report).length > 0 && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Code Report</div>
                <CodeReportBody report={report.code_report} />
              </div>
            )}
            {report.planner_report && Object.keys(report.planner_report).length > 0 && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Response Plan</div>
                <PlannerReportInline report={report.planner_report} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Response Planner page — orchestrator agent integration with 4 tabs:
 * Incident description, Sub-agents, Planning process, History.
 */
function ResponsePlanner() {
  const { token, logout } = useAuth()
  const [activeTab, setActiveTab] = useTabWithHash('config')
  const [systemDescription, setSystemDescription] = useState('')
  const [securityAlerts, setSecurityAlerts] = useState('')
  const [operatorFeedback, setOperatorFeedback] = useState('')
  const [specification, setSpecification] = useState('')
  const [specificationCommands, setSpecificationCommands] = useState([])
  const [systemDescriptionImages, setSystemDescriptionImages] = useState([])
  const [securityAlertsImages, setSecurityAlertsImages] = useState([])
  const [conversationHistory, rawSetConversationHistory] = useState([])
  const conversationHistoryRef = useRef([])
  const setConversationHistory = (value) => {
    const next = typeof value === 'function' ? value(conversationHistoryRef.current) : value
    conversationHistoryRef.current = next
    rawSetConversationHistory(next)
  }
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
  const [orchestratorModel, setOrchestratorModel] = useState('')
  const [reportManagerModel, setReportManagerModel] = useState('')
  const [reportAgentModel, setReportAgentModel] = useState('')
  const [reportReviewerModel, setReportReviewerModel] = useState('')
  const [planManagerModel, setPlanManagerModel] = useState('')
  const [codeManagerModel, setCodeManagerModel] = useState('')
  const [codeAgentModel, setCodeAgentModel] = useState('')
  const [codeReviewerModel, setCodeReviewerModel] = useState('')
  const [plannerAgentModel, setPlannerAgentModel] = useState('')
  const [validationAgentModel, setValidationAgentModel] = useState('')
  const [compactionModel, setCompactionModel] = useState('')
  const [orchestratorCompaction, setOrchestratorCompaction] = useState(80)
  const [reportManagerCompaction, setReportManagerCompaction] = useState(80)
  const [reportAgentCompaction, setReportAgentCompaction] = useState(80)
  const [reportReviewerCompaction, setReportReviewerCompaction] = useState(80)
  const [planManagerCompaction, setPlanManagerCompaction] = useState(80)
  const [codeManagerCompaction, setCodeManagerCompaction] = useState(80)
  const [codeAgentCompaction, setCodeAgentCompaction] = useState(80)
  const [codeReviewerCompaction, setCodeReviewerCompaction] = useState(80)
  const [plannerAgentCompaction, setPlannerAgentCompaction] = useState(80)
  const [validationAgentCompaction, setValidationAgentCompaction] = useState(80)
  const [reportManagerIterations, setReportManagerIterations] = useState(1)
  const [planManagerIterations, setPlanManagerIterations] = useState(1)
  const [codeManagerIterations, setCodeManagerIterations] = useState(1)
  const [plannerTimeLimitMinutes, setPlannerTimeLimitMinutes] = useState(10)
  const [reportHistory, setReportHistory] = useState([])
  const [selectedIncidentId, setSelectedIncidentId] = useState(null)
  const sessionIdRef = useRef(null)
  const setSessionId = (value) => {
    sessionIdRef.current = value
  }
  const [restoredSession, setRestoredSession] = useState(false)
  const restoredSessionRef = useRef(false)
  const logEndRef = useRef(null)
  const streamingTraceRef = useRef(null)
  const isNearBottomRef = useRef(true)
  const abortControllerRef = useRef(null)
  const [lastHeartbeatTime, setLastHeartbeatTime] = useState(Date.now())
  const [livenessStatus, setLivenessStatus] = useState('alive')
  const [heartbeatStatus, setHeartbeatStatus] = useState('')
  const isSourceTabRef = useRef(false)
  const pollingRef = useRef(null)
  const lastSaveRef = useRef(0)
  const saveAbortRef = useRef(null)
  const callStepRef = useRef(null)
  const [jobs, setJobs] = useState(null)

  const fetchJobs = async () => {
    try {
      const res = await fetch(API_AGENTS_JOBS_URL, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setJobs(data)
      }
    } catch {
      /* ignore */
    }
  }

  const cancelJob = async (jobId) => {
    try {
      await fetch(apiJobCancelUrl(jobId), {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      })
      await fetchJobs()
    } catch {
      /* ignore */
    }
  }

  const removeJob = async (jobId) => {
    try {
      await fetch(`${API_AGENTS_JOBS_URL}/${jobId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })
      await fetchJobs()
    } catch {
      /* ignore */
    }
  }

  const removeAllDoneJobs = async () => {
    const done = (jobs || []).filter((j) => j.done)
    for (const j of done) {
      try {
        await fetch(`${API_AGENTS_JOBS_URL}/${j.job_id}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` }
        })
      } catch {
        /* ignore */
      }
    }
    await fetchJobs()
  }

  useEffect(() => {
    if (activeTab === 'jobs') fetchJobs()
  }, [activeTab])

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

  useEffect(() => {
    if (!isSourceTabRef.current) return
    const sid = sessionIdRef.current
    if (!sid) return

    const save = () => {
      if (!isSourceTabRef.current || !sessionIdRef.current) return
      lastSaveRef.current = Date.now()
      // Cancel any in-flight save so stale PUTs don't pile up
      // and exhaust the browser's per-host connection limit.
      if (saveAbortRef.current) saveAbortRef.current.abort()
      const ac = new AbortController()
      saveAbortRef.current = ac
      fetch(`${API_AGENTS_SESSIONS_URL}/${sid}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          conversation_history: conversationHistoryRef.current,
          pending_proposal: pendingProposal,
          context_usage: contextUsage,
          ui_state: { running, executingTool, dtStatus }
        }),
        signal: ac.signal
      }).catch((err) => {
        if (err.name !== 'AbortError') {
          console.warn('Session auto-save failed:', err.message)
        }
      })
    }

    const elapsed = Date.now() - lastSaveRef.current
    if (elapsed >= 1000) {
      save()
      return
    }
    const timer = setTimeout(save, 1000 - elapsed)
    return () => clearTimeout(timer)
  }, [conversationHistory])

  useEffect(() => {
    if (restoredSession) return
    let aborted = false
    fetch(API_AGENTS_SESSIONS_ACTIVE_URL, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then((res) => {
        if (aborted || restoredSessionRef.current) return null
        if (res.status === 401) {
          logout()
          return null
        }
        return res.ok ? res.json() : null
      })
      .then(async (data) => {
        if (aborted || restoredSessionRef.current) return
        if (!data || !data.session) {
          restoredSessionRef.current = true
          setRestoredSession(true)
          return
        }
        const session = data.session
        setSessionId(session.id)
        const inputs = session.incident_inputs || {}
        setSystemDescription(inputs.systemDescription || '')
        setSecurityAlerts(inputs.securityAlerts || '')
        setOperatorFeedback(inputs.operatorFeedback || '')
        setSpecification(inputs.specification || '')
        setSpecificationCommands(inputs.specificationCommands || [])
        setSystemDescriptionImages(inputs.systemDescriptionImages || [])
        setSecurityAlertsImages(inputs.securityAlertsImages || [])
        setSelectedIncidentId(inputs.selectedIncidentId || null)
        const config = session.agent_config || {}
        setOrchestratorModel(config.orchestratorModel || '')
        setReportManagerModel(config.reportManagerModel || '')
        setReportAgentModel(config.reportAgentModel || '')
        setReportReviewerModel(config.reportReviewerModel || '')
        setPlanManagerModel(config.planManagerModel || '')
        setCodeManagerModel(config.codeManagerModel || '')
        setCodeAgentModel(config.codeAgentModel || '')
        setCodeReviewerModel(config.codeReviewerModel || '')
        setPlannerAgentModel(config.plannerAgentModel || '')
        setValidationAgentModel(config.validationAgentModel || '')
        setCompactionModel(config.compactionModel || '')
        setOrchestratorCompaction(config.orchestratorCompaction || 80)
        setReportManagerCompaction(config.reportManagerCompaction || 80)
        setReportAgentCompaction(config.reportAgentCompaction || 80)
        setReportReviewerCompaction(config.reportReviewerCompaction || 80)
        setPlanManagerCompaction(config.planManagerCompaction || 80)
        setCodeManagerCompaction(config.codeManagerCompaction || 80)
        setCodeAgentCompaction(config.codeAgentCompaction || 80)
        setCodeReviewerCompaction(config.codeReviewerCompaction || 80)
        setPlannerAgentCompaction(config.plannerAgentCompaction || 80)
        setValidationAgentCompaction(config.validationAgentCompaction || 80)
        setReportManagerIterations(config.reportManagerIterations || 1)
        setPlanManagerIterations(config.planManagerIterations || 1)
        setCodeManagerIterations(config.codeManagerIterations || 1)
        setPlannerTimeLimitMinutes(config.plannerTimeLimitMinutes || 10)
        setAutopilot(config.autopilot ?? true)
        const uiState = session.ui_state || {}
        let jobRunning = false
        let jobEventCount = -1
        try {
          const jobRes = await fetch(apiJobStatusUrl(String(session.id)), {
            headers: { Authorization: `Bearer ${token}` }
          })
          if (jobRes.ok) {
            const jobData = await jobRes.json()
            jobRunning = jobData.running && !jobData.done
            jobEventCount = jobData.event_count ?? 0
          }
        } catch {
          /* treat as no running job */
        }
        let history = session.conversation_history || []
        let proposal = session.pending_proposal || null
        if (jobRunning) {
          // Save the original _startTime before stripping active entries
          const activeStream = history.find((e) => e.type === 'tool_streaming' && !e.stopped)
          const originalStartTime = activeStream?._startTime || null
          // Strip streaming entries — polling will rebuild them from scratch
          history = history.filter(
            (e) => e.type !== 'streaming' && !(e.type === 'tool_streaming' && !e.stopped)
          )
          setContextUsage(session.context_usage || null)
          setConversationHistory(history)
          setPendingProposal(null)
          if (!window.location.hash) setActiveTab('planning')
          restoredSessionRef.current = true
          setRestoredSession(true)
          // Claim this tab as the source and stop multi-tab polling
          isSourceTabRef.current = true
          if (pollingRef.current) {
            clearInterval(pollingRef.current)
            pollingRef.current = null
          }
          setRunning(true)
          // Detect job type and resume
          const toolName = uiState.executingTool
          if (toolName && STREAMING_TOOLS.has(toolName)) {
            setExecutingTool(toolName)
            resumeToolJob(String(session.id), toolName, originalStartTime, jobEventCount)
          } else {
            callStep(history, String(session.id), jobEventCount)
          }
        } else {
          // Job is not running — if no events were recorded, the job
          // never existed in this server lifetime (backend restarted).
          // Cancel the stale session immediately to avoid a brief
          // flash of old activity before the stale-detection effect
          // clears it.
          if (jobEventCount === 0) {
            fetch(`${API_AGENTS_SESSIONS_URL}/${String(session.id)}`, {
              method: 'PUT',
              headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`
              },
              body: JSON.stringify({
                status: 'cancelled',
                conversation_history: [],
                ui_state: { running: false, executingTool: null, dtStatus: null }
              })
            }).catch(() => {})
            setSessionId(null)
            setConversationHistory([])
            setPendingProposal(null)
            setContextUsage(null)
            setRunning(false)
            setExecutingTool(null)
            setDtStatus(null)
            setSystemDescription('')
            setSecurityAlerts('')
            setOperatorFeedback('')
            setSpecification('')
            setSystemDescriptionImages([])
            setSecurityAlertsImages([])
            setSelectedIncidentId(null)
            restoredSessionRef.current = true
            setRestoredSession(true)
            return
          }
          if (history.length > 0) {
            const last = history[history.length - 1]
            if (last.type === 'tool_approval' && last.approved) {
              history = history.slice(0, -1)
              const lastProposal = [...history].reverse().find((e) => e.type === 'tool_proposal')
              if (lastProposal) {
                proposal = lastProposal
              }
            }
          }
          // Clean stale in-flight entries — no live job exists after reload
          history = history
            .map((e) => {
              if (e.type === 'streaming') {
                return e.text ? { ...e, type: 'reasoning', role: 'model' } : null
              }
              if (e.type === 'tool_streaming' && !e.stopped) {
                return { ...e, stopped: true }
              }
              return e
            })
            .filter(Boolean)
          setContextUsage(session.context_usage || null)
          // Never restore running/executingTool — jobs are in-memory only
          setRunning(false)
          setExecutingTool(null)
          setDtStatus(null)
          setConversationHistory(history)
          setPendingProposal(proposal)
          if (!window.location.hash) setActiveTab('planning')
          restoredSessionRef.current = true
          setRestoredSession(true)
        }
      })
      .catch(() => {
        if (!aborted) {
          restoredSessionRef.current = true
          setRestoredSession(true)
        }
      })
    return () => {
      aborted = true
    }
  }, [token, restoredSession, logout])

  useEffect(() => {
    if (isSourceTabRef.current) return
    const sid = sessionIdRef.current
    if (!sid) return
    const interval = setInterval(() => {
      Promise.all([
        fetch(API_AGENTS_SESSIONS_ACTIVE_URL, {
          headers: { Authorization: `Bearer ${token}` }
        }).then((res) => (res.ok ? res.json() : null)),
        fetch(apiJobStatusUrl(sid), {
          headers: { Authorization: `Bearer ${token}` }
        }).then((res) => (res.ok ? res.json() : null))
      ])
        .then(([data, jobData]) => {
          if (!data?.session) return
          const s = data.session
          const jobRunning = jobData ? !jobData.done : false
          if (!jobRunning) {
            setConversationHistory([])
            setPendingProposal(null)
            setContextUsage(null)
            setRunning(false)
            setExecutingTool(null)
            setDtStatus(null)
            if (s.status !== 'active') clearInterval(interval)
            return
          }
          const rawHistory = (s.conversation_history || [])
            .map((e) => {
              if (e.type === 'streaming')
                return e.text ? { ...e, type: 'reasoning', role: 'model' } : null
              if (e.type === 'tool_streaming' && !e.stopped) return { ...e, stopped: true }
              return e
            })
            .filter(Boolean)
          setConversationHistory(rawHistory)
          setPendingProposal(s.pending_proposal || null)
          setContextUsage(s.context_usage || null)
          setRunning(true)
          setExecutingTool(s.ui_state?.executingTool || null)
          setDtStatus(s.ui_state?.dtStatus || null)
        })
        .catch(() => {})
    }, 1000)
    pollingRef.current = interval
    return () => clearInterval(interval)
  }, [restoredSession, token])

  useEffect(() => {
    if (!restoredSession || !sessionIdRef.current) return
    if (isSourceTabRef.current) return
    const sid = sessionIdRef.current
    fetch(apiJobStatusUrl(sid), {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!data) return
        if (data.done && !data.running) {
          // Job is not running — could be a stale session after backend
          // restart. If no events were recorded the job never existed in
          // this server lifetime, so cancel the session and reset all state.
          if (data.event_count === 0) {
            fetch(`${API_AGENTS_SESSIONS_URL}/${sid}`, {
              method: 'PUT',
              headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`
              },
              body: JSON.stringify({
                status: 'cancelled',
                conversation_history: [],
                ui_state: { running: false, executingTool: null, dtStatus: null }
              })
            }).catch(() => {})
            setSessionId(null)
            setConversationHistory([])
            setPendingProposal(null)
            setContextUsage(null)
            setRunning(false)
            setExecutingTool(null)
            setDtStatus(null)
            setSystemDescription('')
            setSecurityAlerts('')
            setOperatorFeedback('')
            setSpecification('')
            setSystemDescriptionImages([])
            setSecurityAlertsImages([])
            setSelectedIncidentId(null)
            return
          }
          return fetch(API_AGENTS_SESSIONS_ACTIVE_URL, {
            headers: { Authorization: `Bearer ${token}` }
          })
            .then((res) => (res.ok ? res.json() : null))
            .then((freshData) => {
              if (!freshData?.session) return
              const s = freshData.session
              const history = (s.conversation_history || [])
                .map((e) => {
                  if (e.type === 'streaming')
                    return e.text ? { ...e, type: 'reasoning', role: 'model' } : null
                  if (e.type === 'tool_streaming' && !e.stopped) return { ...e, stopped: true }
                  return e
                })
                .filter(Boolean)
              setConversationHistory(history)
              setPendingProposal(s.pending_proposal || null)
              setContextUsage(s.context_usage || null)
              setRunning(false)
              setExecutingTool(null)
              setDtStatus(null)
              if (s.status === 'active' && history.length > 0) {
                const last = history[history.length - 1]
                if (last.type === 'tool_result') {
                  isSourceTabRef.current = true
                  if (pollingRef.current) {
                    clearInterval(pollingRef.current)
                    pollingRef.current = null
                  }
                  callStep(history)
                }
              }
            })
        }
      })
      .catch(() => {})
  }, [restoredSession])

  const scrollToBottom = () => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
    setHasNewActivity(false)
  }

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    const sid = sessionIdRef.current
    if (sid) {
      fetch(apiJobCancelUrl(sid), {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      }).catch(() => {})
    }
    fetch(API_DT_PYTHON_STOP_URL, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` }
    }).catch(() => {})
    setRunning(false)
    setExecutingTool(null)
    setPendingProposal(null)
    isSourceTabRef.current = false
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
    if (sid) {
      fetch(`${API_AGENTS_SESSIONS_URL}/${sid}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          status: 'cancelled',
          conversation_history: conversationHistoryRef.current,
          ui_state: { running: false, executingTool: null, dtStatus: null }
        })
      }).catch(() => {})
    }
  }

  const stripForBackend = (history) =>
    history
      .filter((entry) => entry.type !== 'tool_streaming')
      .map((entry) => {
        if (entry.type === 'tool_result' && entry.result?.image) {
          return {
            ...entry,
            result: { status: 'success', message: 'Image generated successfully' }
          }
        }
        if (entry.type === 'tool_result') {
          return {
            role: entry.role,
            type: entry.type,
            tool_name: entry.tool_name,
            result: entry.result
          }
        }
        return entry
      })

  const handleDtEvent = (event) => {
    sharedHandleDtEvent(event, setConversationHistory, setDtStatus)
  }

  const callStep = async (history, resumeJobId = null, catchUpUntil = 0) => {
    setRunning(true)
    const controller = new AbortController()
    abortControllerRef.current = controller
    const streamingEntry = { role: 'model', type: 'streaming', text: '', _startTime: Date.now() }
    let errorOccurred = false
    let streamingAdded = false
    let caughtUp = catchUpUntil <= 0
    try {
      let job_id
      if (resumeJobId) {
        job_id = resumeJobId
      } else {
        const res = await fetch(API_AGENTS_ORCHESTRATOR_STEP_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          signal: controller.signal,
          body: JSON.stringify({
            session_id: sessionIdRef.current,
            system_description: systemDescription,
            security_alerts: securityAlerts,
            operator_feedback: operatorFeedback,
            conversation_history: stripForBackend(history),
            images: [...systemDescriptionImages, ...securityAlertsImages],
            model_name: orchestratorModel || undefined,
            compaction_model: compactionModel || undefined,
            compaction_threshold: orchestratorCompaction / 100
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
          setConversationHistory((prev) => {
            const base = prev.filter((e) => e !== streamingEntry)
            return [...base, { role: 'system', type: 'error', message: msg }]
          })
          return
        }
        ;({ job_id } = await res.json())
      }
      let accumulated = ''
      let toolInputAccumulated = ''
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
        onEvent: (event, eventIndex) => {
          setLastHeartbeatTime(Date.now())
          setLivenessStatus('alive')
          if (errorOccurred) return

          // Transition from catch-up to live mode
          if (!caughtUp && eventIndex >= catchUpUntil) {
            caughtUp = true
            // streamingEntry is already in state; flush accumulated data
            if (streamingAdded) {
              setConversationHistory((prev) => [...prev])
            }
          }

          if (event.type === 'dt_progress' || event.type === 'dt_progress_detail' || event.type === 'sandbox_progress') {
            if (!caughtUp) return
            handleDtEvent(event)
            return
          }

          if (!streamingAdded) {
            streamingAdded = true
            // Always add immediately so the spinner is visible during catch-up
            setConversationHistory((prev) => [...prev, streamingEntry])
          }

          if (event.ts && !streamingEntry._tsAdjusted) {
            streamingEntry._startTime = event.ts
            streamingEntry._tsAdjusted = true
          }
          if (event.type === 'text' || event.type === 'thinking') {
            accumulated += event.delta
            streamingEntry.text = accumulated
            if (caughtUp) setConversationHistory((prev) => [...prev])
          } else if (event.type === 'tool_input_started') {
            streamingEntry.generatingTool = event.tool_name
            if (caughtUp) setConversationHistory((prev) => [...prev])
          } else if (event.type === 'tool_input_delta') {
            toolInputAccumulated += event.delta
            streamingEntry.toolInput = toolInputAccumulated
            if (caughtUp) setConversationHistory((prev) => [...prev])
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
          } else if (event.type === 'orchestrator_agent_report') {
            finalEntry = {
              role: 'model',
              type: 'orchestrator_agent_report',
              orchestrator_agent_report: event.orchestrator_agent_report,
              thinking_trace: event.thinking_trace || ''
            }
          } else if (event.type === 'context_usage') {
            setContextUsage(event)
          } else if (event.type === 'context_compaction') {
            const compactionEntry = {
              role: 'system',
              type: 'context_compaction',
              original_tokens: event.original_tokens,
              compacted_tokens: event.compacted_tokens,
              compaction_model: event.compaction_model
            }
            if (caughtUp) {
              setConversationHistory((prev) => {
                const idx = prev.indexOf(streamingEntry)
                if (idx === -1) return [...prev, compactionEntry]
                return [...prev.slice(0, idx), compactionEntry, ...prev.slice(idx)]
              })
            }
          } else if (event.type === 'error') {
            const msg = event.message || 'Agent stream error'
            setAlert({ type: 'danger', message: msg })
            setConversationHistory((prev) => {
              const base = prev.filter((e) => e !== streamingEntry)
              return [
                ...base,
                {
                  role: 'system',
                  type: 'error',
                  message: msg,
                  errorDetail: event.errorDetail || null
                }
              ]
            })
            errorOccurred = true
          }
        }
      })

      // If the job completed entirely within the catch-up window, flush now
      if (!caughtUp && streamingAdded) {
        caughtUp = true
        setConversationHistory((prev) => [...prev])
      }

      if (errorOccurred) return

      setDtStatus(null)
      if (finalEntry) {
        const entries = []
        const reasoningText = finalEntry.thinking_trace || accumulated
        if (reasoningText) {
          entries.push({ role: 'model', type: 'reasoning', text: reasoningText })
        }
        entries.push(finalEntry)
        setConversationHistory((prev) => {
          const base = prev.filter((e) => e !== streamingEntry)
          return [...base, ...entries]
        })
        if (finalEntry.type === 'tool_proposal') {
          setPendingProposal(finalEntry)
        }
        if (finalEntry.type === 'orchestrator_agent_report') {
          finalEntry.orchestrator_agent_report = enrichOrchestratorReport(
            finalEntry.orchestrator_agent_report,
            history
          )
          saveReport(finalEntry.orchestrator_agent_report)
        }
      } else if (accumulated) {
        let report
        try {
          report = JSON.parse(accumulated)
        } catch {
          report = {
            executive_summary: accumulated
          }
        }
        report = enrichOrchestratorReport(report, history)
        setConversationHistory((prev) => {
          const base = prev.filter((e) => e !== streamingEntry)
          return [
            ...base,
            {
              role: 'model',
              type: 'orchestrator_agent_report',
              orchestrator_agent_report: report
            }
          ]
        })
        saveReport(report)
      } else {
        setConversationHistory((prev) => {
          const base = prev.filter((e) => e !== streamingEntry)
          return [
            ...base,
            { role: 'system', type: 'error', message: 'Agent returned an empty response.' }
          ]
        })
      }
    } catch (err) {
      if (err.name === 'AbortError') return
      if (errorOccurred) return
      setAlert({ type: 'danger', message: `Agent error: ${err.message}` })
      errorOccurred = true
      setConversationHistory((prev) => [
        ...prev,
        { role: 'system', type: 'error', message: err.message, errorDetail: err.errorDetail }
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
  callStepRef.current = callStep

  const resumeToolJob = async (jobId, toolName, originalStartTime = null, catchUpUntil = 0) => {
    const controller = new AbortController()
    abortControllerRef.current = controller
    const streamEntry = {
      type: 'tool_streaming',
      tool_name: toolName,
      output: '',
      subEvents: [],
      _startTime: originalStartTime || Date.now()
    }
    let caughtUp = catchUpUntil <= 0
    // Always add streamEntry immediately so the spinner is visible during catch-up
    setConversationHistory((prev) => [...prev, streamEntry])
    try {
      let doneEvent = null
      setLivenessStatus('alive')
      setLastHeartbeatTime(Date.now())
      await pollJobEvents({
        jobId,
        token,
        signal: controller.signal,
        onHeartbeat: (status) => {
          setLastHeartbeatTime(Date.now())
          setHeartbeatStatus(status)
        },
        onStale: () => setLivenessStatus('stale'),
        onEvent: (event, eventIndex) => {
          setLastHeartbeatTime(Date.now())
          setLivenessStatus('alive')

          // Transition from catch-up to live mode
          if (!caughtUp && eventIndex >= catchUpUntil) {
            caughtUp = true
            // streamEntry is already in state; flush accumulated data
            setConversationHistory((prev) => [...prev])
          }

          if (event.type === 'dt_progress' || event.type === 'dt_progress_detail' || event.type === 'sandbox_progress') {
            if (!caughtUp) return
            handleDtEvent(event)
            return
          }
          if (event.type === 'output_chunk') {
            streamEntry.output += event.text
            if (caughtUp) setConversationHistory((prev) => [...prev])
          } else if (event.type === 'sub_event') {
            const inner = event.event
            if (inner.type === 'context_usage') {
              streamEntry.contextUsage = inner
              if (caughtUp) setConversationHistory((prev) => [...prev])
              return
            }
            if (inner.type === 'prompt') {
              streamEntry.prompt = inner.text
              streamEntry.promptImages = inner.images || []
              if (caughtUp) setConversationHistory((prev) => [...prev])
              return
            }
            const evTs = event.ts || Date.now()
            if (inner.type === 'thinking_delta') {
              const last = streamEntry.subEvents[streamEntry.subEvents.length - 1]
              if (last && last.type === 'reasoning') {
                last.text += inner.text
              } else {
                streamEntry.subEvents.push({
                  type: 'reasoning',
                  text: inner.text,
                  _startTime: evTs
                })
              }
            } else if (inner.type === 'text_delta') {
              const last = streamEntry.subEvents[streamEntry.subEvents.length - 1]
              if (last && last.type === 'text') {
                last.text += inner.text
              } else {
                streamEntry.subEvents.push({
                  type: 'text',
                  text: inner.text,
                  _startTime: evTs
                })
              }
            } else if (inner.type === 'nested_event') {
              const lastToolCall = [...streamEntry.subEvents]
                .reverse()
                .find((e) => e.type === 'tool_call' && !e._completed)
              if (lastToolCall) {
                if (inner.event.type === 'prompt') {
                  lastToolCall._prompt = inner.event.text
                  lastToolCall._promptImages = inner.event.images || []
                } else if (inner.event.type === 'context_usage') {
                  lastToolCall._contextUsage = inner.event
                } else {
                  if (!lastToolCall.subEvents) lastToolCall.subEvents = []
                  handleNestedSubEvent(lastToolCall.subEvents, inner.event, evTs)
                }
              }
            } else if (inner.type === 'tool_result') {
              const lastCall = [...streamEntry.subEvents]
                .reverse()
                .find((e) => e.type === 'tool_call')
              if (lastCall) lastCall._completed = true
              streamEntry.subEvents.push({
                type: 'tool_result',
                tool_name: inner.tool_name,
                result: inner.result,
                subEvents: inner.subEvents || []
              })
            } else {
              if (!inner._startTime) inner._startTime = evTs
              streamEntry.subEvents.push(inner)
            }
            if (caughtUp) setConversationHistory((prev) => [...prev])
          } else if (event.type === 'done') {
            doneEvent = event
          } else if (event.type === 'error') {
            const err = new Error(event.message || 'Streaming tool error')
            err.errorDetail = event.errorDetail || null
            throw err
          }
        }
      })
      // If the job completed entirely within the catch-up window, flush now
      if (!caughtUp) {
        caughtUp = true
        setConversationHistory((prev) => [...prev])
      }
      streamEntry.stopped = true
      const result = doneEvent
        ? doneEvent.result || {
            container: doneEvent.container,
            command: doneEvent.command,
            exit_code: doneEvent.exit_code,
            output: doneEvent.output
          }
        : { status: 'unknown', message: 'Job ended without a done event' }
      const resultEntry = {
        role: 'tool',
        type: 'tool_result',
        tool_name: toolName,
        result,
        subEvents: streamEntry.subEvents,
        prompt: streamEntry.prompt,
        contextUsage: streamEntry.contextUsage
      }
      setConversationHistory((prev) => [...prev, resultEntry])
      setExecutingTool(null)
      await callStepRef.current(conversationHistoryRef.current)
    } catch (err) {
      if (err.name === 'AbortError') return
      if (err.status === 401) {
        logout()
        return
      }
      setAlert({ type: 'danger', message: `Tool resume error: ${err.message}` })
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
          .concat([
            { role: 'system', type: 'error', message: err.message, errorDetail: err.errorDetail }
          ])
      )
    }
  }

  const handleRun = async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
    isSourceTabRef.current = true
    setPendingProposal(null)
    setConversationHistory([])
    setExpandedEntries({})
    setContextUsage(null)
    setActiveTab('planning')
    setRunning(true)
    try {
      const res = await fetch(API_AGENTS_SESSIONS_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          incident_inputs: {
            systemDescription,
            securityAlerts,
            operatorFeedback,
            specification,
            specificationCommands,
            systemDescriptionImages,
            securityAlertsImages,
            selectedIncidentId
          },
          agent_config: {
            orchestratorModel,
            reportManagerModel,
            reportAgentModel,
            reportReviewerModel,
            planManagerModel,
            codeManagerModel,
            codeAgentModel,
            codeReviewerModel,
            plannerAgentModel,
            validationAgentModel,
            compactionModel,
            orchestratorCompaction,
            reportManagerCompaction,
            reportAgentCompaction,
            reportReviewerCompaction,
            planManagerCompaction,
            codeManagerCompaction,
            codeAgentCompaction,
            codeReviewerCompaction,
            plannerAgentCompaction,
            validationAgentCompaction,
            reportManagerIterations,
            planManagerIterations,
            codeManagerIterations,
            plannerTimeLimitMinutes,
            autopilot
          }
        })
      })
      if (res.status === 401) {
        logout()
        return
      }
      if (res.ok) {
        const data = await res.json()
        setSessionId(data.session?.id || null)
      }
    } catch {
      /* session creation is optional */
    }
    callStep([])
  }

  const handleApprove = async () => {
    if (!pendingProposal) return
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
    isSourceTabRef.current = true
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
      const historyForBackend = conversationHistoryRef.current
      setConversationHistory((prev) => [...prev, approvalEntry, streamEntry])
      try {
        const extraBody = {
          session_id: sessionIdRef.current,
          system_description: systemDescription,
          security_alerts: securityAlerts,
          operator_feedback: operatorFeedback,
          images: [...systemDescriptionImages, ...securityAlertsImages],
          conversation_history: historyForBackend,
          report_manager_model: reportManagerModel || undefined,
          report_agent_model: reportAgentModel || undefined,
          report_reviewer_model: reportReviewerModel || undefined,
          plan_manager_model: planManagerModel || undefined,
          code_manager_model: codeManagerModel || undefined,
          code_agent_model: codeAgentModel || undefined,
          code_reviewer_model: codeReviewerModel || undefined,
          planner_agent_model: plannerAgentModel || undefined,
          validation_agent_model: validationAgentModel || undefined,
          report_manager_iterations: reportManagerIterations,
          plan_manager_iterations: planManagerIterations,
          code_manager_iterations: codeManagerIterations,
          planner_time_limit_minutes: plannerTimeLimitMinutes,
          compaction_model: compactionModel || undefined,
          report_manager_compaction: reportManagerCompaction / 100,
          report_agent_compaction: reportAgentCompaction / 100,
          report_reviewer_compaction: reportReviewerCompaction / 100,
          plan_manager_compaction: planManagerCompaction / 100,
          code_manager_compaction: codeManagerCompaction / 100,
          code_agent_compaction: codeAgentCompaction / 100,
          code_reviewer_compaction: codeReviewerCompaction / 100,
          planner_agent_compaction: plannerAgentCompaction / 100,
          validation_agent_compaction: validationAgentCompaction / 100
        }
        const { result } = await executeStreamingTool({
          url: API_AGENTS_ORCHESTRATOR_TOOL_URL,
          toolName: proposal.tool_name,
          toolArgs: proposal.tool_args,
          incidentId: selectedIncidentId,
          token,
          signal: controller.signal,
          onChunk: (text) => {
            streamEntry.output += text
            setConversationHistory((prev) => [...prev])
          },
          onSubEvent: (event) => {
            if (event.type === 'context_usage') {
              streamEntry.contextUsage = event
              setConversationHistory((prev) => [...prev])
              return
            }
            if (event.type === 'prompt') {
              streamEntry.prompt = event.text
              streamEntry.promptImages = event.images || []
              setConversationHistory((prev) => [...prev])
              return
            }
            const evTs = event._ts || Date.now()
            if (event.type === 'thinking_delta') {
              const last = streamEntry.subEvents[streamEntry.subEvents.length - 1]
              if (last && last.type === 'reasoning') {
                last.text += event.text
              } else {
                streamEntry.subEvents.push({
                  type: 'reasoning',
                  text: event.text,
                  _startTime: evTs
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
                  _startTime: evTs
                })
              }
            } else if (event.type === 'nested_event') {
              const lastToolCall = [...streamEntry.subEvents]
                .reverse()
                .find((e) => e.type === 'tool_call' && !e._completed)
              if (lastToolCall) {
                if (event.event.type === 'prompt') {
                  lastToolCall._prompt = event.event.text
                  lastToolCall._promptImages = event.event.images || []
                } else if (event.event.type === 'context_usage') {
                  lastToolCall._contextUsage = event.event
                } else {
                  if (!lastToolCall.subEvents) lastToolCall.subEvents = []
                  handleNestedSubEvent(lastToolCall.subEvents, event.event, evTs)
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
              if (!event._startTime) event._startTime = evTs
              streamEntry.subEvents.push(event)
            }
            setConversationHistory((prev) => [...prev])
          },
          onDtProgress: handleDtEvent,
          extraBody,
          onHeartbeat: (status) => {
            setLastHeartbeatTime(Date.now())
            setHeartbeatStatus(status)
            setLivenessStatus('alive')
          },
          onStale: () => setLivenessStatus('stale')
        })
        streamEntry.stopped = true
        const resultEntry = {
          role: 'tool',
          type: 'tool_result',
          tool_name: proposal.tool_name,
          result,
          subEvents: streamEntry.subEvents,
          prompt: streamEntry.prompt,
          contextUsage: streamEntry.contextUsage
        }
        setConversationHistory((prev) => [...prev, resultEntry])
        setExecutingTool(null)
        await callStep(conversationHistoryRef.current)
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
            .concat([
              { role: 'system', type: 'error', message: err.message, errorDetail: err.errorDetail }
            ])
        )
      }
      return
    }

    try {
      const res = await fetch(API_AGENTS_ORCHESTRATOR_TOOL_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        signal: controller.signal,
        body: JSON.stringify({
          session_id: sessionIdRef.current,
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
      setConversationHistory((prev) => [...prev, approvalEntry, resultEntry])
      setExecutingTool(null)
      await callStep(conversationHistoryRef.current)
    } catch (err) {
      if (err.name === 'AbortError') return
      setAlert({ type: 'danger', message: `Tool execution error: ${err.message}` })
      setExecutingTool(null)
    }
  }

  const handleDeny = async () => {
    if (!pendingProposal) return
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
    isSourceTabRef.current = true
    const denialEntry = {
      role: 'user',
      type: 'tool_approval',
      tool_name: pendingProposal.tool_name,
      approved: false
    }
    setConversationHistory((prev) => [...prev, denialEntry])
    setPendingProposal(null)
    await callStep(conversationHistoryRef.current)
  }

  const loadExample = async (incidentId) => {
    restoredSessionRef.current = true
    setRestoredSession(true)
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
      setSpecification(data.specification || '')
      setSpecificationCommands(data.specification_commands || [])
      setSystemDescriptionImages(data.system_description_images || [])
      setSecurityAlertsImages([])
    } catch (err) {
      setAlert({ type: 'danger', message: `Failed to load example: ${err.message}` })
    }
  }

  const handleClear = () => {
    isSourceTabRef.current = false
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
    const sid = sessionIdRef.current
    if (sid) {
      fetch(`${API_AGENTS_SESSIONS_URL}/${sid}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      }).catch(() => {})
    }
    setSessionId(null)
    setSystemDescription('')
    setSecurityAlerts('')
    setOperatorFeedback('')
    setSpecification('')
    setSpecificationCommands([])
    setSystemDescriptionImages([])
    setSecurityAlertsImages([])
    setConversationHistory([])
    setPendingProposal(null)
    setExpandedEntries({})
    setSelectedIncidentId(null)
  }

  const handleClearLog = () => {
    setConversationHistory([])
    setPendingProposal(null)
    setContextUsage(null)
    setExpandedEntries({})
  }

  const getPromptText = async () => {
    const res = await fetch(API_AGENTS_ORCHESTRATOR_PROMPT_URL, {
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
      images: [...systemDescriptionImages, ...securityAlertsImages]
    }
  }

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_AGENTS_REPORTS_URL}?agent_type=orchestrator`, {
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
          agent_type: 'orchestrator',
          report,
          incident_id: selectedIncidentId,
          conversation_history: cleanConversationHistory(conversationHistoryRef.current),
          model_name: orchestratorModel || undefined
        })
      })
      await fetchHistory()
      isSourceTabRef.current = false
      const sid = sessionIdRef.current
      if (sid) {
        fetch(`${API_AGENTS_SESSIONS_URL}/${sid}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({
            status: 'completed',
            ui_state: { running: false, executingTool: null, dtStatus: null }
          })
        }).catch(() => {})
      }
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
      await fetch(`${API_AGENTS_REPORTS_URL}?agent_type=orchestrator`, {
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

  const toggleEntry = (index, value) => {
    setExpandedEntries((prev) => ({
      ...prev,
      [index]: value !== undefined ? value : !prev[index]
    }))
  }

  const isAgentBusy = running || executingTool

  const renderFinalReport = (entry, index, isExpanded) => (
    <OrchestratorAgentReportView
      key={index}
      entry={entry}
      index={index}
      isExpanded={isExpanded}
      toggleEntry={toggleEntry}
    />
  )

  const renderToolResult = (entry) => {
    if (entry.tool_name === 'run_report_manager' && entry.result) {
      const r = entry.result
      return (
        <div style={{ marginTop: '10px' }}>
          {r.report_manager_report?.executive_summary && (
            <div className="ia-assessment-section">
              <div className="ia-assessment-label">Report Manager Summary</div>
              <p className="ia-assessment-body mb-0">{r.report_manager_report.executive_summary}</p>
            </div>
          )}
          {r.assessment && (
            <div style={{ marginTop: '10px' }}>
              <AssessmentBody
                report={
                  r.attack_path_image
                    ? { ...r.assessment, attack_path_image: r.attack_path_image }
                    : r.assessment
                }
              />
            </div>
          )}
        </div>
      )
    }
    if (entry.tool_name === 'run_plan_manager' && entry.result) {
      return <PlanManagerReportBody result={entry.result} />
    }
    return null
  }

  return (
    <div className="ResponsePlanner">
      {alert && (
        <div className={`alert alert-${alert.type} alert-dismissible`} role="alert">
          {alert.message}
          <button type="button" className="close" aria-label="Close" onClick={() => setAlert(null)}>
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
      )}

      <h2>Response planner</h2>
      <p className="subtitle">
        An agentic multi-agent system for autonomous incident response planning
      </p>
      <hr />

      <ul className="nav nav-tabs rp-tabs">
        <li className="nav-item">
          <button
            type="button"
            className={`nav-link${activeTab === 'config' ? ' active' : ''}`}
            onClick={() => setActiveTab('config')}
          >
            Incident description
          </button>
        </li>
        <li className="nav-item">
          <button
            type="button"
            className={`nav-link${activeTab === 'subagents' ? ' active' : ''}`}
            onClick={() => setActiveTab('subagents')}
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

      <div className="tab-content">
        {activeTab === 'config' && (
          <ConfigTab
            systemDescription={systemDescription}
            setSystemDescription={setSystemDescription}
            securityAlerts={securityAlerts}
            setSecurityAlerts={setSecurityAlerts}
            operatorFeedback={operatorFeedback}
            setOperatorFeedback={setOperatorFeedback}
            specificationCommands={specificationCommands}
            setSpecificationCommands={setSpecificationCommands}
            systemDescriptionImages={systemDescriptionImages}
            setSystemDescriptionImages={setSystemDescriptionImages}
            securityAlertsImages={securityAlertsImages}
            setSecurityAlertsImages={setSecurityAlertsImages}
            handlePaste={handlePaste}
            loadExample={loadExample}
            onRun={handleRun}
            onClear={handleClear}
            isAgentBusy={isAgentBusy}
            autopilot={autopilot}
            setAutopilot={setAutopilot}
          />
        )}

        {activeTab === 'subagents' && (
          <SubAgentsTab
            models={models}
            isAgentBusy={isAgentBusy}
            token={token}
            systemDescription={systemDescription}
            securityAlerts={securityAlerts}
            operatorFeedback={operatorFeedback}
            orchestratorModel={orchestratorModel}
            setOrchestratorModel={setOrchestratorModel}
            reportManagerModel={reportManagerModel}
            setReportManagerModel={setReportManagerModel}
            reportAgentModel={reportAgentModel}
            setReportAgentModel={setReportAgentModel}
            reportReviewerModel={reportReviewerModel}
            setReportReviewerModel={setReportReviewerModel}
            planManagerModel={planManagerModel}
            setPlanManagerModel={setPlanManagerModel}
            codeManagerModel={codeManagerModel}
            setCodeManagerModel={setCodeManagerModel}
            codeAgentModel={codeAgentModel}
            setCodeAgentModel={setCodeAgentModel}
            codeReviewerModel={codeReviewerModel}
            setCodeReviewerModel={setCodeReviewerModel}
            plannerAgentModel={plannerAgentModel}
            setPlannerAgentModel={setPlannerAgentModel}
            validationAgentModel={validationAgentModel}
            setValidationAgentModel={setValidationAgentModel}
            compactionModel={compactionModel}
            setCompactionModel={setCompactionModel}
            reportManagerIterations={reportManagerIterations}
            setReportManagerIterations={setReportManagerIterations}
            planManagerIterations={planManagerIterations}
            setPlanManagerIterations={setPlanManagerIterations}
            codeManagerIterations={codeManagerIterations}
            setCodeManagerIterations={setCodeManagerIterations}
            plannerTimeLimitMinutes={plannerTimeLimitMinutes}
            setPlannerTimeLimitMinutes={setPlannerTimeLimitMinutes}
            orchestratorCompaction={orchestratorCompaction}
            setOrchestratorCompaction={setOrchestratorCompaction}
            reportManagerCompaction={reportManagerCompaction}
            setReportManagerCompaction={setReportManagerCompaction}
            reportAgentCompaction={reportAgentCompaction}
            setReportAgentCompaction={setReportAgentCompaction}
            reportReviewerCompaction={reportReviewerCompaction}
            setReportReviewerCompaction={setReportReviewerCompaction}
            planManagerCompaction={planManagerCompaction}
            setPlanManagerCompaction={setPlanManagerCompaction}
            codeManagerCompaction={codeManagerCompaction}
            setCodeManagerCompaction={setCodeManagerCompaction}
            codeAgentCompaction={codeAgentCompaction}
            setCodeAgentCompaction={setCodeAgentCompaction}
            codeReviewerCompaction={codeReviewerCompaction}
            setCodeReviewerCompaction={setCodeReviewerCompaction}
            plannerAgentCompaction={plannerAgentCompaction}
            setPlannerAgentCompaction={setPlannerAgentCompaction}
            validationAgentCompaction={validationAgentCompaction}
            setValidationAgentCompaction={setValidationAgentCompaction}
          />
        )}

        <div style={{ display: activeTab === 'planning' ? undefined : 'none' }}>
          <AgentPlanningTab
            loading={!restoredSession}
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
            onClear={handleClearLog}
            onViewPrompt={getPromptText}
            dtStatus={dtStatus}
            modelName={orchestratorModel}
            livenessStatus={livenessStatus}
            lastHeartbeatTime={lastHeartbeatTime}
            heartbeatStatus={heartbeatStatus}
          />
        </div>

        {activeTab === 'history' && (
          <AgentHistoryTab
            reportHistory={reportHistory}
            deleteReport={deleteReport}
            deleteAllReports={deleteAllReports}
            renderReport={(report) => (
              <OrchestratorAgentReportView
                entry={{ type: 'orchestrator_agent_report', orchestrator_agent_report: report }}
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
    </div>
  )
}

export default ResponsePlanner
