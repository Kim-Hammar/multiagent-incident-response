import { Fragment } from 'react'

/**
 * Shared Jobs tab component — shows all background jobs with
 * cancel/remove controls.
 */
function JobsTab({ jobs, fetchJobs, cancelJob, removeJob, removeAllDoneJobs }) {
  const ago = (ms) => {
    const s = Math.round((Date.now() - ms) / 1000)
    if (s < 60) return `${s}s ago`
    if (s < 3600) return `${Math.round(s / 60)}m ago`
    return `${Math.round(s / 3600)}h ago`
  }

  return (
    <div style={{ marginTop: '16px' }}>
      <div className="d-flex mb-2" style={{ gap: '8px' }}>
        <button className="btn btn-sm btn-outline-secondary ia-btn" onClick={fetchJobs}>
          <i className="fa fa-refresh" /> Refresh
        </button>
        {jobs.some((j) => j.done) && (
          <button className="btn btn-sm btn-outline-danger ia-btn" onClick={removeAllDoneJobs}>
            Remove all done
          </button>
        )}
      </div>
      {jobs.length === 0 ? (
        <p className="text-muted">No jobs tracked.</p>
      ) : (
        <div className="table-responsive">
          <table className="table table-sm table-bordered" style={{ fontSize: '13px' }}>
            <thead>
              <tr>
                <th>Job ID</th>
                <th>Status</th>
                <th>Events</th>
                <th>Started</th>
                <th>Last Activity</th>
                <th>Status Text</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => {
                const badge = j.error
                  ? 'badge-danger'
                  : j.cancelled
                    ? 'badge-warning'
                    : j.done
                      ? 'badge-success'
                      : 'badge-primary'
                const label = j.error
                  ? 'error'
                  : j.cancelled
                    ? 'cancelled'
                    : j.done
                      ? 'done'
                      : 'running'
                return (
                  <Fragment key={j.job_id}>
                    <tr>
                      <td>
                        <code>{j.job_id.slice(0, 8)}</code>
                      </td>
                      <td>
                        <span className={`badge ${badge}`}>{label}</span>
                      </td>
                      <td>{j.event_count}</td>
                      <td>{ago(j.start_time)}</td>
                      <td>{ago(j.last_event_time)}</td>
                      <td
                        style={{
                          maxWidth: '250px',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis'
                        }}
                      >
                        {j.last_status}
                      </td>
                      <td>
                        {!j.done && !j.cancelled && (
                          <button
                            className="btn btn-sm btn-outline-danger ia-btn mr-1"
                            onClick={() => cancelJob(j.job_id)}
                          >
                            Cancel
                          </button>
                        )}
                        {j.done && (
                          <button
                            className="btn btn-sm btn-outline-danger ia-btn"
                            onClick={() => removeJob(j.job_id)}
                          >
                            Remove
                          </button>
                        )}
                      </td>
                    </tr>
                    {j.error && (
                      <tr>
                        <td
                          colSpan={7}
                          style={{
                            backgroundColor: '#fff0f0',
                            borderTop: 'none',
                            padding: '4px 12px 8px',
                            fontSize: '0.85em'
                          }}
                        >
                          <i className="fa fa-exclamation-triangle text-danger" />{' '}
                          <span
                            style={{
                              fontFamily: 'monospace',
                              whiteSpace: 'pre-wrap',
                              wordBreak: 'break-word'
                            }}
                          >
                            {j.error}
                          </span>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default JobsTab
