/**
 * Polling utility for background job events.
 *
 * Replaces NDJSON streaming with periodic polling of
 * the /api/agents/jobs/<jobId>/events endpoint.
 */

const API_BASE = '/api/agents/jobs'

/**
 * Poll a background job for events until it completes.
 *
 * @param {Object} opts
 * @param {string} opts.jobId - The background job ID
 * @param {string} opts.token - Auth bearer token
 * @param {AbortSignal} [opts.signal] - Optional AbortController signal
 * @param {(event: Object) => void} opts.onEvent - Called for each new event
 * @param {number} [opts.pollInterval=300] - Milliseconds between polls
 * @returns {Promise<void>}
 */
export async function pollJobEvents({ jobId, token, signal, onEvent, pollInterval = 300 }) {
  let nextIndex = 0
  while (true) {
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')

    const res = await fetch(`${API_BASE}/${jobId}/events?after=${nextIndex}`, {
      headers: { Authorization: `Bearer ${token}` },
      signal
    })

    if (res.status === 401) {
      throw Object.assign(new Error('Unauthorized'), { status: 401 })
    }
    if (!res.ok) {
      throw new Error(`Job poll failed (HTTP ${res.status})`)
    }

    const data = await res.json()
    const { events, done, error, next_index } = data

    for (const event of events) {
      onEvent(event)
    }

    nextIndex = next_index

    if (done) {
      if (error) throw new Error(error)
      return
    }

    await new Promise((resolve) => setTimeout(resolve, pollInterval))
  }
}
