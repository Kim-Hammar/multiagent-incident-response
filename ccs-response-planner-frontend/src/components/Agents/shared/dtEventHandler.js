/**
 * Process a DT redeploy event by updating a mutable dtEntries array.
 * Used by agent components that rebuild conversation history on each event.
 * The caller must include dtEntries in its setConversationHistory call.
 */
export function processDtEvent(event, dtEntries, setDtStatus) {
  if (event.type === 'dt_progress') {
    setDtStatus(event.message)
    for (const e of dtEntries) {
      if (!e.done) {
        e.done = true
      }
    }
    dtEntries.push({
      role: 'system',
      type: 'dt_redeploy',
      phase: event.phase,
      message: event.message,
      done: event.phase === 'ready',
      details: [],
      _startTime: Date.now()
    })
  } else if (event.type === 'dt_progress_detail') {
    const target = [...dtEntries]
      .reverse()
      .find((e) => e.phase === event.phase)
    if (target) {
      target.details = [...(target.details || []), event.message]
    }
  } else if (event.type === 'sandbox_progress') {
    setDtStatus(event.message)
    for (const e of dtEntries) {
      if (e.type === 'sandbox_start' && !e.done) {
        e.done = true
      }
    }
    dtEntries.push({
      role: 'system',
      type: 'sandbox_start',
      phase: event.phase,
      message: event.message,
      done: event.phase === 'ready',
      details: [],
      _startTime: Date.now()
    })
  }
}

/**
 * Handle a DT redeploy event using setConversationHistory with functional
 * updaters. Used by ResponsePlanner which mutates the streaming entry in
 * place and never rebuilds the full history array.
 */
export function handleDtEvent(event, setConversationHistory, setDtStatus) {
  if (event.type === 'dt_progress') {
    setDtStatus(event.message)
    setConversationHistory((prev) => {
      const updated = [...prev]
      for (const e of updated) {
        if (e.type === 'dt_redeploy' && !e.done) {
          e.done = true
        }
      }
      return [
        ...updated,
        {
          role: 'system',
          type: 'dt_redeploy',
          phase: event.phase,
          message: event.message,
          done: event.phase === 'ready',
          details: [],
          _startTime: Date.now()
        }
      ]
    })
  } else if (event.type === 'dt_progress_detail') {
    setConversationHistory((prev) => {
      const target = [...prev]
        .reverse()
        .find((e) => e.type === 'dt_redeploy' && e.phase === event.phase)
      if (target) {
        target.details = [...(target.details || []), event.message]
      }
      return [...prev]
    })
  } else if (event.type === 'sandbox_progress') {
    setDtStatus(event.message)
    setConversationHistory((prev) => {
      const updated = [...prev]
      for (const e of updated) {
        if (e.type === 'sandbox_start' && !e.done) {
          e.done = true
        }
      }
      return [
        ...updated,
        {
          role: 'system',
          type: 'sandbox_start',
          phase: event.phase,
          message: event.message,
          done: event.phase === 'ready',
          details: [],
          _startTime: Date.now()
        }
      ]
    })
  }
}
