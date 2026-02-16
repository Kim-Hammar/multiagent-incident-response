const STRIP_KEYS = new Set([
  '_model_parts',
  '_anthropic_content',
  '_tool_use_id',
  '_vendor',
  '_runId',
  'subEvents'
])

/**
 * Clean conversation history before persisting.
 * Removes transient streaming entries and strips internal API fields.
 */
export function cleanConversationHistory(history) {
  return history
    .filter((entry) => entry.type !== 'streaming')
    .map((entry) => {
      const cleaned = {}
      for (const [key, value] of Object.entries(entry)) {
        if (!STRIP_KEYS.has(key)) {
          cleaned[key] = value
        }
      }
      return cleaned
    })
}

const BACKEND_STRIP_KEYS = new Set([
  ...STRIP_KEYS,
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
