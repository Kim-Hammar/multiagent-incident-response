/**
 * Pure SVG line chart showing RL training cost over episodes.
 * Two lines: individual episode cost (thin, lighter) + rolling mean (thick, dark).
 * Cost is the negated reward (cost = -reward), so positive values represent penalty.
 */
function RewardChart({ data, algorithm, hyperparameters }) {
  if (!data || data.length === 0) {
    return (
      <div className="card ia-entry ia-streaming-entry">
        <div className="card-body">
          <div className="ia-thinking-header">
            <div className="spinner-border spinner-border-sm" role="status">
              <span className="sr-only">Loading...</span>
            </div>
            <span className="ia-thinking-title">Waiting for training data...</span>
          </div>
        </div>
      </div>
    )
  }

  const width = 900
  const height = 320
  const pad = { top: 20, right: 20, bottom: 35, left: 55 }
  const plotW = width - pad.left - pad.right
  const plotH = height - pad.top - pad.bottom

  const episodes = data.map((d) => d.episode)
  const costs = data.map((d) => -d.reward)
  const meanCosts = data.map((d) => -d.mean_reward)
  const all = [...costs, ...meanCosts]

  const minEp = Math.min(...episodes)
  const maxEp = Math.max(...episodes)
  const minC = Math.min(...all)
  const maxC = Math.max(...all)
  const rangeEp = maxEp - minEp || 1
  const rangeC = maxC - minC || 1

  const xScale = (ep) => pad.left + ((ep - minEp) / rangeEp) * plotW
  const yScale = (c) => pad.top + plotH - ((c - minC) / rangeC) * plotH

  const costPath = data
    .map((d, i) => `${i === 0 ? 'M' : 'L'}${xScale(d.episode)},${yScale(-d.reward)}`)
    .join(' ')
  const meanPath = data
    .map((d, i) => `${i === 0 ? 'M' : 'L'}${xScale(d.episode)},${yScale(-d.mean_reward)}`)
    .join(' ')

  const latest = data[data.length - 1]
  const yTicks = 5
  const tickVals = Array.from({ length: yTicks + 1 }, (_, i) => minC + (rangeC / yTicks) * i)

  return (
    <div className="card ia-entry ia-streaming-entry">
      <div className="card-body">
        <div className="ia-thinking-header">
          <div className="spinner-border spinner-border-sm" role="status">
            <span className="sr-only">Loading...</span>
          </div>
          <i className="fa fa-line-chart" aria-hidden="true" />
          <span className="ia-thinking-title">
            RL Training &mdash; Episode {latest.episode}, Mean Cost:{' '}
            {(-latest.mean_reward).toFixed(2)}
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
          <path d={costPath} fill="none" stroke="#adb5bd" strokeWidth="1" opacity="0.6" />
          <path d={meanPath} fill="none" stroke="#212529" strokeWidth="2.5" />
          <text
            x={pad.left + plotW / 2}
            y={height - 5}
            textAnchor="middle"
            fontSize="11"
            fill="#666"
          >
            Episode
          </text>
          <text
            x={12}
            y={pad.top + plotH / 2}
            textAnchor="middle"
            fontSize="11"
            fill="#666"
            transform={`rotate(-90, 12, ${pad.top + plotH / 2})`}
          >
            Cost
          </text>
        </svg>
        {(algorithm || hyperparameters) && (
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
            {algorithm && (
              <span>
                <strong>Algorithm:</strong> {algorithm}
              </span>
            )}
            {hyperparameters && (
              <span>
                <strong>Hyperparameters:</strong> {hyperparameters}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default RewardChart
