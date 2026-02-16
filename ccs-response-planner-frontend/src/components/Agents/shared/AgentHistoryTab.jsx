import { useState, useRef } from 'react'
import AgentActivityLog from './AgentActivityLog.jsx'
import { API_AGENTS_REPORTS_URL } from '../../Common/constants.js'

/**
 * Shared history tab for all agents.
 * Displays a list of saved reports with expand/collapse and delete.
 * Uses a renderReport render prop to display agent-specific report formatting.
 * Optionally lazy-loads the full planning process (conversation history).
 */
function AgentHistoryTab({
  reportHistory,
  deleteReport,
  deleteAllReports,
  renderReport,
  renderFinalReport,
  renderToolResult,
  token,
  logout
}) {
  const [historyExpanded, setHistoryExpanded] = useState({})
  const [showProcess, setShowProcess] = useState({})
  const [loadedHistory, setLoadedHistory] = useState({})
  const [loadingHistory, setLoadingHistory] = useState({})
  const [processExpanded, setProcessExpanded] = useState({})
  const logEndRef = useRef(null)

  const fetchConversationHistory = async (reportId) => {
    if (loadedHistory[reportId]) {
      setShowProcess((prev) => ({ ...prev, [reportId]: !prev[reportId] }))
      return
    }
    setLoadingHistory((prev) => ({ ...prev, [reportId]: true }))
    try {
      const res = await fetch(`${API_AGENTS_REPORTS_URL}/${reportId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.status === 401 && logout) {
        logout()
        return
      }
      if (res.ok) {
        const data = await res.json()
        if (data.conversation_history) {
          setLoadedHistory((prev) => ({ ...prev, [reportId]: data.conversation_history }))
          setShowProcess((prev) => ({ ...prev, [reportId]: true }))
        }
      }
    } catch {
      /* ignore */
    } finally {
      setLoadingHistory((prev) => ({ ...prev, [reportId]: false }))
    }
  }

  const toggleProcessEntry = (reportId, index) => {
    setProcessExpanded((prev) => ({
      ...prev,
      [`${reportId}-${index}`]: !prev[`${reportId}-${index}`]
    }))
  }

  if (reportHistory.length === 0) {
    return (
      <p style={{ fontSize: '13px', color: '#6c757d', marginTop: '16px' }}>
        No reports saved yet. Run the agent to generate a report.
      </p>
    )
  }

  return (
    <div style={{ marginTop: '16px' }}>
      {deleteAllReports && reportHistory.length > 0 && (
        <div style={{ marginBottom: '12px' }}>
          <button
            type="button"
            className="btn btn-outline-danger btn-sm"
            style={{ fontSize: '11px', padding: '2px 10px' }}
            onClick={() => {
              if (window.confirm('Delete all reports? This cannot be undone.')) {
                deleteAllReports()
              }
            }}
          >
            <i className="fa fa-trash" aria-hidden="true" /> Delete all
          </button>
        </div>
      )}
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
                {entry.incident_name && (
                  <span style={{ color: '#007bff', marginLeft: '8px' }}>
                    <i className="fa fa-tag" aria-hidden="true" /> {entry.incident_name}
                  </span>
                )}
                {entry.model_name && (
                  <span style={{ color: '#6c757d', marginLeft: '8px' }}>
                    <i className="fa fa-microchip" aria-hidden="true" /> {entry.model_name}
                  </span>
                )}
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
              <div style={{ marginTop: '8px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                {entry.has_conversation_history && (
                  <button
                    type="button"
                    className={`btn btn-sm ${showProcess[entry.id] ? 'btn-outline-secondary' : 'btn-outline-info'}`}
                    style={{ fontSize: '11px', padding: '2px 10px' }}
                    onClick={() => fetchConversationHistory(entry.id)}
                    disabled={loadingHistory[entry.id]}
                  >
                    {loadingHistory[entry.id] ? (
                      <>
                        <span
                          className="spinner-border spinner-border-sm"
                          role="status"
                          style={{ width: '10px', height: '10px', marginRight: '4px' }}
                        />
                        Loading...
                      </>
                    ) : (
                      <>
                        <i
                          className={`fa fa-${showProcess[entry.id] ? 'eye-slash' : 'eye'}`}
                          aria-hidden="true"
                        />{' '}
                        {showProcess[entry.id] ? 'Hide' : 'Show'} planning process
                      </>
                    )}
                  </button>
                )}
                <button
                  type="button"
                  className="btn btn-outline-danger btn-sm"
                  style={{ fontSize: '11px', padding: '2px 10px' }}
                  onClick={() => deleteReport(entry.id)}
                >
                  <i className="fa fa-trash" aria-hidden="true" /> Delete
                </button>
              </div>
              {showProcess[entry.id] && loadedHistory[entry.id] && (
                <div style={{ marginTop: '12px' }}>
                  <AgentActivityLog
                    conversationHistory={loadedHistory[entry.id]}
                    expandedEntries={Object.fromEntries(
                      loadedHistory[entry.id].map((_, i) => [
                        i,
                        processExpanded[`${entry.id}-${i}`] ?? false
                      ])
                    )}
                    toggleEntry={(index) => toggleProcessEntry(entry.id, index)}
                    pendingProposal={null}
                    executingTool={null}
                    handleApprove={() => {}}
                    handleDeny={() => {}}
                    contextUsage={null}
                    hasNewActivity={false}
                    scrollToBottom={() => {}}
                    logEndRef={logEndRef}
                    streamingTraceRef={null}
                    renderFinalReport={renderFinalReport || null}
                    renderExecutingTool={null}
                    renderToolResult={renderToolResult || null}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

export default AgentHistoryTab
