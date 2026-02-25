import { useState, useEffect, useRef } from 'react'
import useTabWithHash from '../../hooks/useTabWithHash.js'
import { useAuth } from '../../contexts/AuthContext.jsx'
import {
  API_EXAMPLES_URL,
  API_AGENTS_REPORT_MANAGER_STEP_URL,
  API_AGENTS_REPORT_MANAGER_TOOL_URL,
  API_AGENTS_REPORT_MANAGER_PROMPT_URL,
  API_AGENTS_REPORT_PROMPT_URL,
  API_AGENTS_REPORT_REVIEW_PROMPT_URL,
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
import { processDtEvent } from './shared/dtEventHandler.js'
import { pollJobEvents } from './shared/pollJobEvents.js'
import { STREAMING_TOOLS, executeStreamingTool } from './shared/streamingToolExec.js'
import { AssessmentBody, IncidentReviewBody as ReviewBody } from './shared/ReportBodies.jsx'

/* ── Final report card ────────────────────────────────────────── */

function ReportManagerReportView({ entry, index, isExpanded, toggleEntry }) {
  const report = entry.report_manager_report || {}

  const assessment = entry.final_assessment || report.final_assessment || null

  return (
    <div className="card ia-entry ia-result-entry">
      <div className="card-body">
        <div className="ia-result-header" onClick={() => toggleEntry(index)}>
          <i className="fa fa-flag-checkered" aria-hidden="true" />
          <span className="ia-result-label">Report Manager Report</span>
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
            {report.report_summary && (
              <div className="mb-3">
                <strong>Report Summary:</strong>
                <p>{report.report_summary}</p>
              </div>
            )}
            {assessment && (
              <div className="mb-3" style={{ whiteSpace: 'normal' }}>
                <strong>Final Assessment</strong>
                <AssessmentBody report={assessment} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

/* ── Main component ───────────────────────────────────────────── */

/**
 * ReportManagerAgent component — orchestrates ReportAgent + ReportReviewerAgent
 * in an automated generate-review-revise loop to produce high-quality
 * incident assessment reports.
 */
function ReportManagerAgent() {
  const { token, logout } = useAuth()
  const [activeTab, setActiveTab] = useTabWithHash('config')
  const [systemDescription, setSystemDescription] = useState('')
  const [securityAlerts, setSecurityAlerts] = useState('')
  const [operatorFeedback, setOperatorFeedback] = useState('')
  const [systemDescriptionImages, setSystemDescriptionImages] = useState([])
  const [securityAlertsImages, setSecurityAlertsImages] = useState([])
  const [operatorFeedbackImages, setOperatorFeedbackImages] = useState([])
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
  const [reportAgentModel, setReportAgentModel] = useState('')
  const [reviewerAgentModel, setReviewerAgentModel] = useState('')
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
    pollingRef,
    restoredSession
  } = useAgentSession({
    agentType: 'report_manager',
    token,
    logout,
    activeTab,
    onRestore: (session) => {
      const inputs = session.incident_inputs || {}
      setSystemDescription(inputs.systemDescription || '')
      setSecurityAlerts(inputs.securityAlerts || '')
      setOperatorFeedback(inputs.operatorFeedback || '')
      setSystemDescriptionImages(inputs.systemDescriptionImages || [])
      setSecurityAlertsImages(inputs.securityAlertsImages || [])
      setOperatorFeedbackImages(inputs.operatorFeedbackImages || [])
      setSelectedIncidentId(inputs.selectedIncidentId || null)
      const config = session.agent_config || {}
      setManagerModel(config.managerModel || '')
      setReportAgentModel(config.reportAgentModel || '')
      setReviewerAgentModel(config.reviewerAgentModel || '')
      setCompactionModel(config.compactionModel || '')
      setCompactionThreshold(config.compactionThreshold || 80)
      setMaxIterations(config.maxIterations || 1)
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

  const extractFinalReports = (history) => {
    let assessment = null
    let reviewReport = null
    for (let i = history.length - 1; i >= 0; i--) {
      const h = history[i]
      if (!assessment && h.type === 'tool_result' && h.tool_name === 'run_report_agent') {
        const raw = h.result?.assessment || null
        const img = h.result?.attack_path_image
        assessment = raw && img ? { ...raw, attack_path_image: img } : raw
      }
      if (
        !reviewReport &&
        h.type === 'tool_result' &&
        h.tool_name === 'run_report_reviewer_agent'
      ) {
        reviewReport = h.result?.report_review || null
      }
      if (assessment && reviewReport) break
    }
    return { assessment, reviewReport }
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
      if (entry.type === 'tool_streaming') {
        return { ...entry, subEvents: [], output: '' }
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
    const compactionEntries = []
    const dtEntries = []
    setConversationHistory([...history, streamingEntry])
    try {
      let job_id = resumeJobId
      if (!job_id) {
        const res = await fetch(API_AGENTS_REPORT_MANAGER_STEP_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({
            system_description: systemDescription,
            security_alerts: securityAlerts,
            operator_feedback: operatorFeedback,
            conversation_history: stripImagesFromHistory(
              history.filter((e) => e.type !== 'dt_redeploy' && e.type !== 'sandbox_start')
            ),
            images: [
              ...systemDescriptionImages,
              ...securityAlertsImages,
              ...operatorFeedbackImages
            ],
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
          } else if (event.type === 'report_manager_report') {
            finalEntry = {
              role: 'model',
              type: 'report_manager_report',
              report_manager_report: event.report_manager_report,
              thinking_trace: event.thinking_trace || ''
            }
          } else if (event.type === 'dt_progress' || event.type === 'dt_progress_detail' || event.type === 'sandbox_progress') {
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
        if (finalEntry.type === 'report_manager_report') {
          const { assessment, reviewReport } = extractFinalReports(history)
          finalEntry.final_assessment = assessment
          finalEntry.final_review_report = reviewReport
          saveReport(
            {
              ...finalEntry.report_manager_report,
              final_assessment: assessment,
              final_review_report: reviewReport
            },
            updated
          )
        }
      } else if (accumulated) {
        let report
        try {
          report = JSON.parse(accumulated)
        } catch {
          report = {
            executive_summary: accumulated,
            report_summary: ''
          }
        }
        const { assessment, reviewReport } = extractFinalReports(history)
        report.final_assessment = assessment
        report.final_review_report = reviewReport
        const fallbackHistory = [
          ...history,
          ...compactionEntries,
          ...dtEntries,
          {
            role: 'model',
            type: 'report_manager_report',
            report_manager_report: report,
            final_assessment: assessment,
            final_review_report: reviewReport
          }
        ]
        setConversationHistory(fallbackHistory)
        saveReport(report, fallbackHistory)
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
        securityAlerts,
        operatorFeedback,
        systemDescriptionImages,
        securityAlertsImages,
        operatorFeedbackImages,
        selectedIncidentId
      },
      {
        managerModel,
        reportAgentModel,
        reviewerAgentModel,
        compactionModel,
        compactionThreshold,
        maxIterations,
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
      const subModel =
        proposal.tool_name === 'run_report_reviewer_agent' ? reviewerAgentModel : reportAgentModel
      const streamEntry = {
        type: 'tool_streaming',
        tool_name: proposal.tool_name,
        output: '',
        subEvents: [],
        _modelName: subModel || undefined,
        _startTime: Date.now()
      }
      const latestHistory = conversationHistoryRef.current
      const base = [...latestHistory, approvalEntry, streamEntry]
      setConversationHistory(base)
      try {
        let lastAssessment
        if (proposal.tool_name === 'run_report_reviewer_agent') {
          for (let i = latestHistory.length - 1; i >= 0; i--) {
            const h = latestHistory[i]
            if (h.type === 'tool_result' && h.tool_name === 'run_report_agent') {
              lastAssessment = h.result?.assessment || null
              break
            }
          }
        }
        const extraBody = {
          system_description: systemDescription,
          security_alerts: securityAlerts,
          operator_feedback: operatorFeedback,
          images: [...systemDescriptionImages, ...securityAlertsImages, ...operatorFeedbackImages],
          report_agent_model: reportAgentModel || undefined,
          reviewer_agent_model: reviewerAgentModel || undefined,
          conversation_history: latestHistory.filter((e) => e.type !== 'dt_redeploy' && e.type !== 'sandbox_start'),
          last_assessment: lastAssessment,
          compaction_model: compactionModel || undefined,
          compaction_threshold: compactionThreshold / 100,
          session_id: sessionIdRef.current
        }
        const { result } = await executeStreamingTool({
          url: API_AGENTS_REPORT_MANAGER_TOOL_URL,
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
            if (event.type === 'nested_event') {
              const lastToolCall = [...streamEntry.subEvents]
                .reverse()
                .find((e) => e.type === 'tool_call' && !e._completed)
              if (lastToolCall) {
                const inner = event.event || {}
                if (inner.type === 'parallel_start') {
                  lastToolCall._parallelHosts = inner.hosts
                } else {
                  if (!lastToolCall.subEvents) lastToolCall.subEvents = []
                  if (!inner._startTime) inner._startTime = Date.now()
                  lastToolCall.subEvents.push(inner)
                }
              }
              setConversationHistory([...base])
              return
            }
            if (event.type === 'tool_result') {
              const lastCall = [...streamEntry.subEvents]
                .reverse()
                .find((e) => e.type === 'tool_call')
              if (lastCall) lastCall._completed = true
              const entry = {
                type: 'tool_result',
                tool_name: event.tool_name,
                result: event.result,
                _startTime: Date.now()
              }
              const callSubs = lastCall?.subEvents || []
              if (callSubs.length > 0) {
                entry.subEvents = callSubs
                entry._parallelHosts = lastCall?._parallelHosts
              }
              streamEntry.subEvents.push(entry)
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
        if (proposal.tool_name === 'run_report_reviewer_agent') {
          for (let i = base.length - 1; i >= 0; i--) {
            const h = base[i]
            if (h.type === 'tool_result' && h.tool_name === 'run_report_agent') {
              resultEntry._attackPathImage = h.result?.attack_path_image
              break
            }
          }
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
      const res = await fetch(API_AGENTS_REPORT_MANAGER_TOOL_URL, {
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
    clearSession()
  }

  const resumeToolJob = async (jobId, toolName, startTime) => {
    const subModel =
      toolName === 'run_report_reviewer_agent' ? reviewerAgentModel : reportAgentModel
    const streamEntry = {
      type: 'tool_streaming',
      tool_name: toolName,
      output: '',
      subEvents: [],
      _modelName: subModel || undefined,
      _startTime: startTime || Date.now()
    }
    setConversationHistory((prev) => [...prev, streamEntry])
    setExecutingTool(toolName)
    const controller = new AbortController()
    abortControllerRef.current = controller
    try {
      const latestHistory = conversationHistoryRef.current
      let lastAssessment
      if (toolName === 'run_report_reviewer_agent') {
        for (let i = latestHistory.length - 1; i >= 0; i--) {
          const h = latestHistory[i]
          if (h.type === 'tool_result' && h.tool_name === 'run_report_agent') {
            lastAssessment = h.result?.assessment || null
            break
          }
        }
      }
      const extraBody = {
        system_description: systemDescription,
        security_alerts: securityAlerts,
        operator_feedback: operatorFeedback,
        images: [...systemDescriptionImages, ...securityAlertsImages, ...operatorFeedbackImages],
        report_agent_model: reportAgentModel || undefined,
        reviewer_agent_model: reviewerAgentModel || undefined,
        conversation_history: latestHistory.filter((e) => e.type !== 'dt_redeploy' && e.type !== 'sandbox_start'),
        last_assessment: lastAssessment,
        compaction_model: compactionModel || undefined,
        compaction_threshold: compactionThreshold / 100,
        session_id: sessionIdRef.current
      }
      const { result } = await executeStreamingTool({
        url: API_AGENTS_REPORT_MANAGER_TOOL_URL,
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
    const res = await fetch(API_AGENTS_REPORT_MANAGER_PROMPT_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({
        system_description: systemDescription,
        security_alerts: securityAlerts,
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
      images: [...systemDescriptionImages, ...securityAlertsImages, ...operatorFeedbackImages]
    }
  }

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_AGENTS_REPORTS_URL}?agent_type=report_manager`, {
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
          agent_type: 'report_manager',
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
      await fetch(`${API_AGENTS_REPORTS_URL}?agent_type=report_manager`, {
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
    <ReportManagerReportView
      key={index}
      entry={entry}
      index={index}
      isExpanded={isExpanded}
      toggleEntry={toggleEntry}
    />
  )

  const renderToolResult = (entry) => {
    if (entry.tool_name === 'run_report_agent' && entry.result?.assessment) {
      const img = entry.result?.attack_path_image
      const report = img
        ? { ...entry.result.assessment, attack_path_image: img }
        : entry.result.assessment
      return <AssessmentBody report={report} />
    }
    if (entry.tool_name === 'run_report_reviewer_agent' && entry.result?.report_review) {
      return (
        <>
          {entry._attackPathImage && (
            <div className="ia-assessment-section" style={{ marginTop: '10px' }}>
              <div className="ia-assessment-label">Attack Path Image (attached to reviewer)</div>
              <img
                src={entry._attackPathImage}
                alt="Attack path attached to reviewer"
                style={{
                  maxWidth: '100%',
                  border: '1px solid #dee2e6',
                  borderRadius: '4px'
                }}
              />
            </div>
          )}
          <ReviewBody report={entry.result.report_review} />
        </>
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
            Report generation process
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
              This agent coordinates the ReportAgent and ReportReviewerAgent in an automated
              generate-review-revise loop to produce high-quality incident assessment reports.
            </p>
          </div>

          <div className="ia-section">
            <label htmlFor="rm-system-desc">System description</label>
            <p className="ia-hint">
              Describe the target system, its architecture, hosts, and services.
            </p>
            <textarea
              id="rm-system-desc"
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
            <label htmlFor="rm-security-alerts">Security alerts</label>
            <p className="ia-hint">
              Paste the security alerts/logs that triggered incident response.
            </p>
            <textarea
              id="rm-security-alerts"
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
            <label htmlFor="rm-operator-feedback">Operator feedback (optional)</label>
            <p className="ia-hint">
              Additional guidance or constraints for the incident assessment.
            </p>
            <textarea
              id="rm-operator-feedback"
              className="form-control ia-textarea"
              rows="4"
              value={operatorFeedback}
              onChange={(e) => setOperatorFeedback(e.target.value)}
              onPaste={handlePaste(setOperatorFeedbackImages)}
              disabled={isAgentBusy}
              placeholder="e.g., Focus on lateral movement indicators. The web server is the most critical asset."
            />
            <ImageThumbnails
              images={operatorFeedbackImages}
              setImages={setOperatorFeedbackImages}
              disabled={isAgentBusy}
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
              id="rm-autopilot"
              checked={autopilot}
              onChange={(e) => setAutopilot(e.target.checked)}
            />
            <label className="form-check-label" htmlFor="rm-autopilot">
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
              label: 'Report Manager',
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
              promptUrl: API_AGENTS_REPORT_MANAGER_PROMPT_URL
            },
            {
              label: 'Report Agent',
              model: reportAgentModel,
              setModel: setReportAgentModel,
              promptUrl: API_AGENTS_REPORT_PROMPT_URL
            },
            {
              label: 'Report Reviewer',
              model: reviewerAgentModel,
              setModel: setReviewerAgentModel,
              promptUrl: API_AGENTS_REPORT_REVIEW_PROMPT_URL
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
          renderReport={(report) => (
            <ReportManagerReportView
              entry={{ type: 'report_manager_report', report_manager_report: report }}
              index="history"
              isExpanded={true}
              toggleEntry={() => {}}
            />
          )}
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

export default ReportManagerAgent
