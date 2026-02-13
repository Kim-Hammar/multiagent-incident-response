const STRIP_KEYS = new Set([
  '_model_parts',
  '_anthropic_content',
  '_tool_use_id',
  '_vendor',
  '_runId'
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
