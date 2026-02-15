/**
 * Shared NDJSON streaming helper for dt_exec / pentest_exec tool execution
 * and sub-agent streaming tools (run_code_agent, run_code_reviewer_agent).
 */

export const STREAMING_TOOLS = new Set([
  'dt_exec',
  'pentest_exec',
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
 * Execute a streaming tool call, reading NDJSON from the response body.
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
  extraBody
}) {
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

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
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
        if (event.type === 'output_chunk') {
          onChunk(event.text)
        } else if (event.type === 'sub_event' && onSubEvent) {
          onSubEvent(event.event)
        } else if (event.type === 'done') {
          doneEvent = event
        } else if (event.type === 'error') {
          throw new Error(event.message || 'Streaming tool error')
        }
      } catch (e) {
        if (e.message && !e.message.startsWith('Unexpected')) throw e
        /* skip non-JSON lines */
      }
    }
  }

  if (!doneEvent) {
    throw new Error('Stream ended without a done event')
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
