import { useState } from 'react'

/**
 * Shared history tab for all agents.
 * Displays a list of saved reports with expand/collapse and delete.
 * Uses a renderReport render prop to display agent-specific report formatting.
 */
function AgentHistoryTab({ reportHistory, deleteReport, renderReport }) {
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
      {reportHistory.map((entry) => (
        <div key={entry.id} style={{ marginBottom: '12px' }}>
          <div
            className="card"
            style={{ cursor: 'pointer' }}
            onClick={() =>
              setHistoryExpanded((prev) => ({
                ...prev,
                [entry.id]: !prev[entry.id]
              }))
            }
          >
            <div
              className="card-body"
              style={{
                padding: '8px 14px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}
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
          </div>
          {historyExpanded[entry.id] && (
            <div style={{ marginTop: '8px' }}>
              {renderReport(entry.report)}
              <button
                type="button"
                className="btn btn-outline-danger btn-sm"
                style={{ fontSize: '11px', padding: '2px 10px', marginTop: '8px' }}
                onClick={() => deleteReport(entry.id)}
              >
                <i className="fa fa-trash" aria-hidden="true" /> Delete
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

export default AgentHistoryTab
