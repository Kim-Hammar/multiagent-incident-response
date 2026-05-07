import RewardChart from './RewardChart.jsx'

function downloadPolicyZip(policyData) {
  const bytes = Uint8Array.from(atob(policyData), (c) => c.charCodeAt(0))
  const blob = new Blob([bytes], { type: 'application/zip' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'rl_policy.zip'
  a.click()
  URL.revokeObjectURL(url)
}

/**
 * Renders an rl_train tool result as a training chart + evaluation summary,
 * replacing the default raw-JSON display.
 */
function RlTrainResult({ trainingData, trainingMeta, result, policyData }) {
  const evalResult = result?.result
  const doneEvent = result?.done
  const actions = evalResult?.action_sequence || []
  const meanCost = evalResult?.total_reward != null ? -evalResult.total_reward : null
  const detailCost =
    evalResult?.detail_episode_reward != null ? -evalResult.detail_episode_reward : null

  return (
    <div>
      {trainingData && trainingData.length > 0 && (
        <RewardChart
          data={trainingData}
          algorithm={trainingMeta?.algorithm}
          hyperparameters={trainingMeta?.hyperparameters}
          completed={true}
        />
      )}

      {evalResult && (
        <div style={{ marginTop: '12px' }}>
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '12px',
              marginBottom: '12px'
            }}
          >
            {meanCost != null && (
              <div className="ia-metric-card">
                <div className="ia-metric-label">Mean Eval Cost</div>
                <div className="ia-metric-value">{meanCost.toFixed(2)}</div>
              </div>
            )}
            {detailCost != null && (
              <div className="ia-metric-card">
                <div className="ia-metric-label">Detail Episode Cost</div>
                <div className="ia-metric-value">{detailCost.toFixed(2)}</div>
              </div>
            )}
            {evalResult.num_steps != null && (
              <div className="ia-metric-card">
                <div className="ia-metric-label">Steps</div>
                <div className="ia-metric-value">{evalResult.num_steps}</div>
              </div>
            )}
            {evalResult.num_eval_episodes != null && (
              <div className="ia-metric-card">
                <div className="ia-metric-label">Eval Episodes</div>
                <div className="ia-metric-value">{evalResult.num_eval_episodes}</div>
              </div>
            )}
            {doneEvent?.exit_code != null && (
              <div className="ia-metric-card">
                <div className="ia-metric-label">Exit Code</div>
                <div className="ia-metric-value">{doneEvent.exit_code}</div>
              </div>
            )}
          </div>

          {policyData && (
            <div style={{ marginBottom: '12px' }}>
              <button
                className="btn btn-sm btn-outline-dark"
                onClick={() => downloadPolicyZip(policyData)}
              >
                <i className="fa fa-download" /> Download policy
              </button>
            </div>
          )}

          {actions.length > 0 && (
            <div>
              <div
                style={{ fontSize: '12px', fontWeight: 600, color: '#333', marginBottom: '6px' }}
              >
                Learned Action Sequence
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                {actions.map((action, i) => (
                  <span
                    key={i}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      background: '#f1f3f5',
                      border: '1px solid #dee2e6',
                      borderRadius: '4px',
                      padding: '2px 8px',
                      fontSize: '11px',
                      color: '#333'
                    }}
                  >
                    <span style={{ fontWeight: 600, color: '#868e96' }}>{i + 1}.</span>
                    {action}
                  </span>
                ))}
              </div>
            </div>
          )}

          {doneEvent?.stderr && (
            <details style={{ marginTop: '10px' }}>
              <summary style={{ fontSize: '12px', color: '#888', cursor: 'pointer' }}>
                stderr output
              </summary>
              <pre
                style={{
                  fontSize: '11px',
                  background: '#f8f9fa',
                  padding: '8px',
                  marginTop: '4px',
                  maxHeight: '150px',
                  overflow: 'auto'
                }}
              >
                {doneEvent.stderr}
              </pre>
            </details>
          )}
        </div>
      )}
    </div>
  )
}

export default RlTrainResult
