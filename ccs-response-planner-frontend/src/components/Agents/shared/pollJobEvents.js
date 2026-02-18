/**
 * Polling utility for background job events.
 *
 * Replaces NDJSON streaming with periodic polling of
 * the /api/agents/jobs/<jobId>/events endpoint.
 */

const API_BASE = '/api/agents/jobs'
const STALE_THRESHOLD = 30000

/**
 * Poll a background job for events until it completes.
 *
 * @param {Object} opts
 * @param {string} opts.jobId - The background job ID
 * @param {string} opts.token - Auth bearer token
 * @param {AbortSignal} [opts.signal] - Optional AbortController signal
 * @param {(event: Object) => void} opts.onEvent - Called for each new event
 * @param {(status: string) => void} [opts.onHeartbeat] - Called with status string on each heartbeat
 * @param {(elapsedMs: number) => void} [opts.onStale] - Called when no real events for 30s
 * @param {number} [opts.pollInterval=300] - Milliseconds between polls
 * @param {number} [opts.maxDuration=18000000] - Max polling duration in ms (default 5 hours)
 * @returns {Promise<void>}
 */
export async function pollJobEvents({
  jobId,
  token,
  signal,
  onEvent,
  onHeartbeat,
  onStale,
  pollInterval = 300,
  maxDuration = 5 * 60 * 60 * 1000
}) {
  let nextIndex = 0
  let retries = 0
  const MAX_RETRIES = 5
  const startTime = Date.now()
  let lastRealEventTime = Date.now()
  let staleNotified = false

  while (true) {
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')

    if (Date.now() - startTime > maxDuration) {
      throw new Error(
        'Job polling timed out — the operation took too long. Check the History tab for results.'
      )
    }

    try {
      const fetchSignal = signal
        ? AbortSignal.any([signal, AbortSignal.timeout(10000)])
        : AbortSignal.timeout(10000)

      const res = await fetch(`${API_BASE}/${jobId}/events?after=${nextIndex}`, {
        headers: { Authorization: `Bearer ${token}` },
        signal: fetchSignal
      })

      if (res.status === 401) {
        throw Object.assign(new Error('Unauthorized'), { status: 401 })
      }
      if (!res.ok) {
        throw new Error(`Job poll failed (HTTP ${res.status})`)
      }

      const data = await res.json()
      const { events, done, error, next_index } = data

      retries = 0

      for (const event of events) {
        if (event.type === 'heartbeat') {
          lastRealEventTime = Date.now()
          staleNotified = false
          if (onHeartbeat && event.status) onHeartbeat(event.status)
          continue
        }
        lastRealEventTime = Date.now()
        staleNotified = false
        onEvent(event)
      }

      nextIndex = next_index

      if (done) {
        if (error) throw new Error(error)
        return
      }
    } catch (err) {
      if (err.name === 'AbortError' && signal?.aborted) throw err
      if ((err.name === 'TimeoutError' || err.name === 'TypeError') && retries < MAX_RETRIES) {
        retries++
      } else {
        throw err
      }
    }

    // Stale check runs every iteration — even after failed fetches
    if (onStale && !staleNotified && Date.now() - lastRealEventTime > STALE_THRESHOLD) {
      staleNotified = true
      onStale(Date.now() - lastRealEventTime)
    }

    await new Promise((resolve) => setTimeout(resolve, pollInterval))
  }
}
