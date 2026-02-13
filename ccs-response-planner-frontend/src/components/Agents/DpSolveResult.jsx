import ConvergenceChart from './ConvergenceChart.jsx'

/**
 * Renders a dp_solve tool result as a convergence chart + evaluation summary,
 * replacing the default raw-JSON display.
 */
function DpSolveResult({ solverData, solverMeta, result }) {
  const evalResult = result?.result
  const doneEvent = result?.done
  const actions = evalResult?.action_sequence || []
  const meanCost = evalResult?.total_reward != null ? -evalResult.total_reward : null

  return (
    <div>
      {solverData && solverData.length > 0 && (
        <ConvergenceChart
          data={solverData}
          method={solverMeta?.method}
          parameters={solverMeta?.parameters}
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
            {evalResult.num_states != null && (
              <div className="ia-metric-card">
                <div className="ia-metric-label">Total States</div>
                <div className="ia-metric-value">{evalResult.num_states}</div>
              </div>
            )}
            {evalResult.num_iterations != null && (
              <div className="ia-metric-card">
                <div className="ia-metric-label">Iterations</div>
                <div className="ia-metric-value">{evalResult.num_iterations}</div>
              </div>
            )}
            {evalResult.final_bellman_error != null && (
              <div className="ia-metric-card">
                <div className="ia-metric-label">Final Bellman Error</div>
                <div className="ia-metric-value">
                  {evalResult.final_bellman_error.toExponential(2)}
                </div>
              </div>
            )}
            {meanCost != null && (
              <div className="ia-metric-card">
                <div className="ia-metric-label">Mean Eval Cost</div>
                <div className="ia-metric-value">{meanCost.toFixed(2)}</div>
              </div>
            )}
            {evalResult.num_steps != null && (
              <div className="ia-metric-card">
                <div className="ia-metric-label">Steps</div>
                <div className="ia-metric-value">{evalResult.num_steps}</div>
              </div>
            )}
            {doneEvent?.exit_code != null && (
              <div className="ia-metric-card">
                <div className="ia-metric-label">Exit Code</div>
                <div className="ia-metric-value">{doneEvent.exit_code}</div>
              </div>
            )}
          </div>

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

export default DpSolveResult
