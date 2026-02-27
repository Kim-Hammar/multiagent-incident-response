/**
 * Polling utility for background job events.
 *
 * Replaces NDJSON streaming with periodic polling of
 * the /api/agents/jobs/<jobId>/events endpoint.
 */

const API_BASE = '/api/agents/jobs'
const STALE_THRESHOLD = 30000
const EVENT_LIMIT = 5
const FETCH_TIMEOUT = 10000

/**
 * Poll a background job for events until it completes.
 *
 * @param {Object} opts
 * @param {string} opts.jobId - The background job ID
 * @param {string} opts.token - Auth bearer token
 * @param {AbortSignal} [opts.signal] - Optional AbortController signal
 * @param {(event: Object, eventIndex: number) => void} opts.onEvent - Called for each new event (with its global index)
 * @param {(status: string) => void} [opts.onHeartbeat] - Called with status string on each heartbeat
 * @param {(elapsedMs: number) => void} [opts.onStale] - Called when no real events for 30s
 * @param {number} [opts.startIndex=0] - Event index to start polling from
 * @param {number} [opts.pollInterval=300] - Milliseconds between polls
 * @returns {Promise<void>}
 */
export async function pollJobEvents({
  jobId,
  token,
  signal,
  onEvent,
  onHeartbeat,
  onStale,
  startIndex = 0,
  pollInterval = 100
}) {
  let nextIndex = startIndex
  let retries = 0
  const MAX_RETRIES = 45
  let lastRealEventTime = Date.now()
  let staleNotified = false
  let pollCount = 0

  while (true) {
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')

    let gotFullBatch = false
    pollCount++

    try {
      const fetchSignal = signal
        ? AbortSignal.any([signal, AbortSignal.timeout(FETCH_TIMEOUT)])
        : AbortSignal.timeout(FETCH_TIMEOUT)

      const url = `${API_BASE}/${jobId}/events?after=${nextIndex}&limit=${EVENT_LIMIT}`
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
        signal: fetchSignal
      })

      if (res.status === 401) {
        throw Object.assign(new Error('Unauthorized'), { status: 401 })
      }
      if (!res.ok) {
        console.warn('[pollJobEvents] HTTP %d for job=%s after=%d', res.status, jobId, nextIndex)
        throw new Error(`Job poll failed (HTTP ${res.status})`)
      }

      const data = await res.json()
      const { events, done, error, next_index } = data

      retries = 0
      gotFullBatch = events.length >= EVENT_LIMIT

      // Log every 50th poll and whenever done or non-empty events
      if (done || events.length > 0 || pollCount % 50 === 0) {
        const types = events.map((e) => e.type).join(',')
        console.log(
          '[pollJobEvents] job=%s poll#%d after=%d events=%d types=[%s] done=%s next=%d',
          jobId,
          pollCount,
          nextIndex,
          events.length,
          types,
          done,
          next_index
        )
      }

      // Advance cursor before processing so an onEvent error
      // cannot leave us re-fetching the same batch forever.
      const batchStartIndex = nextIndex
      nextIndex = next_index

      for (let i = 0; i < events.length; i++) {
        const event = events[i]
        try {
          if (event.type === 'heartbeat') {
            lastRealEventTime = Date.now()
            staleNotified = false
            if (onHeartbeat && event.status) onHeartbeat(event.status)
            continue
          }
          lastRealEventTime = Date.now()
          staleNotified = false
          onEvent(event, batchStartIndex + i)
        } catch (eventErr) {
          // Always propagate abort so callers can cancel cleanly.
          if (eventErr.name === 'AbortError') throw eventErr
          // Log unexpected processing errors but keep polling —
          // a frozen UI is worse than a skipped event.
          console.error('[pollJobEvents] onEvent error (skipped):', eventErr)
        }
      }

      if (done) {
        console.log('[pollJobEvents] job=%s DONE after %d polls', jobId, pollCount)
        if (error) {
          const err = new Error(error.message || String(error))
          err.errorDetail = error
          throw err
        }
        return
      }
    } catch (err) {
      if (err.name === 'AbortError' && signal?.aborted) throw err
      if (
        (err.name === 'TimeoutError' || err.name === 'TypeError' || err.name === 'SyntaxError') &&
        retries < MAX_RETRIES
      ) {
        retries++
        if (retries % 5 === 0) {
          console.warn(
            '[pollJobEvents] job=%s retry %d/%d (%s: %s)',
            jobId,
            retries,
            MAX_RETRIES,
            err.name,
            err.message
          )
        }
      } else {
        console.error(
          '[pollJobEvents] job=%s fatal error after %d polls: %s: %s',
          jobId,
          pollCount,
          err.name,
          err.message
        )
        err._source = 'poll_network'
        throw err
      }
    }

    // Stale check runs every iteration — even after failed fetches
    if (onStale && !staleNotified && Date.now() - lastRealEventTime > STALE_THRESHOLD) {
      staleNotified = true
      onStale(Date.now() - lastRealEventTime)
    }

    // When catching up (got a full batch), poll immediately — more events
    // are likely waiting.  Only sleep when we're caught up or on error.
    if (!gotFullBatch) {
      await new Promise((resolve) => setTimeout(resolve, pollInterval))
    }
  }
}
