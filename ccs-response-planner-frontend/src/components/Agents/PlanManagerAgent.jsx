import { useState, useEffect, useRef } from 'react'
import useTabWithHash from '../../hooks/useTabWithHash.js'
import { useAuth } from '../../contexts/AuthContext.jsx'
import {
  API_EXAMPLES_URL,
  API_AGENTS_PLAN_MANAGER_STEP_URL,
  API_AGENTS_PLAN_MANAGER_TOOL_URL,
  API_AGENTS_PLAN_MANAGER_PROMPT_URL,
  API_AGENTS_CODE_MANAGER_PROMPT_URL,
  API_AGENTS_CODE_PROMPT_URL,
  API_AGENTS_CODE_REVIEW_PROMPT_URL,
  API_AGENTS_PLANNER_PROMPT_URL,
  API_AGENTS_VALIDATION_PROMPT_URL,
  API_LLM_URL,
  API_AGENTS_REPORTS_URL,
  API_DT_PYTHON_STOP_URL
} from '../Common/constants'
import PlannerAgentReport from './PlannerAgentReport.jsx'
import ValidationAgentReport from './ValidationAgentReport.jsx'
import ImageThumbnails from './shared/ImageThumbnails.jsx'
import AgentConfigTable from './shared/AgentConfigTable.jsx'
import ExampleSelector from './shared/ExampleSelector.jsx'
import AgentPlanningTab from './shared/AgentPlanningTab.jsx'
import AgentHistoryTab from './shared/AgentHistoryTab.jsx'
import JobsTab from './shared/JobsTab.jsx'
import { useAgentSession } from './shared/useAgentSession.js'
import { cleanConversationHistory } from './shared/conversationUtils.js'
import { processDtEvent } from './shared/dtEventHandler.js'
import { PlanManagerReportBody } from './shared/ReportBodies.jsx'
import { pollJobEvents } from './shared/pollJobEvents.js'
import { STREAMING_TOOLS, executeStreamingTool } from './shared/streamingToolExec.js'

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
      subEvents.push({ type: 'reasoning', text: innerEvent.text, _startTime: Date.now() })
    }
  } else if (innerEvent.type === 'text_delta') {
    const last = subEvents[subEvents.length - 1]
    if (last && last.type === 'text') {
      last.text += innerEvent.text
    } else {
      subEvents.push({ type: 'text', text: innerEvent.text, _startTime: Date.now() })
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
        handleNestedSubEvent(lastToolCall.subEvents, innerEvent.event)
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
    if (!innerEvent._startTime) innerEvent._startTime = Date.now()
    subEvents.push(innerEvent)
  }
}

/**
 * Enrich a plan_manager_report with sub-reports extracted from conversation history.
 */
function enrichReport(report, history) {
  const enriched = { ...report }
  for (let i = history.length - 1; i >= 0; i--) {
    const e = history[i]
    if (e.type !== 'tool_result' || !e.result) continue
    if (e.tool_name === 'run_code_manager' && !enriched.code_report) {
      if (e.result.code_report && Object.keys(e.result.code_report).length > 0) {
        enriched.code_report = e.result.code_report
      }
    }
    if (e.tool_name === 'run_planner_agent') {
      if (!enriched.planner_report && e.result.planner_report) {
        enriched.planner_report = e.result.planner_report
      }
      if (!enriched.response_plan && e.result.response_plan) {
        enriched.response_plan = e.result.response_plan
      }
    }
    if (e.tool_name === 'run_validation_agent' && !enriched.validation_report) {
      if (e.result.validation_report && Object.keys(e.result.validation_report).length > 0) {
        enriched.validation_report = e.result.validation_report
      }
    }
  }
  return enriched
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
          <PlanManagerReportBody result={{ plan_manager_report: report, ...report }} />
        )}
      </div>
    </div>
  )
}

/**
 * Wrapper for history tab entries that lazily fetches conversation_history
 * and re-enriches the report with sub-reports when they are missing.
 */
function PlanManagerHistoryReport({ report, reportId, hasConversationHistory, token, logout }) {
  const [enrichedReport, setEnrichedReport] = useState(report)
  const [loading, setLoading] = useState(false)
  const fetchedRef = useRef(false)

  const isMissingSubs =
    !report?.code_report &&
    !report?.planner_report &&
    !report?.validation_report &&
    !report?.response_plan

  useEffect(() => {
    if (!isMissingSubs || !hasConversationHistory || !reportId || fetchedRef.current) return
    fetchedRef.current = true
    setLoading(true)
    const doFetch = async () => {
      try {
        const res = await fetch(`${API_AGENTS_REPORTS_URL}/${reportId}`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        if (res.status === 401 && logout) {
          logout()
          return
        }
        if (res.ok) {
          const data = await res.json()
          if (data?.conversation_history) {
            setEnrichedReport(enrichReport(report, data.conversation_history))
          }
        }
      } catch {
        /* ignore */
      } finally {
        setLoading(false)
      }
    }
    doFetch()
  }, [report, reportId, hasConversationHistory, token, logout, isMissingSubs])

  if (loading) {
    return (
      <div className="text-center" style={{ padding: '16px 0' }}>
        <span
          className="spinner-border spinner-border-sm"
          role="status"
          style={{ width: '14px', height: '14px', marginRight: '6px' }}
        />
        <span style={{ fontSize: '12px', color: '#6c757d' }}>Loading full report...</span>
      </div>
    )
  }

  return (
    <PlanManagerReport
      entry={{ type: 'plan_manager_report', plan_manager_report: enrichedReport }}
      index="history"
      isExpanded={true}
      toggleEntry={() => {}}
    />
  )
}

/**
 * PlanManagerAgent component — orchestrates the full incident response pipeline:
 * CodeManager -> Planner Agent -> Validation Agent with iterative revision.
 */
function PlanManagerAgent() {
  const { token, logout } = useAuth()
  const [activeTab, setActiveTab] = useTabWithHash('config')
  const [systemDescription, setSystemDescription] = useState('')
  const [incidentReport, setIncidentReport] = useState('')
  const [specification, setSpecification] = useState('')
  const [specificationCommands, setSpecificationCommands] = useState([])
  const [operatorFeedback, setOperatorFeedback] = useState('')
  const [systemDescriptionImages, setSystemDescriptionImages] = useState([])
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
  const [codeManagerModel, setCodeManagerModel] = useState('')
  const [codeAgentModel, setCodeAgentModel] = useState('')
  const [reviewerAgentModel, setReviewerAgentModel] = useState('')
  const [plannerAgentModel, setPlannerAgentModel] = useState('')
  const [validationAgentModel, setValidationAgentModel] = useState('')
  const [compactionModel, setCompactionModel] = useState('')
  const [compactionThreshold, setCompactionThreshold] = useState(80)
  const [codeManagerIterations, setCodeManagerIterations] = useState(1)
  const [plannerTimeLimitMinutes, setPlannerTimeLimitMinutes] = useState(10)
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
    pollingRef,
    restoredSession
  } = useAgentSession({
    agentType: 'plan_manager',
    token,
    logout,
    activeTab,
    onRestore: (session) => {
      const inputs = session.incident_inputs || {}
      setSystemDescription(inputs.systemDescription || '')
      setIncidentReport(inputs.incidentReport || '')
      setSpecification(inputs.specification || '')
      setSpecificationCommands(inputs.specificationCommands || [])
      setOperatorFeedback(inputs.operatorFeedback || '')
      setSystemDescriptionImages(inputs.systemDescriptionImages || [])
      setSelectedIncidentId(inputs.selectedIncidentId || null)
      const config = session.agent_config || {}
      setManagerModel(config.managerModel || '')
      setCodeManagerModel(config.codeManagerModel || '')
      setCodeAgentModel(config.codeAgentModel || '')
      setReviewerAgentModel(config.reviewerAgentModel || '')
      setPlannerAgentModel(config.plannerAgentModel || '')
      setValidationAgentModel(config.validationAgentModel || '')
      setCompactionModel(config.compactionModel || '')
      setCompactionThreshold(config.compactionThreshold || 80)
      setMaxIterations(config.maxIterations || 1)
      setCodeManagerIterations(config.codeManagerIterations || 1)
      setPlannerTimeLimitMinutes(config.plannerTimeLimitMinutes || 10)
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
      return [...cleaned, { role: 'system', type: 'error', message: 'Planning stopped by user.' }]
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
    const dtEntries = []
    setConversationHistory([...history, streamingEntry])
    try {
      let job_id = resumeJobId
      if (!job_id) {
        const res = await fetch(API_AGENTS_PLAN_MANAGER_STEP_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({
            system_description: systemDescription,
            incident_report: incidentReport,
            specification: specification,
            specification_commands: specificationCommands,
            operator_feedback: operatorFeedback,
            conversation_history: history.filter((e) => e.type !== 'dt_redeploy'),
            images: [...systemDescriptionImages],
            model_name: managerModel || undefined,
            last_prompt_tokens: contextUsage?.prompt_tokens || 0,
            compaction_model: compactionModel || undefined,
            compaction_threshold: compactionThreshold / 100,
            max_iterations: maxIterations,
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
            ...dtEntries,
            { role: 'system', type: 'error', message: msg }
          ])
          return
        }
        const resp = await res.json()
        job_id = resp.job_id
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
        onEvent: (event) => {
          setLastHeartbeatTime(Date.now())
          setLivenessStatus('alive')
          if (event.type === 'text' || event.type === 'thinking') {
            accumulated += event.delta
            setConversationHistory([
              ...history,
              ...compactionEntries,
              ...dtEntries,
              ...(dtEntries.some((e) => !e.done) ? [] : [{ ...streamingEntry, text: accumulated }])
            ])
          } else if (event.type === 'tool_input_started') {
            streamingEntry.generatingTool = event.tool_name
            setConversationHistory([
              ...history,
              ...compactionEntries,
              ...dtEntries,
              ...(dtEntries.some((e) => !e.done) ? [] : [{ ...streamingEntry, text: accumulated }])
            ])
          } else if (event.type === 'tool_input_delta') {
            toolInputAccumulated += event.delta
            streamingEntry.toolInput = toolInputAccumulated
            setConversationHistory([
              ...history,
              ...compactionEntries,
              ...dtEntries,
              ...(dtEntries.some((e) => !e.done) ? [] : [{ ...streamingEntry, text: accumulated }])
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
          } else if (event.type === 'plan_manager_report') {
            finalEntry = {
              role: 'model',
              type: 'plan_manager_report',
              plan_manager_report: event.plan_manager_report,
              thinking_trace: event.thinking_trace || ''
            }
          } else if (event.type === 'dt_progress' || event.type === 'dt_progress_detail') {
            processDtEvent(event, dtEntries, setDtStatus)
            setConversationHistory([...history, ...compactionEntries, ...dtEntries])
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
              ...dtEntries,
              ...(dtEntries.some((e) => !e.done) ? [] : [{ ...streamingEntry, text: accumulated }])
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
        const updated = [...history, ...compactionEntries, ...dtEntries, ...entries]
        setConversationHistory(updated)
        if (finalEntry.type === 'tool_proposal') {
          setPendingProposal(finalEntry)
        }
        if (finalEntry.type === 'plan_manager_report') {
          saveReport(enrichReport(finalEntry.plan_manager_report, updated), updated)
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
            planner_agent_summary: '',
            validation_summary: ''
          }
        }
        const fallbackHistory = [
          ...history,
          ...compactionEntries,
          ...dtEntries,
          {
            role: 'model',
            type: 'plan_manager_report',
            plan_manager_report: report
          }
        ]
        setConversationHistory(fallbackHistory)
        saveReport(enrichReport(report, fallbackHistory), fallbackHistory)
      } else {
        setConversationHistory([
          ...history,
          ...compactionEntries,
          ...dtEntries,
          { role: 'system', type: 'error', message: 'Agent returned an empty response.' }
        ])
      }
    } catch (err) {
      if (err.name === 'AbortError') return
      setAlert({ type: 'danger', message: `Agent error: ${err.message}` })
      setConversationHistory([
        ...history,
        ...compactionEntries,
        ...dtEntries,
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

  const handleRun = async () => {
    setPendingProposal(null)
    setConversationHistory([])
    setExpandedEntries({})
    setContextUsage(null)
    setActiveTab('planning')
    setRunning(true)
    await createSession(
      {
        systemDescription,
        incidentReport,
        specification,
        specificationCommands,
        operatorFeedback,
        systemDescriptionImages,
        selectedIncidentId
      },
      {
        managerModel,
        codeManagerModel,
        codeAgentModel,
        reviewerAgentModel,
        plannerAgentModel,
        validationAgentModel,
        compactionModel,
        compactionThreshold,
        maxIterations,
        codeManagerIterations,
        plannerTimeLimitMinutes,
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
      const streamEntry = {
        type: 'tool_streaming',
        tool_name: proposal.tool_name,
        output: '',
        subEvents: [],
        _startTime: Date.now()
      }
      const latestHistory = conversationHistoryRef.current
      const base = [...latestHistory, approvalEntry, streamEntry]
      setConversationHistory(base)
      try {
        const extraBody = {
          system_description: systemDescription,
          incident_report: incidentReport,
          specification: specification,
          specification_commands: specificationCommands,
          operator_feedback: operatorFeedback,
          images: [...systemDescriptionImages],
          conversation_history: latestHistory.filter((e) => e.type !== 'dt_redeploy'),
          code_manager_model: codeManagerModel || undefined,
          code_agent_model: codeAgentModel || undefined,
          reviewer_agent_model: reviewerAgentModel || undefined,
          planner_agent_model: plannerAgentModel || undefined,
          validation_agent_model: validationAgentModel || undefined,
          code_manager_iterations: codeManagerIterations,
          planner_time_limit_minutes: plannerTimeLimitMinutes,
          compaction_model: compactionModel || undefined,
          compaction_threshold: compactionThreshold / 100,
          session_id: sessionIdRef.current
        }
        const { result } = await executeStreamingTool({
          url: API_AGENTS_PLAN_MANAGER_TOOL_URL,
          toolName: proposal.tool_name,
          toolArgs: proposal.tool_args,
          incidentId: selectedIncidentId,
          token,
          signal: controller.signal,
          onHeartbeat: (status) => {
            setLastHeartbeatTime(Date.now())
            setHeartbeatStatus(status)
            setLivenessStatus('alive')
          },
          onStale: () => setLivenessStatus('stale'),
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
            .concat([
              { role: 'system', type: 'error', message: err.message, errorDetail: err.errorDetail }
            ])
        )
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
          incident_id: selectedIncidentId,
          session_id: sessionIdRef.current
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
    const updated = [...conversationHistoryRef.current, denialEntry]
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
      setSpecificationCommands(data.specification_commands || [])
      setOperatorFeedback('')
      setSystemDescriptionImages(data.system_description_images || [])

      const infoRes = await fetch(
        `${API_AGENTS_REPORTS_URL}?agent_type=report&incident_id=${incidentId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      if (infoRes.ok) {
        const infoReports = await infoRes.json()
        if (infoReports.length > 0) {
          const reportText = { ...(infoReports[0].report || {}) }
          delete reportText.attack_path_image
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
    setSpecificationCommands([])
    setOperatorFeedback('')
    setSystemDescriptionImages([])
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
      subEvents: [],
      _startTime: startTime || Date.now()
    }
    setConversationHistory((prev) => [...prev, streamEntry])
    setExecutingTool(toolName)
    const controller = new AbortController()
    abortControllerRef.current = controller
    try {
      const latestHistory = conversationHistoryRef.current
      const extraBody = {
        system_description: systemDescription,
        incident_report: incidentReport,
        specification: specification,
        specification_commands: specificationCommands,
        operator_feedback: operatorFeedback,
        images: [...systemDescriptionImages],
        conversation_history: latestHistory.filter((e) => e.type !== 'dt_redeploy'),
        code_manager_model: codeManagerModel || undefined,
        code_agent_model: codeAgentModel || undefined,
        reviewer_agent_model: reviewerAgentModel || undefined,
        planner_agent_model: plannerAgentModel || undefined,
        validation_agent_model: validationAgentModel || undefined,
        code_manager_iterations: codeManagerIterations,
        planner_time_limit_minutes: plannerTimeLimitMinutes,
        compaction_model: compactionModel || undefined,
        compaction_threshold: compactionThreshold / 100,
        session_id: sessionIdRef.current
      }
      const { result } = await executeStreamingTool({
        url: API_AGENTS_PLAN_MANAGER_TOOL_URL,
        toolName,
        toolArgs: {},
        incidentId: selectedIncidentId,
        token,
        signal: controller.signal,
        resumeJobId: jobId,
        onHeartbeat: (status) => {
          setLastHeartbeatTime(Date.now())
          setHeartbeatStatus(status)
          setLivenessStatus('alive')
        },
        onStale: () => setLivenessStatus('stale'),
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
            if (!event._startTime) event._startTime = Date.now()
            streamEntry.subEvents.push(event)
          }
          setConversationHistory((prev) => [...prev])
        },
        extraBody
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
        specification_commands: specificationCommands,
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
      images: [...systemDescriptionImages]
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

  const saveReport = async (report, historyToSave) => {
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
          conversation_history: cleanConversationHistory(historyToSave),
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
      await fetch(`${API_AGENTS_REPORTS_URL}?agent_type=plan_manager`, {
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
        </div>
      )
    }
    if (entry.tool_name === 'run_planner_agent' && entry.result) {
      const r = entry.result
      return (
        <div style={{ marginTop: '10px' }}>
          {r.planner_report && (
            <PlannerAgentReport
              entry={{ type: 'planner_report', planner_report: r.planner_report }}
              index="pm-planner"
              isExpanded={true}
              toggleEntry={() => {}}
            />
          )}
          {r.response_plan && (
            <div className="ia-assessment-section" style={{ marginTop: '10px' }}>
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
          {r.validation_report && (
            <ValidationAgentReport
              entry={{ type: 'validation_report', validation_report: r.validation_report }}
              index="pm-val"
              isExpanded={true}
              toggleEntry={() => {}}
            />
          )}
        </div>
      )
    }
    return null
  }

  if (!restoredSession) {
    return (
      <div className="text-center" style={{ padding: '48px 0' }}>
        <div className="spinner-border" role="status" style={{ width: '2.5rem', height: '2.5rem' }}>
          <span className="sr-only">Loading...</span>
        </div>
        <p className="text-muted mt-3">Loading agent...</p>
      </div>
    )
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
        <div style={{ marginTop: '16px' }}>
          <div className="ia-description">
            <p>
              This agent orchestrates the full incident response pipeline: CodeManager (MDP
              generation) -&gt; Planner Agent (policy training) -&gt; Validation Agent (digital twin
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
              Paste the incident report/assessment produced by the Report Agent.
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
            <label>Specification commands</label>
            <p className="ia-hint">Service-level requirements that must hold after recovery.</p>
            <div
              style={{
                border: '1px solid #dee2e6',
                borderRadius: '4px',
                padding: '10px 14px',
                fontSize: '12px',
                maxHeight: '300px',
                overflowY: 'auto'
              }}
            >
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #dee2e6', textAlign: 'left' }}>
                    <th style={{ padding: '4px 8px 6px 0', fontWeight: 600 }}>Host</th>
                    <th style={{ padding: '4px 8px 6px 0', fontWeight: 600 }}>Description</th>
                    <th style={{ padding: '4px 8px 6px 0', fontWeight: 600 }}>Command</th>
                    <th style={{ padding: '4px 0 6px 0', fontWeight: 600, width: '32px' }} />
                  </tr>
                </thead>
                <tbody>
                  {specificationCommands.map((cmd, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #f0f0f0' }}>
                      <td style={{ padding: '3px 6px 3px 0' }}>
                        <input
                          type="text"
                          className="form-control form-control-sm"
                          value={cmd.host}
                          onChange={(e) =>
                            setSpecificationCommands((prev) =>
                              prev.map((c, j) => (j === i ? { ...c, host: e.target.value } : c))
                            )
                          }
                          disabled={isAgentBusy}
                          placeholder="hostname"
                          style={{ fontSize: '12px', fontFamily: 'monospace' }}
                        />
                      </td>
                      <td style={{ padding: '3px 6px 3px 0' }}>
                        <input
                          type="text"
                          className="form-control form-control-sm"
                          value={cmd.description}
                          onChange={(e) =>
                            setSpecificationCommands((prev) =>
                              prev.map((c, j) =>
                                j === i ? { ...c, description: e.target.value } : c
                              )
                            )
                          }
                          disabled={isAgentBusy}
                          placeholder="what to verify"
                          style={{ fontSize: '12px' }}
                        />
                      </td>
                      <td style={{ padding: '3px 6px 3px 0' }}>
                        <input
                          type="text"
                          className="form-control form-control-sm"
                          value={cmd.command}
                          onChange={(e) =>
                            setSpecificationCommands((prev) =>
                              prev.map((c, j) => (j === i ? { ...c, command: e.target.value } : c))
                            )
                          }
                          disabled={isAgentBusy}
                          placeholder="shell command"
                          style={{ fontSize: '12px', fontFamily: 'monospace' }}
                        />
                      </td>
                      <td style={{ padding: '3px 0', textAlign: 'center' }}>
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-danger"
                          onClick={() =>
                            setSpecificationCommands((prev) => prev.filter((_, j) => j !== i))
                          }
                          disabled={isAgentBusy}
                          title="Remove row"
                          style={{ padding: '1px 6px', fontSize: '11px', lineHeight: 1.4 }}
                        >
                          <i className="fa fa-times" aria-hidden="true" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {specificationCommands.length === 0 && (
                <p
                  style={{
                    textAlign: 'center',
                    color: '#888',
                    margin: '8px 0 4px',
                    fontSize: '12px'
                  }}
                >
                  No specification commands. Add rows manually or load an example.
                </p>
              )}
              <button
                type="button"
                className="btn btn-sm btn-outline-secondary"
                onClick={() =>
                  setSpecificationCommands((prev) => [
                    ...prev,
                    { host: '', description: '', command: '' }
                  ])
                }
                disabled={isAgentBusy}
                style={{ marginTop: '6px', fontSize: '11px' }}
              >
                <i className="fa fa-plus" aria-hidden="true" /> Add row
              </button>
            </div>
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
            specification_commands: specificationCommands,
            operator_feedback: operatorFeedback
          })}
          rows={[
            {
              label: 'Plan Manager',
              model: managerModel,
              setModel: setManagerModel,
              iteration: {
                min: 1,
                max: 5,
                value: maxIterations,
                set: setMaxIterations,
                suffix: 'iterations'
              },
              compaction: compactionThreshold,
              setCompaction: setCompactionThreshold,
              promptUrl: API_AGENTS_PLAN_MANAGER_PROMPT_URL
            },
            {
              label: 'Code Manager',
              model: codeManagerModel,
              setModel: setCodeManagerModel,
              iteration: {
                min: 1,
                max: 10,
                value: codeManagerIterations,
                set: setCodeManagerIterations,
                suffix: 'iterations'
              },
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
              label: 'Planner Agent',
              model: plannerAgentModel,
              setModel: setPlannerAgentModel,
              iteration: {
                min: 1,
                max: 60,
                value: plannerTimeLimitMinutes,
                set: setPlannerTimeLimitMinutes,
                suffix: 'min'
              },
              promptUrl: API_AGENTS_PLANNER_PROMPT_URL
            },
            {
              label: 'Validation Agent',
              model: validationAgentModel,
              setModel: setValidationAgentModel,
              promptUrl: API_AGENTS_VALIDATION_PROMPT_URL
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
          onViewPrompt={getPromptText}
          dtStatus={dtStatus}
          modelName={managerModel}
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
          renderReport={(report, entry) => (
            <PlanManagerHistoryReport
              report={report}
              reportId={entry?.id}
              hasConversationHistory={entry?.has_conversation_history}
              token={token}
              logout={logout}
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
  )
}

export default PlanManagerAgent
