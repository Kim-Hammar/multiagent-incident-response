import { useState, useEffect, useCallback, useRef } from 'react'
import {
  API_DIGITAL_TWIN_DEPLOY_URL,
  API_DIGITAL_TWIN_STOP_URL,
  API_DIGITAL_TWIN_STATUS_URL
} from '../Common/constants'
import Terminal from './Terminal.jsx'

/**
 * Deployment tab for the digital twin.
 * Provides deploy/stop controls, a live activity log, container status table, and terminal access.
 */
function DeployTab({ token, logout }) {
  const [status, setStatus] = useState(null)
  const [deploying, setDeploying] = useState(false)
  const [stopping, setStopping] = useState(false)
  const [logLines, setLogLines] = useState([])
  const [terminalContainer, setTerminalContainer] = useState(null)
  const intervalRef = useRef(null)
  const logEndRef = useRef(null)

  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch(API_DIGITAL_TWIN_STATUS_URL, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.status === 401) {
        logout()
        return
      }
      const data = await response.json()
      setStatus(data)
    } catch {
      /* polling failure is silent */
    }
  }, [token, logout])

  useEffect(() => {
    fetchStatus()
    intervalRef.current = setInterval(fetchStatus, 5000)
    return () => clearInterval(intervalRef.current)
  }, [fetchStatus])

  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logLines])

  const readNdjsonStream = async (url) => {
    setLogLines([])
    const response = await fetch(url, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` }
    })
    if (response.status === 401) {
      logout()
      return
    }
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop()
      for (const line of lines) {
        if (!line.trim()) continue
        try {
          const parsed = JSON.parse(line)
          if (parsed.type === 'progress') {
            setLogLines((prev) => [...prev, parsed.message])
          }
        } catch {
          /* skip malformed lines */
        }
      }
    }
  }

  const handleDeploy = async () => {
    setDeploying(true)
    try {
      await readNdjsonStream(API_DIGITAL_TWIN_DEPLOY_URL)
      await fetchStatus()
    } catch {
      setLogLines((prev) => [...prev, 'Error: deployment failed'])
    } finally {
      setDeploying(false)
    }
  }

  const handleStop = async () => {
    setTerminalContainer(null)
    setStopping(true)
    try {
      await readNdjsonStream(API_DIGITAL_TWIN_STOP_URL)
      await fetchStatus()
    } catch {
      setLogLines((prev) => [...prev, 'Error: shutdown failed'])
    } finally {
      setStopping(false)
    }
  }

  const deployed = status?.deployed || false
  const containers = status?.containers || []

  return (
    <div className="deploy-tab">
      <div className="deploy-controls">
        <button
          type="button"
          className="btn btn-dark deploy-btn"
          onClick={handleDeploy}
          disabled={deploying || stopping}
        >
          {deploying ? (
            <>
              <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />{' '}
              Deploying...
            </>
          ) : (
            <>
              <i className="fa fa-play" aria-hidden="true" /> Deploy
            </>
          )}
        </button>
        <button
          type="button"
          className="btn btn-outline-dark deploy-btn"
          onClick={handleStop}
          disabled={!deployed || deploying || stopping}
        >
          {stopping ? (
            <>
              <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />{' '}
              Stopping...
            </>
          ) : (
            <>
              <i className="fa fa-stop" aria-hidden="true" /> Stop
            </>
          )}
        </button>
        <span className={`badge badge-${deployed ? 'success' : 'secondary'} deploy-badge`}>
          {deployed ? 'Deployed' : 'Not deployed'}
        </span>
      </div>

      {logLines.length > 0 && (
        <div className="activity-log">
          <div className="activity-log-header">
            <span>Activity</span>
            <button
              type="button"
              className="activity-log-clear"
              onClick={() => setLogLines([])}
              aria-label="Clear log"
            >
              &times;
            </button>
          </div>
          <div className="activity-log-body">
            {logLines.map((line, i) => (
              <div key={i} className="activity-log-line">
                <span className="activity-log-icon">&#8250;</span> {line}
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        </div>
      )}

      {containers.length > 0 && (
        <table className="table table-striped table-sm">
          <thead>
            <tr>
              <th>Host ID</th>
              <th>Container</th>
              <th>Image</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {containers.map((c) => (
              <tr key={c.host_id}>
                <td>{c.host_id}</td>
                <td>
                  <code>{c.container}</code>
                </td>
                <td>
                  <code>{c.image}</code>
                </td>
                <td>
                  <span className={`badge badge-${c.status === 'running' ? 'success' : 'warning'}`}>
                    {c.status}
                  </span>
                </td>
                <td>
                  <button
                    type="button"
                    className="btn btn-outline-dark deploy-btn"
                    onClick={() =>
                      setTerminalContainer(terminalContainer === c.container ? null : c.container)
                    }
                    disabled={c.status !== 'running'}
                  >
                    <i className="fa fa-terminal" aria-hidden="true" />{' '}
                    {terminalContainer === c.container ? 'Close' : 'Terminal'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {terminalContainer && (
        <Terminal
          containerName={terminalContainer}
          token={token}
          onClose={() => setTerminalContainer(null)}
        />
      )}
    </div>
  )
}

export default DeployTab
