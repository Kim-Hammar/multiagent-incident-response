const STRIP_KEYS = new Set([
  '_model_parts',
  '_anthropic_content',
  '_tool_use_id',
  '_vendor',
  '_runId'
])

const STRIP_SUBEVENTS_TOOLS = new Set([
  'run_report_agent',
  'run_report_reviewer_agent',
  'run_code_agent'
])

/**
 * Recursively walk a subEvents tree and replace base64 image data with
 * small placeholders so persisted JSONB doesn't bloat.
 */
function stripNestedImages(events) {
  if (!Array.isArray(events)) return events
  return events.map((evt) => {
    const copy = { ...evt }
    if (copy.result) {
      const r = { ...copy.result }
      if (r.image) r.image = '[image stripped]'
      if (r.attack_path_image) r.attack_path_image = '[image stripped]'
      copy.result = r
    }
    // Strip sub-agent activity sub-events — they contain the full
    // investigation activity which bloats persisted history and is
    // not needed outside the live streaming view.
    if (copy.type === 'tool_result' && STRIP_SUBEVENTS_TOOLS.has(copy.tool_name)) {
      delete copy.subEvents
    } else if (copy.subEvents) {
      copy.subEvents = stripNestedImages(copy.subEvents)
    }
    return copy
  })
}

/**
 * Clean conversation history before persisting.
 * Removes transient streaming / tool_streaming entries, strips internal API
 * fields, and replaces nested base64 images with placeholders.
 */
export function cleanConversationHistory(history) {
  return history
    .filter((entry) => entry.type !== 'streaming' && entry.type !== 'tool_streaming')
    .map((entry) => {
      const cleaned = {}
      for (const [key, value] of Object.entries(entry)) {
        if (!STRIP_KEYS.has(key)) {
          cleaned[key] = key === 'subEvents' ? stripNestedImages(value) : value
        }
      }
      return cleaned
    })
}

const BACKEND_STRIP_KEYS = new Set([
  ...STRIP_KEYS,
  'subEvents',
  'prompt',
  'promptImages',
  '_modelName',
  'contextUsage',
  '_startTime',
  'stopped'
])

/**
 * Strip UI-only fields from conversation history before sending to the backend.
 * Removes streaming entries, tool_streaming entries, and transient UI metadata.
 */
export function stripForBackend(history) {
  return history
    .filter((entry) => entry.type !== 'streaming' && entry.type !== 'tool_streaming')
    .map((entry) => {
      const cleaned = {}
      for (const [key, value] of Object.entries(entry)) {
        if (!BACKEND_STRIP_KEYS.has(key)) {
          cleaned[key] = value
        }
      }
      return cleaned
    })
}
