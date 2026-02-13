import { useState, useEffect } from 'react'

/**
 * Pure SVG charts showing DP value iteration convergence.
 * Top chart: Bellman error (log scale) vs iteration.
 * Bottom chart: Expected cost of current policy vs iteration.
 */
function ConvergenceChart({
  data,
  method,
  parameters,
  solvingStartTime,
  completed,
  timeLimitMinutes
}) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!solvingStartTime) {
      setElapsed(0)
      return
    }
    const tick = () => setElapsed(Math.floor((Date.now() - solvingStartTime) / 1000))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [solvingStartTime])

  const minutes = String(Math.floor(elapsed / 60)).padStart(2, '0')
  const seconds = String(elapsed % 60).padStart(2, '0')
  const limitStr = timeLimitMinutes ? `${String(timeLimitMinutes).padStart(2, '0')}:00` : null
  const elapsedStr = limitStr ? `${minutes}:${seconds} / ${limitStr}` : `${minutes}:${seconds}`
  const overLimit = timeLimitMinutes && elapsed > timeLimitMinutes * 60

  if (!data || data.length === 0) {
    return (
      <div className="card ia-entry ia-streaming-entry">
        <div className="card-body">
          <div className="ia-thinking-header">
            <div className="spinner-border spinner-border-sm" role="status">
              <span className="sr-only">Loading...</span>
            </div>
            <span className="ia-thinking-title">
              Waiting for solver data...
              {solvingStartTime && (
                <span
                  style={{
                    marginLeft: '12px',
                    color: overLimit ? '#dc3545' : '#888',
                    fontWeight: overLimit ? '600' : 'normal'
                  }}
                >
                  {elapsedStr}
                </span>
              )}
            </span>
          </div>
        </div>
      </div>
    )
  }

  const width = 900
  const height = 260
  const pad = { top: 20, right: 20, bottom: 35, left: 65 }
  const plotW = width - pad.left - pad.right
  const plotH = height - pad.top - pad.bottom

  // --- Bellman error chart data ---
  const iterations = data.map((d) => d.iteration)
  const errors = data.map((d) => d.bellman_error ?? 0)
  const logErrors = errors.map((e) => (e > 0 ? Math.log10(e) : -10))

  const minIter = Math.min(...iterations)
  const maxIter = Math.max(...iterations)
  const minLog = Math.min(...logErrors)
  const maxLog = Math.max(...logErrors)
  const rangeIter = maxIter - minIter || 1
  const rangeLog = maxLog - minLog || 1

  const xScale = (iter) => pad.left + ((iter - minIter) / rangeIter) * plotW
  const yScale = (logE) => pad.top + plotH - ((logE - minLog) / rangeLog) * plotH

  const errorPath = data
    .map((d, i) => {
      const logE = d.bellman_error > 0 ? Math.log10(d.bellman_error) : -10
      return `${i === 0 ? 'M' : 'L'}${xScale(d.iteration)},${yScale(logE)}`
    })
    .join(' ')

  const latest = data[data.length - 1] || {}
  const latestError = latest.bellman_error != null ? latest.bellman_error : null
  const yTicks = 5
  const tickVals = Array.from({ length: yTicks + 1 }, (_, i) => minLog + (rangeLog / yTicks) * i)

  // --- Expected cost chart data ---
  const costData = data.filter((d) => d.expected_cost != null)
  const hasCostData = costData.length > 0
  const latestCost = hasCostData ? costData[costData.length - 1].expected_cost : null

  let costChart = null
  if (hasCostData) {
    const costVals = costData.map((d) => d.expected_cost)
    const minCost = Math.min(...costVals)
    const maxCost = Math.max(...costVals)
    const rangeCost = maxCost - minCost || 1
    const costPad = 0.05 * rangeCost
    const adjMin = minCost - costPad
    const adjMax = maxCost + costPad
    const adjRange = adjMax - adjMin || 1

    const cXScale = (iter) => pad.left + ((iter - minIter) / rangeIter) * plotW
    const cYScale = (c) => pad.top + plotH - ((c - adjMin) / adjRange) * plotH

    const costPath = costData
      .map((d, i) => `${i === 0 ? 'M' : 'L'}${cXScale(d.iteration)},${cYScale(d.expected_cost)}`)
      .join(' ')

    const costTickVals = Array.from(
      { length: yTicks + 1 },
      (_, i) => adjMin + (adjRange / yTicks) * i
    )

    // Dots at each eval point
    const costDots = costData.map((d) => ({
      cx: cXScale(d.iteration),
      cy: cYScale(d.expected_cost),
      iter: d.iteration,
      cost: d.expected_cost
    }))

    costChart = (
      <div style={{ marginTop: '8px' }}>
        <div style={{ fontSize: '12px', fontWeight: 600, color: '#333', marginBottom: '4px' }}>
          Expected Cost (policy evaluation every{' '}
          {costData.length > 1 ? costData[1].iteration - costData[0].iteration : '?'} iterations)
        </div>
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto' }}>
          {costTickVals.map((v, i) => (
            <g key={i}>
              <line
                x1={pad.left}
                x2={pad.left + plotW}
                y1={cYScale(v)}
                y2={cYScale(v)}
                stroke="#e0e0e0"
                strokeWidth="1"
              />
              <text x={pad.left - 8} y={cYScale(v) + 4} textAnchor="end" fontSize="10" fill="#666">
                {v.toFixed(1)}
              </text>
            </g>
          ))}
          <line
            x1={pad.left}
            x2={pad.left}
            y1={pad.top}
            y2={pad.top + plotH}
            stroke="#ccc"
            strokeWidth="1"
          />
          <line
            x1={pad.left}
            x2={pad.left + plotW}
            y1={pad.top + plotH}
            y2={pad.top + plotH}
            stroke="#ccc"
            strokeWidth="1"
          />
          <path d={costPath} fill="none" stroke="#0d6efd" strokeWidth="2" />
          {costDots.map((dot, i) => (
            <circle key={i} cx={dot.cx} cy={dot.cy} r="3" fill="#0d6efd" />
          ))}
          <text
            x={pad.left + plotW / 2}
            y={height - 5}
            textAnchor="middle"
            fontSize="11"
            fill="#666"
          >
            Iteration
          </text>
          <text
            x={12}
            y={pad.top + plotH / 2}
            textAnchor="middle"
            fontSize="11"
            fill="#666"
            transform={`rotate(-90, 12, ${pad.top + plotH / 2})`}
          >
            Expected Cost
          </text>
        </svg>
      </div>
    )
  }

  return (
    <div className="card ia-entry ia-streaming-entry">
      <div className="card-body">
        <div className="ia-thinking-header">
          {completed ? (
            <i className="fa fa-check-circle" aria-hidden="true" style={{ color: '#28a745' }} />
          ) : (
            <div className="spinner-border spinner-border-sm" role="status">
              <span className="sr-only">Loading...</span>
            </div>
          )}
          <i className="fa fa-line-chart" aria-hidden="true" />
          <span className="ia-thinking-title">
            {completed ? 'DP Value Iteration Complete' : 'DP Value Iteration'} &mdash;{' '}
            {latest.iteration ?? 0} Iterations
            {latest.num_states > 0 && <span> | {latest.num_states} states</span>}
            {latestError != null && <span>, Bellman Error: {latestError.toExponential(2)}</span>}
            {latestCost != null && <span>, Cost: {latestCost.toFixed(2)}</span>}
            {!completed && solvingStartTime && (
              <span
                style={{
                  marginLeft: '12px',
                  color: overLimit ? '#dc3545' : '#888',
                  fontWeight: overLimit ? '600' : 'normal'
                }}
              >
                {elapsedStr}
              </span>
            )}
          </span>
        </div>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          style={{ width: '100%', height: 'auto', marginTop: '10px' }}
        >
          {tickVals.map((v, i) => (
            <g key={i}>
              <line
                x1={pad.left}
                x2={pad.left + plotW}
                y1={yScale(v)}
                y2={yScale(v)}
                stroke="#e0e0e0"
                strokeWidth="1"
              />
              <text x={pad.left - 8} y={yScale(v) + 4} textAnchor="end" fontSize="10" fill="#666">
                {`10^${v.toFixed(1)}`}
              </text>
            </g>
          ))}
          <line
            x1={pad.left}
            x2={pad.left}
            y1={pad.top}
            y2={pad.top + plotH}
            stroke="#ccc"
            strokeWidth="1"
          />
          <line
            x1={pad.left}
            x2={pad.left + plotW}
            y1={pad.top + plotH}
            y2={pad.top + plotH}
            stroke="#ccc"
            strokeWidth="1"
          />
          <path d={errorPath} fill="none" stroke="#212529" strokeWidth="2.5" />
          <text
            x={pad.left + plotW / 2}
            y={height - 5}
            textAnchor="middle"
            fontSize="11"
            fill="#666"
          >
            Iteration
          </text>
          <text
            x={12}
            y={pad.top + plotH / 2}
            textAnchor="middle"
            fontSize="11"
            fill="#666"
            transform={`rotate(-90, 12, ${pad.top + plotH / 2})`}
          >
            Bellman Error (log)
          </text>
        </svg>
        {costChart}
        {(method || parameters) && (
          <div
            style={{
              marginTop: '8px',
              fontSize: '12px',
              color: '#555',
              display: 'flex',
              flexWrap: 'wrap',
              gap: '16px'
            }}
          >
            {method && (
              <span>
                <strong>Method:</strong> {method}
              </span>
            )}
            {parameters && (
              <span>
                <strong>Parameters:</strong> {parameters}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default ConvergenceChart
