/**
 * Shared helper for dt_exec tool execution
 * and sub-agent streaming tools (run_code_agent, run_code_reviewer_agent).
 *
 * Uses background job polling instead of NDJSON streaming.
 */

import { pollJobEvents } from './pollJobEvents.js'

export const STREAMING_TOOLS = new Set([
  'dt_exec',
  'run_code_agent',
  'run_code_reviewer_agent',
  'run_code_manager',
  'run_rl_agent',
  'run_validation_agent',
  'run_report_agent',
  'run_report_reviewer_agent',
  'run_report_manager',
  'run_plan_manager'
])

/**
 * Execute a streaming tool call via a background job.
 *
 * POSTs to start the job, then polls for events.
 *
 * @param {Object} opts
 * @param {string} opts.url - The tool endpoint URL
 * @param {string} opts.toolName - The tool being executed
 * @param {Object} opts.toolArgs - Arguments for the tool
 * @param {number|null} opts.incidentId - Optional incident ID
 * @param {string} opts.token - Auth bearer token
 * @param {AbortSignal} opts.signal - AbortController signal
 * @param {(text: string) => void} opts.onChunk - Callback for each output chunk
 * @param {(event: Object) => void} [opts.onSubEvent] - Callback for sub-agent events
 * @param {Object} [opts.extraBody] - Extra fields to include in the request body
 * @returns {Promise<{result: Object}>} The final done event as tool result
 */
export async function executeStreamingTool({
  url,
  toolName,
  toolArgs,
  incidentId,
  token,
  signal,
  onChunk,
  onSubEvent,
  extraBody,
  resumeJobId,
  onHeartbeat,
  onStale
}) {
  let job_id = resumeJobId
  if (!job_id) {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({
        tool_name: toolName,
        tool_args: toolArgs,
        incident_id: incidentId,
        ...extraBody
      }),
      signal
    })

    if (res.status === 401) {
      throw Object.assign(new Error('Unauthorized'), { status: 401 })
    }
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}))
      throw new Error(errData.error || `Tool execution failed (HTTP ${res.status})`)
    }

    const resp = await res.json()
    job_id = resp.job_id
  }

  let doneEvent = null

  await pollJobEvents({
    jobId: job_id,
    token,
    signal,
    onHeartbeat,
    onStale,
    onEvent: (event) => {
      if (event.type === 'heartbeat') return
      if (event.type === 'output_chunk') {
        onChunk(event.text)
      } else if (event.type === 'sub_event' && onSubEvent) {
        if (event.ts) event.event._ts = event.ts
        onSubEvent(event.event)
      } else if (event.type === 'done') {
        doneEvent = event
      } else if (event.type === 'error') {
        throw new Error(event.message || 'Streaming tool error')
      }
    }
  })

  if (!doneEvent) {
    throw new Error('Job ended without a done event')
  }

  if (doneEvent.result) {
    return { result: doneEvent.result }
  }

  return {
    result: {
      container: doneEvent.container,
      command: doneEvent.command,
      exit_code: doneEvent.exit_code,
      output: doneEvent.output
    }
  }
}
