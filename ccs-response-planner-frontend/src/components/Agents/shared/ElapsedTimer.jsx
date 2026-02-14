import { useState, useEffect } from 'react'

/**
 * Small component that displays elapsed seconds.
 * If `startTime` (epoch ms) is provided, computes elapsed from that
 * timestamp — this is resilient to component remounts.
 * Otherwise falls back to counting from mount time.
 */
function ElapsedTimer({ startTime }) {
  const [seconds, setSeconds] = useState(() =>
    startTime ? Math.floor((Date.now() - startTime) / 1000) : 0
  )
  useEffect(() => {
    const id = setInterval(
      () => setSeconds(startTime ? Math.floor((Date.now() - startTime) / 1000) : (s) => s + 1),
      1000
    )
    return () => clearInterval(id)
  }, [startTime])
  return <span className="ia-elapsed">{seconds}s</span>
}

export default ElapsedTimer
