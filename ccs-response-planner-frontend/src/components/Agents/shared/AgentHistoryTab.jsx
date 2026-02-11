import { useState } from 'react'

/**
 * Shared history tab for all agents.
 * Displays a list of saved reports with expand/collapse and delete.
 */
function AgentHistoryTab({ reportHistory, deleteReport }) {
  const [historyExpanded, setHistoryExpanded] = useState({})

  if (reportHistory.length === 0) {
    return (
      <p style={{ fontSize: '13px', color: '#6c757d', marginTop: '16px' }}>
        No reports saved yet. Run the agent to generate a report.
      </p>
    )
  }

  return (
    <div style={{ marginTop: '16px' }}>
      <div className="card">
        <div className="card-body" style={{ padding: '0' }}>
          {reportHistory.map((entry) => (
            <div key={entry.id} className="ia-history-entry">
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: 'pointer'
                }}
                onClick={() =>
                  setHistoryExpanded((prev) => ({
                    ...prev,
                    [entry.id]: !prev[entry.id]
                  }))
                }
              >
                <span style={{ fontSize: '12px', color: '#495057' }}>
                  {new Date(entry.created_at).toLocaleString()}
                  <span style={{ color: '#888', marginLeft: '8px' }}>{entry.username}</span>
                </span>
                <i
                  className={`fa fa-caret-${historyExpanded[entry.id] ? 'down' : 'right'}`}
                  aria-hidden="true"
                  style={{ color: '#6c757d' }}
                />
              </div>
              {historyExpanded[entry.id] && (
                <div className="ia-history-detail">
                  <pre>{JSON.stringify(entry.report, null, 2)}</pre>
                  <button
                    type="button"
                    className="btn btn-outline-danger btn-sm"
                    style={{ fontSize: '11px', padding: '2px 10px' }}
                    onClick={() => deleteReport(entry.id)}
                  >
                    <i className="fa fa-trash" aria-hidden="true" /> Delete
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default AgentHistoryTab
