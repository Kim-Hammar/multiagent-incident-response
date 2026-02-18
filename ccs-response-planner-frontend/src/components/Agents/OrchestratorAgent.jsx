import { useState, useEffect, useRef } from 'react'
import useTabWithHash from '../../hooks/useTabWithHash.js'
import { useAuth } from '../../contexts/AuthContext.jsx'
import {
  API_EXAMPLES_URL,
  API_AGENTS_ORCHESTRATOR_STEP_URL,
  API_AGENTS_ORCHESTRATOR_TOOL_URL,
  API_AGENTS_ORCHESTRATOR_PROMPT_URL,
  API_AGENTS_REPORT_MANAGER_PROMPT_URL,
  API_AGENTS_REPORT_PROMPT_URL,
  API_AGENTS_REPORT_REVIEW_PROMPT_URL,
  API_AGENTS_PLAN_MANAGER_PROMPT_URL,
  API_AGENTS_CODE_MANAGER_PROMPT_URL,
  API_AGENTS_CODE_PROMPT_URL,
  API_AGENTS_CODE_REVIEW_PROMPT_URL,
  API_AGENTS_RL_PROMPT_URL,
  API_AGENTS_VALIDATION_PROMPT_URL,
  API_LLM_URL,
  API_AGENTS_REPORTS_URL,
  API_DT_PYTHON_STOP_URL
} from '../Common/constants'
import ImageThumbnails from './shared/ImageThumbnails.jsx'
import AgentConfigTable from './shared/AgentConfigTable.jsx'
import ExampleSelector from './shared/ExampleSelector.jsx'
import AgentPlanningTab from './shared/AgentPlanningTab.jsx'
import AgentHistoryTab from './shared/AgentHistoryTab.jsx'
import JobsTab from './shared/JobsTab.jsx'
import { useAgentSession } from './shared/useAgentSession.js'
import { cleanConversationHistory } from './shared/conversationUtils.js'
import { pollJobEvents } from './shared/pollJobEvents.js'
import { STREAMING_TOOLS, executeStreamingTool } from './shared/streamingToolExec.js'
import {
  AssessmentBody,
  CodeReportBody,
  ValidationReportBody,
  PlannerReportInline,
  PlanManagerReportBody
} from './shared/ReportBodies.jsx'
/**
 * Extract rich sub-agent data from conversation history and merge it into
 * the orchestrator report so the final view has full details.
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
 * Render the final consolidated report for the orchestrator agent.
 */
function OrchestratorAgentReportView({ entry, index, isExpanded, toggleEntry }) {
  const report = entry.orchestrator_agent_report || {}

  return (
    <div className="card ia-entry ia-result-entry">
      <div className="card-body">
        <div className="ia-result-header" onClick={() => toggleEntry(index)}>
          <i className="fa fa-flag-checkered" aria-hidden="true" />
          <span className="ia-result-label">Final Response Plan</span>
          {report.iterations != null && (
            <span className="badge badge-info ml-2">{report.iterations} iteration(s)</span>
          )}
          <span className="ia-toggle-hint">{isExpanded ? 'collapse' : 'expand'}</span>
        </div>
        {isExpanded && (
          <div style={{ marginTop: '10px' }}>
            {report.executive_summary && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Executive Summary</div>
                <p className="ia-assessment-body mb-0">{report.executive_summary}</p>
              </div>
            )}
            {report.assessment && Object.keys(report.assessment).length > 0 && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Incident Assessment</div>
                <AssessmentBody report={report.assessment} />
              </div>
            )}
            {report.code_report && Object.keys(report.code_report).length > 0 && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">MDP Code Report</div>
                <CodeReportBody report={report.code_report} />
              </div>
            )}
            {report.planner_report && Object.keys(report.planner_report).length > 0 && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">RL Planner Report</div>
                <PlannerReportInline report={report.planner_report} />
              </div>
            )}
            {report.validation_report && Object.keys(report.validation_report).length > 0 && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Validation Report</div>
                <ValidationReportBody report={report.validation_report} />
              </div>
            )}
            {report.response_plan && (
              <div className="ia-assessment-section">
                <div className="ia-assessment-label">Response Plan</div>
                <pre
                  style={{
                    background: '#f5f5f5',
                    padding: '12px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    maxHeight: '400px',
                    overflow: 'auto',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word'
                  }}
                >
                  {report.response_plan}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * OrchestratorAgent component — top-level orchestrator that coordinates the full
 * end-to-end incident response pipeline: ReportManager (assessment) ->
 * PlanManager (MDP + RL + validation) -> consolidated report.
 */
function OrchestratorAgent() {
  const { token, logout } = useAuth()
  const [activeTab, setActiveTab] = useTabWithHash('config')
  const [systemDescription, setSystemDescription] = useState('')
  const [securityAlerts, setSecurityAlerts] = useState('')
  const [operatorFeedback, setOperatorFeedback] = useState('')
  const [systemDescriptionImages, setSystemDescriptionImages] = useState([])
  const [securityAlertsImages, setSecurityAlertsImages] = useState([])
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
  const [rlAgentModel, setRlAgentModel] = useState('')
  const [validationAgentModel, setValidationAgentModel] = useState('')
  const [compactionModel, setCompactionModel] = useState('')
  const [compactionThreshold, setCompactionThreshold] = useState(80)
  const [reportManagerIterations, setReportManagerIterations] = useState(1)
  const [planManagerIterations, setPlanManagerIterations] = useState(1)
  const [codeManagerIterations, setCodeManagerIterations] = useState(1)
  const [rlTimeLimitMinutes, setRlTimeLimitMinutes] = useState(10)
  const [reportHistory, setReportHistory] = useState([])
  const [selectedIncidentId, setSelectedIncidentId] = useState(null)
  const logEndRef = useRef(null)
  const streamingTraceRef = useRef(null)
  const isNearBottomRef = useRef(true)
  const abortControllerRef = useRef(null)
  const [lastHeartbeatTime, setLastHeartbeatTime] = useState(Date.now())
  const [livenessStatus, setLivenessStatus] = useState('alive')
  const [heartbeatStatus, setHeartbeatStatus] = useState('')
  const managerStartTimeRef = useRef(null)

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
    cancelRunningJob,
    createSession,
    clearSession,
    markSessionCancelled,
    setPendingProposalRef,
    setContextUsageRef,
    setUiStateRef,
    pollingRef
  } = useAgentSession({
    agentType: 'orchestrator',
    token,
    logout,
    activeTab,
    incidentInputs: {
      systemDescription,
      securityAlerts,
      operatorFeedback,
      systemDescriptionImages,
      securityAlertsImages
    },
    agentConfig: {
      orchestratorModel,
      reportManagerModel,
      reportAgentModel,
      reportReviewerModel,
      planManagerModel,
      codeManagerModel,
      codeAgentModel,
      codeReviewerModel,
      rlAgentModel,
      validationAgentModel,
      compactionModel,
      compactionThreshold,
      reportManagerIterations,
      planManagerIterations,
      codeManagerIterations,
      rlTimeLimitMinutes,
      autopilot
    },
    onRestore: (session) => {
      if (session.incident_inputs) {
        const inp = session.incident_inputs
        if (inp.systemDescription != null) setSystemDescription(inp.systemDescription)
        if (inp.securityAlerts != null) setSecurityAlerts(inp.securityAlerts)
        if (inp.operatorFeedback != null) setOperatorFeedback(inp.operatorFeedback)
        if (inp.systemDescriptionImages) setSystemDescriptionImages(inp.systemDescriptionImages)
        if (inp.securityAlertsImages) setSecurityAlertsImages(inp.securityAlertsImages)
      }
      if (session.agent_config) {
        const cfg = session.agent_config
        if (cfg.orchestratorModel != null) setOrchestratorModel(cfg.orchestratorModel)
        if (cfg.reportManagerModel != null) setReportManagerModel(cfg.reportManagerModel)
        if (cfg.reportAgentModel != null) setReportAgentModel(cfg.reportAgentModel)
        if (cfg.reportReviewerModel != null) setReportReviewerModel(cfg.reportReviewerModel)
        if (cfg.planManagerModel != null) setPlanManagerModel(cfg.planManagerModel)
        if (cfg.codeManagerModel != null) setCodeManagerModel(cfg.codeManagerModel)
        if (cfg.codeAgentModel != null) setCodeAgentModel(cfg.codeAgentModel)
        if (cfg.codeReviewerModel != null) setCodeReviewerModel(cfg.codeReviewerModel)
        if (cfg.rlAgentModel != null) setRlAgentModel(cfg.rlAgentModel)
        if (cfg.validationAgentModel != null) setValidationAgentModel(cfg.validationAgentModel)
        if (cfg.compactionModel != null) setCompactionModel(cfg.compactionModel)
        if (cfg.compactionThreshold != null) setCompactionThreshold(cfg.compactionThreshold)
        if (cfg.reportManagerIterations != null)
          setReportManagerIterations(cfg.reportManagerIterations)
        if (cfg.planManagerIterations != null) setPlanManagerIterations(cfg.planManagerIterations)
        if (cfg.codeManagerIterations != null) setCodeManagerIterations(cfg.codeManagerIterations)
        if (cfg.rlTimeLimitMinutes != null) setRlTimeLimitMinutes(cfg.rlTimeLimitMinutes)
        if (cfg.autopilot != null) setAutopilot(cfg.autopilot)
      }
      if (session.pending_proposal) setPendingProposal(session.pending_proposal)
      if (session.incident_id) setSelectedIncidentId(session.incident_id)
    },
    onResumeJob: (job) => {
      setActiveTab('planning')
      if (job.tool_name) {
        resumeToolJob(
          job.id,
          job.tool_name,
          job.started_at ? new Date(job.started_at).getTime() : Date.now()
        )
      } else {
        callStep(conversationHistoryRef.current)
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
    cancelRunningJob()
    markSessionCancelled()
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

  const stripImagesFromHistory = (history) =>
    history.map((entry) => {
      if (entry.type === 'tool_result' && entry.result?.image) {
        return {
          ...entry,
          result: { status: 'success', message: 'Image generated successfully' }
        }
      }
      if (entry.type === 'tool_result' && entry.result?.attack_path_image) {
        const rest = Object.fromEntries(
          Object.entries(entry.result).filter(([k]) => k !== 'attack_path_image')
        )
        return { ...entry, result: rest }
      }
      return entry
    })

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
    setConversationHistory((prev) => [...prev, streamingEntry])
    let job_id = resumeJobId
    try {
      if (!job_id) {
        const res = await fetch(API_AGENTS_ORCHESTRATOR_STEP_URL, {
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
            images: [...systemDescriptionImages, ...securityAlertsImages],
            model_name: orchestratorModel || undefined,
            last_prompt_tokens: contextUsage?.prompt_tokens || 0,
            compaction_model: compactionModel || undefined,
            compaction_threshold: compactionThreshold / 100,
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
          setConversationHistory((prev) => {
            const base = prev.filter((e) => e !== streamingEntry)
            return [...base, { role: 'system', type: 'error', message: msg }]
          })
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
            streamingEntry.text = accumulated
            setConversationHistory((prev) => [...prev])
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
          } else if (event.type === 'dt_progress') {
            setDtStatus(event.message)
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
            setConversationHistory((prev) => {
              const idx = prev.indexOf(streamingEntry)
              if (idx === -1) return [...prev, compactionEntry]
              return [...prev.slice(0, idx), compactionEntry, ...prev.slice(idx)]
            })
          } else if (event.type === 'error') {
            const msg = event.message || 'Agent stream error'
            setAlert({ type: 'danger', message: msg })
            setConversationHistory((prev) => {
              const base = prev.filter((e) => e !== streamingEntry)
              return [...base, { role: 'system', type: 'error', message: msg }]
            })
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
          saveReport(finalEntry.orchestrator_agent_report, conversationHistoryRef.current)
        }
      } else if (accumulated) {
        let report
        try {
          report = JSON.parse(accumulated)
        } catch {
          report = {
            executive_summary: accumulated,
            iterations: 0,
            assessment_summary: '',
            response_plan_summary: ''
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
        saveReport(report, conversationHistoryRef.current)
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
      setAlert({ type: 'danger', message: `Agent error: ${err.message}` })
      setConversationHistory((prev) => {
        const base = prev.filter((e) => e !== streamingEntry)
        return [...base, { role: 'system', type: 'error', message: err.message }]
      })
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
    managerStartTimeRef.current = Date.now()
    await createSession(selectedIncidentId)
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
        _startTime: managerStartTimeRef.current || Date.now()
      }
      const historyForBackend = conversationHistoryRef.current
      setConversationHistory((prev) => [...prev, approvalEntry, streamEntry])
      try {
        const extraBody = {
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
          rl_agent_model: rlAgentModel || undefined,
          validation_agent_model: validationAgentModel || undefined,
          report_manager_iterations: reportManagerIterations,
          plan_manager_iterations: planManagerIterations,
          code_manager_iterations: codeManagerIterations,
          rl_time_limit_minutes: rlTimeLimitMinutes,
          compaction_model: compactionModel || undefined,
          compaction_threshold: compactionThreshold / 100,
          session_id: sessionIdRef.current
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
          result
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
            .concat([{ role: 'system', type: 'error', message: err.message }])
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
    const denialEntry = {
      role: 'user',
      type: 'tool_approval',
      tool_name: pendingProposal.tool_name,
      tool_args: pendingProposal.tool_args,
      approved: false
    }
    setConversationHistory((prev) => [...prev, denialEntry])
    setPendingProposal(null)
    await callStep(conversationHistoryRef.current)
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
        security_alerts: securityAlerts,
        operator_feedback: operatorFeedback,
        images: [...systemDescriptionImages, ...securityAlertsImages],
        conversation_history: latestHistory,
        report_manager_model: reportManagerModel || undefined,
        report_agent_model: reportAgentModel || undefined,
        report_reviewer_model: reportReviewerModel || undefined,
        plan_manager_model: planManagerModel || undefined,
        code_manager_model: codeManagerModel || undefined,
        code_agent_model: codeAgentModel || undefined,
        code_reviewer_model: codeReviewerModel || undefined,
        rl_agent_model: rlAgentModel || undefined,
        validation_agent_model: validationAgentModel || undefined,
        report_manager_iterations: reportManagerIterations,
        plan_manager_iterations: planManagerIterations,
        code_manager_iterations: codeManagerIterations,
        rl_time_limit_minutes: rlTimeLimitMinutes,
        compaction_model: compactionModel || undefined,
        compaction_threshold: compactionThreshold / 100,
        session_id: sessionIdRef.current
      }
      const { result } = await executeStreamingTool({
        url: API_AGENTS_ORCHESTRATOR_TOOL_URL,
        toolName,
        toolArgs: {},
        incidentId: selectedIncidentId,
        token,
        signal: controller.signal,
        resumeJobId: jobId,
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
        extraBody,
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
      setExecutingTool(null)
    }
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

  const saveReport = async (report, historyToSave) => {
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
          conversation_history: cleanConversationHistory(historyToSave),
          model_name: orchestratorModel || undefined
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

  const toggleEntry = (index) => {
    setExpandedEntries((prev) => ({ ...prev, [index]: !prev[index] }))
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
            <div className="ia-assessment-section" style={{ marginTop: '10px' }}>
              <div className="ia-assessment-label">Incident Report</div>
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
              This is the top-level orchestrator agent that coordinates the full end-to-end incident
              response pipeline. It first runs the ReportManager to generate and review an incident
              assessment, then feeds that assessment to the PlanManager to generate MDP code, train
              an RL policy, and validate it on the digital twin. Finally, it produces a consolidated
              incident response report.
            </p>
          </div>

          <div className="ia-section">
            <label htmlFor="oa-system-desc">System description</label>
            <p className="ia-hint">
              Describe the target system, its architecture, hosts, and services.
            </p>
            <textarea
              id="oa-system-desc"
              className="form-control ia-textarea"
              rows="6"
              value={systemDescription}
              onChange={(e) => setSystemDescription(e.target.value)}
              onPaste={handlePaste(setSystemDescriptionImages)}
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
            <label htmlFor="oa-security-alerts">Security alerts</label>
            <p className="ia-hint">
              Paste the security alerts/logs that triggered incident response.
            </p>
            <textarea
              id="oa-security-alerts"
              className="form-control ia-textarea"
              rows="6"
              value={securityAlerts}
              onChange={(e) => setSecurityAlerts(e.target.value)}
              onPaste={handlePaste(setSecurityAlertsImages)}
              disabled={isAgentBusy}
              placeholder="e.g., IDS alert: SSH brute-force detected from 10.0.0.2 targeting server 3..."
            />
            <ImageThumbnails
              images={securityAlertsImages}
              setImages={setSecurityAlertsImages}
              disabled={isAgentBusy}
            />
          </div>
          <div className="ia-section">
            <label htmlFor="oa-operator-feedback">Operator feedback (optional)</label>
            <p className="ia-hint">Additional guidance or constraints for the pipeline.</p>
            <textarea
              id="oa-operator-feedback"
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
            disabled={isAgentBusy || (!systemDescription && !securityAlerts)}
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
              id="oa-autopilot"
              checked={autopilot}
              onChange={(e) => setAutopilot(e.target.checked)}
            />
            <label className="form-check-label" htmlFor="oa-autopilot">
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
            security_alerts: securityAlerts,
            operator_feedback: operatorFeedback
          })}
          rows={[
            {
              label: 'Orchestrator',
              model: orchestratorModel,
              setModel: setOrchestratorModel,
              promptUrl: API_AGENTS_ORCHESTRATOR_PROMPT_URL,
              iteration: null,
              compaction: compactionThreshold,
              setCompaction: setCompactionThreshold
            },
            {
              label: 'Report Manager',
              model: reportManagerModel,
              setModel: setReportManagerModel,
              promptUrl: API_AGENTS_REPORT_MANAGER_PROMPT_URL,
              iteration: {
                value: reportManagerIterations,
                set: setReportManagerIterations,
                min: 1,
                max: 10,
                suffix: 'iterations'
              },
              compaction: null,
              setCompaction: null
            },
            {
              label: 'Report Agent',
              model: reportAgentModel,
              setModel: setReportAgentModel,
              promptUrl: API_AGENTS_REPORT_PROMPT_URL,
              iteration: null,
              compaction: null,
              setCompaction: null
            },
            {
              label: 'Report Reviewer',
              model: reportReviewerModel,
              setModel: setReportReviewerModel,
              promptUrl: API_AGENTS_REPORT_REVIEW_PROMPT_URL,
              iteration: null,
              compaction: null,
              setCompaction: null
            },
            {
              label: 'Plan Manager',
              model: planManagerModel,
              setModel: setPlanManagerModel,
              promptUrl: API_AGENTS_PLAN_MANAGER_PROMPT_URL,
              iteration: {
                value: planManagerIterations,
                set: setPlanManagerIterations,
                min: 1,
                max: 5,
                suffix: 'iterations'
              },
              compaction: null,
              setCompaction: null
            },
            {
              label: 'Code Manager',
              model: codeManagerModel,
              setModel: setCodeManagerModel,
              promptUrl: API_AGENTS_CODE_MANAGER_PROMPT_URL,
              iteration: {
                value: codeManagerIterations,
                set: setCodeManagerIterations,
                min: 1,
                max: 10,
                suffix: 'iterations'
              },
              compaction: null,
              setCompaction: null
            },
            {
              label: 'Code Agent',
              model: codeAgentModel,
              setModel: setCodeAgentModel,
              promptUrl: API_AGENTS_CODE_PROMPT_URL,
              iteration: null,
              compaction: null,
              setCompaction: null
            },
            {
              label: 'Code Reviewer',
              model: codeReviewerModel,
              setModel: setCodeReviewerModel,
              promptUrl: API_AGENTS_CODE_REVIEW_PROMPT_URL,
              iteration: null,
              compaction: null,
              setCompaction: null
            },
            {
              label: 'RL Agent',
              model: rlAgentModel,
              setModel: setRlAgentModel,
              promptUrl: API_AGENTS_RL_PROMPT_URL,
              iteration: {
                value: rlTimeLimitMinutes,
                set: setRlTimeLimitMinutes,
                min: 1,
                max: 60,
                suffix: 'min'
              },
              compaction: null,
              setCompaction: null
            },
            {
              label: 'Validation Agent',
              model: validationAgentModel,
              setModel: setValidationAgentModel,
              promptUrl: API_AGENTS_VALIDATION_PROMPT_URL,
              iteration: null,
              compaction: null,
              setCompaction: null
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
          renderToolResult={renderToolResult}
          onStop={handleStop}
          onViewPrompt={getPromptText}
          dtStatus={dtStatus}
          modelName={orchestratorModel}
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
  )
}

export default OrchestratorAgent
