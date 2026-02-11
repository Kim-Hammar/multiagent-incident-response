import { useState, useEffect } from 'react'

/**
 * Small component that displays elapsed seconds since mount.
 */
function ElapsedTimer() {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setSeconds((s) => s + 1), 1000)
    return () => clearInterval(id)
  }, [])
  return <span className="ia-elapsed">{seconds}s</span>
}

export default ElapsedTimer
