import { useState, useEffect, useRef } from 'react'
import useTabWithHash from '../../hooks/useTabWithHash.js'
import { useAuth } from '../../contexts/AuthContext.jsx'
import {
  API_EXAMPLES_URL,
  API_AGENTS_PLANNER_STEP_URL,
  API_AGENTS_PLANNER_TOOL_URL,
  API_AGENTS_PLANNER_PROMPT_URL,
  API_LLM_URL,
  API_AGENTS_REPORTS_URL,
  API_DT_PYTHON_STOP_URL
} from '../Common/constants'
import PlannerAgentConfigTab from './PlannerAgentConfigTab.jsx'
import AgentConfigTable from './shared/AgentConfigTable.jsx'
import PlannerAgentReport from './PlannerAgentReport.jsx'
import RewardChart from './RewardChart.jsx'
import RlTrainResult from './RlTrainResult.jsx'
import AgentPlanningTab from './shared/AgentPlanningTab.jsx'
import AgentHistoryTab from './shared/AgentHistoryTab.jsx'
import JobsTab from './shared/JobsTab.jsx'
import { useAgentSession } from './shared/useAgentSession.js'
import { cleanConversationHistory, stripForBackend } from './shared/conversationUtils.js'
import { pollJobEvents } from './shared/pollJobEvents.js'
import { processDtEvent } from './shared/dtEventHandler.js'

/**
 * PlannerAgent component — drives the Planner agent loop with
 * human-in-the-loop tool approval and live RL training visualization.
 */
function PlannerAgent() {
  const { token, logout } = useAuth()
  const [activeTab, setActiveTab] = useTabWithHash('config')
  const [systemDescription, setSystemDescription] = useState('')
  const [incidentReport, setIncidentReport] = useState('')
  const [specification, setSpecification] = useState('')
  const [specificationCommands, setSpecificationCommands] = useState([])
  const [operatorFeedback, setOperatorFeedback] = useState('')
  const [codeReport, setCodeReport] = useState('')
  const [timeLimitMinutes, setTimeLimitMinutes] = useState(10)
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
  const [selectedModel, setSelectedModel] = useState('')
  const [compactionModel, setCompactionModel] = useState('')
  const [compactionThreshold, setCompactionThreshold] = useState(80)
  const [dtEnabled, setDtEnabled] = useState(true)
  const [reportHistory, setReportHistory] = useState([])
  const [trainingData, setTrainingData] = useState([])
  const [trainingMeta, setTrainingMeta] = useState({
    algorithm: '',
    hyperparameters: '',
    started: false
  })
  const [trainingStartTime, setTrainingStartTime] = useState(null)
  const [evalProgress, setEvalProgress] = useState(null)
  const [policyData, setPolicyData] = useState(null)
  const [selectedIncidentId, setSelectedIncidentId] = useState(null)
  const logEndRef = useRef(null)
  const streamingTraceRef = useRef(null)
  const isNearBottomRef = useRef(true)
  const trainingRunsRef = useRef({})
  const runIdCounterRef = useRef(0)
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
    agentType: 'planner',
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
      setCodeReport(inputs.codeReport || '')
      setTimeLimitMinutes(inputs.timeLimitMinutes || 10)
      setSystemDescriptionImages(inputs.systemDescriptionImages || [])
      setSelectedIncidentId(inputs.selectedIncidentId || null)
      const config = session.agent_config || {}
      setSelectedModel(config.selectedModel || '')
      setCompactionModel(config.compactionModel || '')
      setCompactionThreshold(config.compactionThreshold || 80)
      setAutopilot(config.autopilot ?? true)
      setDtEnabled(config.dtEnabled ?? true)
      setContextUsage(session.context_usage || null)
      setPendingProposal(session.pending_proposal || null)
      if (!window.location.hash) setActiveTab('planning')
    },
    onResumeJob: (jobId, session, toolName) => {
      setContextUsage(session.context_usage || null)
      setPendingProposal(null)
      if (!window.location.hash) setActiveTab('planning')
      setRunning(true)
      // Detect rl_train from conversation history: if the last
      // tool_proposal is rl_train and there's no subsequent
      // tool_approval, the tool job is still running.
      const history = conversationHistoryRef.current
      let resumeTool = toolName || null
      if (!resumeTool) {
        const lastProposal = [...history].reverse().find((e) => e.type === 'tool_proposal')
        const lastApproval = [...history].reverse().find((e) => e.type === 'tool_approval')
        const proposalIdx = lastProposal ? history.indexOf(lastProposal) : -1
        const approvalIdx = lastApproval ? history.indexOf(lastApproval) : -1
        if (lastProposal && proposalIdx > approvalIdx) {
          resumeTool = lastProposal.tool_name
        }
      }
      console.log('[PlannerAgent] onResumeJob: toolName=%s, resumeTool=%s', toolName, resumeTool)
      if (resumeTool === 'rl_train') {
        resumeRlTrain(jobId)
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
      console.log(
        '[PlannerAgent] Autopilot auto-approving: tool=%s',
        pendingProposal.tool_name
      )
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
    setTrainingStartTime(null)
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
    const streamingEntry = { role: 'model', type: 'streaming', text: '' }
    const compactionEntries = []
    const dtEntries = []
    setConversationHistory([...history, streamingEntry])
    const controller = new AbortController()
    abortControllerRef.current = controller
    try {
      let job_id = resumeJobId
      if (!job_id) {
        const res = await fetch(API_AGENTS_PLANNER_STEP_URL, {
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
            code_report: codeReport,
            conversation_history: stripForBackend(history)
              .filter((e) => e.type !== 'dt_redeploy' && e.type !== 'sandbox_start')
              .map((e) =>
                e.type === 'tool_result' && e.tool_name === 'rl_train' && e.result?.progress_data
                  ? { ...e, result: { ...e.result, progress_data: undefined } }
                  : e
              ),
            images: [...systemDescriptionImages],
            model_name: selectedModel || undefined,
            last_prompt_tokens: contextUsage?.prompt_tokens || 0,
            compaction_model: compactionModel || undefined,
            compaction_threshold: compactionThreshold / 100,
            time_limit_minutes: timeLimitMinutes,
            session_id: sessionIdRef.current,
            dt_enabled: dtEnabled
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
          } else if (event.type === 'dt_progress' || event.type === 'dt_progress_detail' || event.type === 'sandbox_progress') {
            processDtEvent(event, dtEntries, setDtStatus)
            setConversationHistory([...history, ...compactionEntries, ...dtEntries])
          } else if (event.type === 'tool_proposal') {
            console.log('[PlannerAgent] callStep received tool_proposal: tool=%s', event.tool_name)
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
            console.log('[PlannerAgent] callStep received planner_report')
            finalEntry = {
              role: 'model',
              type: 'planner_report',
              planner_report: event.planner_report,
              thinking_trace: event.thinking_trace || ''
            }
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
        if (finalEntry.type === 'planner_report') {
          saveReport(finalEntry.planner_report, updated)
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
        const fallbackHistory = [
          ...history,
          ...compactionEntries,
          ...dtEntries,
          { role: 'model', type: 'planner_report', planner_report: report }
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

  const resumeRlTrain = async (jobId) => {
    const history = conversationHistoryRef.current
    const lastProposal = [...history]
      .reverse()
      .find((e) => e.type === 'tool_proposal' && e.tool_name === 'rl_train')
    const toolArgs = lastProposal?.tool_args || {}

    setExecutingTool('rl_train')
    setTrainingData([])
    setEvalProgress(null)
    setTrainingStartTime(Date.now())
    setTrainingMeta({
      algorithm: toolArgs.algorithm || '',
      hyperparameters: toolArgs.hyperparameters || '',
      started: true
    })

    const controller = new AbortController()
    abortControllerRef.current = controller

    const safetyMs = (timeLimitMinutes + 3) * 60 * 1000
    const safetyTimer = setTimeout(() => {
      console.warn('[PlannerAgent] rl_train resume safety timeout fired after %dms', safetyMs)
      controller.abort()
    }, safetyMs)

    try {
      const progressEvents = []
      let resultEvent = null
      let doneEvent = null
      let pollAborted = false

      try {
        await pollJobEvents({
          jobId,
          token,
          signal: controller.signal,
          onEvent: (event) => {
            if (event.type === 'started') {
              setTrainingMeta((prev) => ({ ...prev, started: true }))
            } else if (event.type === 'progress') {
              progressEvents.push(event)
              setTrainingData((prev) => [...prev, event])
            } else if (event.type === 'eval_progress') {
              setEvalProgress(event)
            } else if (event.type === 'result') {
              console.log('[PlannerAgent] rl_train resume: result event received')
              resultEvent = event
            } else if (event.type === 'policy_data') {
              console.log('[PlannerAgent] rl_train resume: policy_data event received')
              if (event.policy_data) setPolicyData(event.policy_data)
            } else if (event.type === 'done' || event.type === 'timeout') {
              console.log(
                '[PlannerAgent] rl_train resume: %s event, exit_code=%s',
                event.type,
                event.exit_code
              )
              doneEvent = event
              if (event.policy_data) setPolicyData(event.policy_data)
            } else if (event.type === 'error') {
              console.log('[PlannerAgent] rl_train resume: error: %s', event.message)
              setAlert({ type: 'danger', message: event.message || 'Training error' })
            }
          }
        })
      } catch (pollErr) {
        if (pollErr.name === 'AbortError') {
          pollAborted = true
          console.warn(
            '[PlannerAgent] rl_train resume poll aborted. episodes=%d, hasResult=%s',
            progressEvents.length,
            !!resultEvent
          )
        } else {
          throw pollErr
        }
      }
      clearTimeout(safetyTimer)
      if (pollAborted && !abortControllerRef.current) return

      console.log(
        '[PlannerAgent] rl_train resume poll %s. episodes=%d, hasResult=%s, hasDone=%s',
        pollAborted ? 'ABORTED' : 'returned',
        progressEvents.length,
        !!resultEvent,
        !!doneEvent
      )
      setTrainingStartTime(null)
      const runId = ++runIdCounterRef.current
      trainingRunsRef.current[runId] = {
        data: [...progressEvents],
        meta: { algorithm: toolArgs.algorithm || '', hyperparameters: toolArgs.hyperparameters || '' }
      }
      const toolResult = {
        progress_episodes: progressEvents.length,
        progress_data: [...progressEvents],
        training_meta: {
          algorithm: toolArgs.algorithm || '',
          hyperparameters: toolArgs.hyperparameters || ''
        },
        result: resultEvent,
        done: doneEvent
      }
      const approvalEntry = {
        role: 'user',
        type: 'tool_approval',
        tool_name: 'rl_train',
        tool_args: toolArgs,
        approved: true
      }
      const resultEntry = {
        role: 'tool',
        type: 'tool_result',
        tool_name: 'rl_train',
        result: toolResult,
        _runId: runId
      }
      let updated
      setConversationHistory((prev) => {
        const stripped = prev.filter((e) => e.type !== 'streaming' && e.type !== 'tool_streaming')
        updated = [...stripped, approvalEntry, resultEntry]
        console.log(
          '[PlannerAgent] rl_train resume result added (runId=%d). Calling callStep. history=%d',
          runId,
          updated.length
        )
        return updated
      })
      setExecutingTool(null)
      await callStep(updated)
    } catch (err) {
      clearTimeout(safetyTimer)
      if (err.name === 'AbortError') return
      setAlert({ type: 'danger', message: `Tool execution error: ${err.message}` })
      setTrainingStartTime(null)
      setExecutingTool(null)
      setRunning(false)
    }
  }

  const handleRun = async () => {
    setPendingProposal(null)
    setConversationHistory([])
    setExpandedEntries({})
    setContextUsage(null)
    setTrainingData([])
    setActiveTab('planning')
    setRunning(true)
    await createSession(
      {
        systemDescription,
        incidentReport,
        specification,
        specificationCommands,
        operatorFeedback,
        codeReport,
        timeLimitMinutes,
        systemDescriptionImages,
        selectedIncidentId
      },
      {
        selectedModel,
        compactionModel,
        compactionThreshold,
        autopilot,
        dtEnabled
      }
    )
    callStep([])
  }

  const handleApprove = async () => {
    if (!pendingProposal) return
    const proposal = pendingProposal
    console.log('[PlannerAgent] handleApprove: tool=%s', proposal.tool_name)
    const approvalEntry = {
      role: 'user',
      type: 'tool_approval',
      tool_name: proposal.tool_name,
      tool_args: proposal.tool_args,
      approved: true
    }
    setPendingProposal(null)
    setExecutingTool(proposal.tool_name)

    if (proposal.tool_name === 'rl_train') {
      setTrainingData([])
      setEvalProgress(null)
      setTrainingStartTime(Date.now())
      setTrainingMeta({
        algorithm: proposal.tool_args.algorithm || '',
        hyperparameters: proposal.tool_args.hyperparameters || '',
        started: false
      })
      const controller = new AbortController()
      abortControllerRef.current = controller

      // Safety timeout: abort the poll if it hasn't completed
      // within timeLimitMinutes + 3 min grace.
      const safetyMs = (timeLimitMinutes + 3) * 60 * 1000
      const safetyTimer = setTimeout(() => {
        console.warn('[PlannerAgent] rl_train safety timeout fired after %dms', safetyMs)
        controller.abort()
      }, safetyMs)

      try {
        const res = await fetch(API_AGENTS_PLANNER_TOOL_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({
            tool_name: proposal.tool_name,
            tool_args: proposal.tool_args,
            session_id: sessionIdRef.current
          })
        })
        if (res.status === 401) {
          clearTimeout(safetyTimer)
          logout()
          return
        }
        if (!res.ok) {
          clearTimeout(safetyTimer)
          const errData = await res.json().catch(() => ({}))
          setAlert({
            type: 'danger',
            message: errData.error || `Tool execution failed (HTTP ${res.status})`
          })
          setExecutingTool(null)
          return
        }

        const { job_id } = await res.json()
        console.log('[PlannerAgent] rl_train job started: job_id=%s', job_id)
        const progressEvents = []
        let resultEvent = null
        let doneEvent = null
        let pollAborted = false

        try {
          await pollJobEvents({
            jobId: job_id,
            token,
            signal: controller.signal,
            onEvent: (event) => {
              if (event.type === 'started') {
                console.log('[PlannerAgent] rl_train: started event received')
                setTrainingMeta((prev) => ({ ...prev, started: true }))
              } else if (event.type === 'progress') {
                progressEvents.push(event)
                setTrainingData((prev) => [...prev, event])
              } else if (event.type === 'eval_progress') {
                setEvalProgress(event)
              } else if (event.type === 'result') {
                console.log('[PlannerAgent] rl_train: result event received')
                resultEvent = event
              } else if (event.type === 'policy_data') {
                console.log('[PlannerAgent] rl_train: policy_data event received')
                if (event.policy_data) setPolicyData(event.policy_data)
              } else if (event.type === 'done' || event.type === 'timeout') {
                console.log(
                  '[PlannerAgent] rl_train: %s event received, exit_code=%s',
                  event.type, event.exit_code
                )
                doneEvent = event
                if (event.policy_data) setPolicyData(event.policy_data)
              } else if (event.type === 'error') {
                console.log('[PlannerAgent] rl_train: error event: %s', event.message)
                setAlert({ type: 'danger', message: event.message || 'Training error' })
              }
            }
          })
        } catch (pollErr) {
          if (pollErr.name === 'AbortError') {
            // Safety timeout or user cancel — use whatever data we collected
            pollAborted = true
            console.warn(
              '[PlannerAgent] rl_train poll aborted. episodes=%d, hasResult=%s',
              progressEvents.length, !!resultEvent
            )
          } else {
            throw pollErr
          }
        }
        clearTimeout(safetyTimer)
        if (pollAborted && !abortControllerRef.current) return

        console.log(
          '[PlannerAgent] rl_train pollJobEvents %s. episodes=%d, hasResult=%s, hasDone=%s',
          pollAborted ? 'ABORTED' : 'returned',
          progressEvents.length, !!resultEvent, !!doneEvent
        )
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
          progress_data: [...progressEvents],
          training_meta: {
            algorithm: proposal.tool_args.algorithm || '',
            hyperparameters: proposal.tool_args.hyperparameters || ''
          },
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
        let updated
        setConversationHistory((prev) => {
          const stripped = prev.filter((e) => e.type !== 'streaming' && e.type !== 'tool_streaming')
          updated = [...stripped, approvalEntry, resultEntry]
          console.log(
            '[PlannerAgent] rl_train result added to history (runId=%d). Calling callStep. history length=%d',
            runId, updated.length
          )
          return updated
        })
        setExecutingTool(null)
        await callStep(updated)
      } catch (err) {
        clearTimeout(safetyTimer)
        if (err.name === 'AbortError') return
        setAlert({ type: 'danger', message: `Tool execution error: ${err.message}` })
        setTrainingStartTime(null)
        setExecutingTool(null)
      }
    } else {
      const controller = new AbortController()
      abortControllerRef.current = controller
      try {
        const res = await fetch(API_AGENTS_PLANNER_TOOL_URL, {
          method: 'POST',
          signal: controller.signal,
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({
            tool_name: proposal.tool_name,
            tool_args: proposal.tool_args,
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
      const headers = { Authorization: `Bearer ${token}` }
      const exampleRes = await fetch(`${API_EXAMPLES_URL}/${incidentId}`, { headers })
      if (exampleRes.status === 401) {
        logout()
        return
      }
      const exampleData = await exampleRes.json()
      setSystemDescription(exampleData.system_description || '')
      setIncidentReport(exampleData.incident_report || '')
      setSpecification(exampleData.specification || '')
      setSpecificationCommands(exampleData.specification_commands || [])
      setOperatorFeedback('')
      setSystemDescriptionImages(exampleData.system_description_images || [])

      const [reportsRes, infoRes] = await Promise.all([
        fetch(`${API_AGENTS_REPORTS_URL}?agent_type=code&incident_id=${incidentId}`, { headers }),
        fetch(`${API_AGENTS_REPORTS_URL}?agent_type=report&incident_id=${incidentId}`, { headers })
      ])

      if (reportsRes.ok) {
        const reports = await reportsRes.json()
        if (reports.length > 0) {
          setCodeReport(JSON.stringify(reports[0].report || {}, null, 2))
        }
      }

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
    setCodeReport('')
    setTimeLimitMinutes(5)
    setSystemDescriptionImages([])
    setConversationHistory([])
    setPendingProposal(null)
    setExpandedEntries({})
    setTrainingData([])
    setTrainingMeta({ algorithm: '', hyperparameters: '', started: false })
    setTrainingStartTime(null)
    setEvalProgress(null)
    setPolicyData(null)
    trainingRunsRef.current = {}
    runIdCounterRef.current = 0
    setSelectedIncidentId(null)
    clearSession()
  }

  const getPromptText = async () => {
    const res = await fetch(API_AGENTS_PLANNER_PROMPT_URL, {
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
        code_report: codeReport,
        time_limit_minutes: timeLimitMinutes
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
      const res = await fetch(`${API_AGENTS_REPORTS_URL}?agent_type=planner`, {
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
          agent_type: 'planner',
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
      await fetch(`${API_AGENTS_REPORTS_URL}?agent_type=planner`, {
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
    <PlannerAgentReport
      key={index}
      entry={entry}
      index={index}
      isExpanded={isExpanded}
      toggleEntry={toggleEntry}
      policyData={policyData}
    />
  )

  const renderToolResult = (entry) => {
    if (entry.tool_name === 'rl_train') {
      const run = entry._runId ? trainingRunsRef.current[entry._runId] : null
      return (
        <RlTrainResult
          trainingData={run ? run.data : entry.result?.progress_data || trainingData}
          trainingMeta={run ? run.meta : entry.result?.training_meta || trainingMeta}
          result={entry.result}
          policyData={policyData || entry.result?.done?.policy_data}
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
          timeLimitMinutes={timeLimitMinutes}
          evalProgress={evalProgress}
          trainingStarted={trainingMeta.started}
        />
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
            Incident description
          </button>
        </li>
        <li className="nav-item">
          <button
            type="button"
            className={`nav-link${activeTab === 'configuration' ? ' active' : ''}`}
            onClick={() => setActiveTab('configuration')}
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
        <PlannerAgentConfigTab
          systemDescription={systemDescription}
          setSystemDescription={setSystemDescription}
          incidentReport={incidentReport}
          setIncidentReport={setIncidentReport}
          specificationCommands={specificationCommands}
          setSpecificationCommands={setSpecificationCommands}
          operatorFeedback={operatorFeedback}
          setOperatorFeedback={setOperatorFeedback}
          codeReport={codeReport}
          setCodeReport={setCodeReport}
          systemDescriptionImages={systemDescriptionImages}
          setSystemDescriptionImages={setSystemDescriptionImages}
          handlePaste={handlePaste}
          isAgentBusy={isAgentBusy}
          handleRun={handleRun}
          loadExample={loadExample}
          handleClear={handleClear}
          autopilot={autopilot}
          setAutopilot={setAutopilot}
        />
      )}

      {activeTab === 'configuration' && (
        <div style={{ marginTop: '16px' }}>
          <div className="form-check">
            <input
              className="form-check-input"
              type="checkbox"
              id="pl-dt-enabled"
              checked={dtEnabled}
              onChange={(e) => setDtEnabled(e.target.checked)}
              disabled={isAgentBusy}
            />
            <label className="form-check-label" htmlFor="pl-dt-enabled">
              Digital Twin enabled{' '}
              <span className="ia-hint">
                (when disabled, agents cannot interact with the digital twin)
              </span>
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
              label: 'Planner Agent',
              model: selectedModel,
              setModel: setSelectedModel,
              promptUrl: API_AGENTS_PLANNER_PROMPT_URL,
              iteration: {
                value: timeLimitMinutes,
                set: setTimeLimitMinutes,
                min: 1,
                max: 60,
                suffix: 'min'
              },
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
          renderExecutingTool={renderExecutingTool}
          renderToolResult={renderToolResult}
          onStop={handleStop}
          onViewPrompt={getPromptText}
          modelName={selectedModel}
          dtStatus={dtStatus}
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
            <PlannerAgentReport
              entry={{ type: 'planner_report', planner_report: report }}
              index="history"
              isExpanded={true}
              toggleEntry={() => {}}
              policyData={policyData}
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

export default PlannerAgent
