import { useState, useEffect, useRef } from 'react'
import {
  API_AGENTS_SESSIONS_URL,
  API_AGENTS_JOBS_URL,
  apiSessionsActiveUrl,
  apiJobStatusUrl,
  apiJobCancelUrl
} from '../../Common/constants'
/**
 * Shared hook for agent session persistence, multi-tab coordination,
 * and background jobs management.
 *
 * @param {object} opts
 * @param {string} opts.agentType - agent type tag (e.g. 'report')
 * @param {string} opts.token - auth token
 * @param {function} opts.logout - auth logout callback
 * @param {string} opts.activeTab - currently active UI tab
 * @param {function} [opts.onRestore] - called with session data on restore
 * @param {function} [opts.onResumeJob] - called when a running job is found
 */
export function useAgentSession({
  agentType,
  token,
  logout,
  activeTab,
  incidentInputs,
  agentConfig,
  onRestore,
  onResumeJob
}) {
  const [conversationHistory, rawSetConversationHistory] = useState([])
  const conversationHistoryRef = useRef([])
  const setConversationHistory = (value) => {
    const next = typeof value === 'function' ? value(conversationHistoryRef.current) : value
    conversationHistoryRef.current = next
    rawSetConversationHistory(next)
  }

  const sessionIdRef = useRef(null)
  const isSourceTabRef = useRef(false)
  const [restoredSession, setRestoredSession] = useState(false)
  const [jobs, setJobs] = useState(null)
  const lastSaveRef = useRef(0)
  const savedCountRef = useRef(0)
  const saveAbortRef = useRef(null)
  const pollingRef = useRef(null)
  const pendingProposalRef = useRef(null)
  const contextUsageRef = useRef(null)
  const uiStateRef = useRef(null)
  const incidentInputsRef = useRef(incidentInputs)
  incidentInputsRef.current = incidentInputs
  const agentConfigRef = useRef(agentConfig)
  agentConfigRef.current = agentConfig

  const setPendingProposalRef = (v) => {
    pendingProposalRef.current = v
  }
  const setContextUsageRef = (v) => {
    contextUsageRef.current = v
  }
  const setUiStateRef = (v) => {
    uiStateRef.current = v
  }

  const saveBackoffRef = useRef(0)

  // Auto-save effect
  useEffect(() => {
    if (!isSourceTabRef.current) return
    const sid = sessionIdRef.current
    if (!sid) return

    const SAVE_INTERVAL = 5000
    const now = Date.now()

    // Back off after save errors to avoid hammering the server
    if (saveBackoffRef.current > now) {
      const timer = setTimeout(() => {}, saveBackoffRef.current - now)
      return () => clearTimeout(timer)
    }

    const save = () => {
      lastSaveRef.current = Date.now()
      // Cancel any in-flight save so stale PUTs don't pile up
      // and exhaust the browser's per-host connection limit.
      if (saveAbortRef.current) saveAbortRef.current.abort()
      const ac = new AbortController()
      saveAbortRef.current = ac
      const history = conversationHistoryRef.current
      const saveFrom = savedCountRef.current
      const newEntries = history.slice(saveFrom)
      const payload = {
        pending_proposal: pendingProposalRef.current,
        context_usage: contextUsageRef.current,
        ui_state: uiStateRef.current
      }
      if (saveFrom === 0) {
        payload.conversation_history = history
      } else if (newEntries.length > 0) {
        payload.append_history = newEntries
      }
      const snapshotLen = history.length
      fetch(`${API_AGENTS_SESSIONS_URL}/${sid}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(payload),
        signal: ac.signal
      })
        .then((res) => {
          if (res.ok) savedCountRef.current = snapshotLen
          else saveBackoffRef.current = Date.now() + 15000
        })
        .catch((err) => {
          if (err.name !== 'AbortError') {
            console.warn('Session auto-save failed:', err.message)
            saveBackoffRef.current = Date.now() + 15000
          }
        })
    }

    const elapsed = now - lastSaveRef.current
    if (elapsed >= SAVE_INTERVAL) {
      save()
      return
    }
    const timer = setTimeout(save, SAVE_INTERVAL - elapsed)
    return () => clearTimeout(timer)
  }, [conversationHistory])

  // Session restoration effect
  useEffect(() => {
    if (restoredSession) return
    fetch(apiSessionsActiveUrl(agentType), {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then((res) => {
        if (res.status === 401) {
          logout()
          return null
        }
        return res.ok ? res.json() : null
      })
      .then(async (data) => {
        if (!data || !data.session) {
          setRestoredSession(true)
          return
        }
        const session = data.session
        sessionIdRef.current = session.id

        const uiState = session.ui_state || {}
        let jobRunning = false
        let jobNotFound = false
        let jobEventCount = -1
        try {
          const jobRes = await fetch(apiJobStatusUrl(String(session.id)), {
            headers: { Authorization: `Bearer ${token}` }
          })
          if (jobRes.ok) {
            const jobData = await jobRes.json()
            jobRunning = jobData.running && !jobData.done
            jobEventCount = jobData.event_count ?? -1
          } else {
            jobNotFound = true
          }
        } catch {
          jobNotFound = true
        }

        // Stale session: job gone (e.g. backend restart) or finished with no
        // events.  Cancel the DB record and skip restoration so old data never
        // flashes in the UI.
        if (!jobRunning && (jobNotFound || jobEventCount === 0)) {
          fetch(`${API_AGENTS_SESSIONS_URL}/${session.id}`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`
            },
            body: JSON.stringify({
              status: 'cancelled',
              conversation_history: [],
              ui_state: { running: false, executingTool: null }
            })
          }).catch(() => {})
          sessionIdRef.current = null
          setRestoredSession(true)
          return
        }

        if (onRestore) onRestore(session)

        let history = session.conversation_history || []
        if (jobRunning) {
          const activeStream = history.find((e) => e.type === 'tool_streaming' && !e.stopped)
          const originalStartTime = activeStream?._startTime || null
          history = history.filter(
            (e) => e.type !== 'streaming' && !(e.type === 'tool_streaming' && !e.stopped)
          )
          setConversationHistory(history)
          savedCountRef.current = history.length
          setRestoredSession(true)
          isSourceTabRef.current = true
          if (pollingRef.current) {
            clearInterval(pollingRef.current)
            pollingRef.current = null
          }
          let toolName = uiState.executingTool
          if (!toolName && session.pending_proposal?.tool_name) {
            toolName = session.pending_proposal.tool_name
          }
          if (onResumeJob) {
            onResumeJob(String(session.id), session, toolName, originalStartTime)
          }
        } else {
          let proposal = session.pending_proposal || null
          if (history.length > 0) {
            const last = history[history.length - 1]
            if (last.type === 'tool_approval' && last.approved) {
              history = history.slice(0, -1)
              const lastProposal = [...history].reverse().find((e) => e.type === 'tool_proposal')
              if (lastProposal) proposal = lastProposal
            }
          }
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
          setConversationHistory(history)
          pendingProposalRef.current = proposal
          setRestoredSession(true)
        }
      })
      .catch(() => {
        setRestoredSession(true)
      })
  }, [token, restoredSession, logout])

  // Stale job detection effect
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
                ui_state: { running: false, executingTool: null }
              })
            }).catch(() => {})
            sessionIdRef.current = null
            setConversationHistory([])
            pendingProposalRef.current = null
            contextUsageRef.current = null
            return
          }
          return fetch(apiSessionsActiveUrl(agentType), {
            headers: { Authorization: `Bearer ${token}` }
          })
            .then((res) => (res.ok ? res.json() : null))
            .then((freshData) => {
              if (!freshData?.session) return
              const s = freshData.session
              const history = (s.conversation_history || [])
                .map((e) => {
                  if (e.type === 'streaming') {
                    return e.text ? { ...e, type: 'reasoning', role: 'model' } : null
                  }
                  if (e.type === 'tool_streaming' && !e.stopped) return { ...e, stopped: true }
                  return e
                })
                .filter(Boolean)
              setConversationHistory(history)
              pendingProposalRef.current = s.pending_proposal || null
              contextUsageRef.current = s.context_usage || null
            })
        }
      })
      .catch(() => {})
  }, [restoredSession])

  // Multi-tab polling effect
  useEffect(() => {
    if (isSourceTabRef.current) return
    const sid = sessionIdRef.current
    if (!sid) return
    const interval = setInterval(() => {
      Promise.all([
        fetch(apiSessionsActiveUrl(agentType), {
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
            pendingProposalRef.current = null
            contextUsageRef.current = null
            if (s.status !== 'active') clearInterval(interval)
            return
          }
          const rawHistory = (s.conversation_history || [])
            .map((e) => {
              if (e.type === 'streaming') {
                return e.text ? { ...e, type: 'reasoning', role: 'model' } : null
              }
              if (e.type === 'tool_streaming' && !e.stopped) return { ...e, stopped: true }
              return e
            })
            .filter(Boolean)
          setConversationHistory(rawHistory)
          pendingProposalRef.current = s.pending_proposal || null
          contextUsageRef.current = s.context_usage || null
        })
        .catch(() => {})
    }, 1000)
    pollingRef.current = interval
    return () => clearInterval(interval)
  }, [restoredSession, token])

  // Jobs fetch
  const fetchJobs = async () => {
    try {
      const res = await fetch(API_AGENTS_JOBS_URL, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) setJobs(await res.json())
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

  // Session CRUD
  const createSession = async (firstArg, secondArg) => {
    // Support both calling conventions:
    //   createSession(incidentId)           — uses incidentInputs/agentConfig from hook options
    //   createSession(inputsObj, configObj)  — legacy direct passing
    let inputs, config, incidentId
    if (typeof firstArg === 'object' && firstArg !== null) {
      inputs = firstArg
      config = secondArg
    } else {
      incidentId = firstArg
      inputs = incidentInputsRef.current
      config = agentConfigRef.current
    }
    try {
      const res = await fetch(API_AGENTS_SESSIONS_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          incident_inputs: inputs,
          agent_config: config,
          ...(incidentId != null && { incident_id: incidentId }),
          agent_type: agentType
        })
      })
      if (res.status === 401) {
        logout()
        return null
      }
      const data = await res.json()
      const session = data.session
      if (session) {
        sessionIdRef.current = session.id
        isSourceTabRef.current = true
        savedCountRef.current = 0
        return session.id
      }
      return null
    } catch {
      return null
    }
  }

  const clearSession = async () => {
    const sid = sessionIdRef.current
    if (sid) {
      try {
        await fetch(`${API_AGENTS_SESSIONS_URL}/${sid}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` }
        })
      } catch {
        /* ignore */
      }
    }
    sessionIdRef.current = null
    isSourceTabRef.current = false
    savedCountRef.current = 0
    setConversationHistory([])
    pendingProposalRef.current = null
    contextUsageRef.current = null
    uiStateRef.current = null
  }

  const cancelRunningJob = () => {
    const sid = sessionIdRef.current
    if (sid) {
      fetch(apiJobCancelUrl(sid), {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      }).catch(() => {})
    }
    isSourceTabRef.current = false
  }

  const markSessionCancelled = () => {
    const sid = sessionIdRef.current
    if (sid) {
      fetch(`${API_AGENTS_SESSIONS_URL}/${sid}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          status: 'cancelled',
          ui_state: { running: false, executingTool: null }
        })
      }).catch(() => {})
    }
  }

  return {
    conversationHistory,
    setConversationHistory,
    conversationHistoryRef,
    sessionIdRef,
    isSourceTabRef,
    restoredSession,
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
  }
}
