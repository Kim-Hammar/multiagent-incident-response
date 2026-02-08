import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../contexts/AuthContext.jsx'
import {
  API_DT_PYTHON_URL,
  API_DT_PYTHON_RUN_URL,
  API_DT_PYTHON_START_URL,
  API_DT_PYTHON_STOP_URL
} from '../Common/constants'

/**
 * Python sandbox management page with container status, start/stop controls, and code editor.
 */
function Python() {
  const { token, logout } = useAuth()

  const [alert, setAlert] = useState(null)
  const [containerStatus, setContainerStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState(false)
  const [stopping, setStopping] = useState(false)

  const [code, setCode] = useState('')
  const [isTest, setIsTest] = useState(false)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState(null)

  useEffect(() => {
    if (!alert) return
    const timer = setTimeout(() => setAlert(null), 3000)
    return () => clearTimeout(timer)
  }, [alert])

  const fetchStatus = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch(API_DT_PYTHON_URL, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.status === 401) {
        logout()
        return
      }
      const data = await response.json()
      setContainerStatus(data.container_status || null)
    } catch (err) {
      setAlert({ type: 'danger', message: `Failed to fetch status: ${err.message}` })
    } finally {
      setLoading(false)
    }
  }, [token, logout])

  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  const handleStart = async () => {
    setStarting(true)
    try {
      const response = await fetch(API_DT_PYTHON_START_URL, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.status === 401) {
        logout()
        return
      }
      const data = await response.json()
      if (!response.ok) {
        setAlert({ type: 'danger', message: data.error || 'Failed to start container' })
        return
      }
      setContainerStatus(data.container_status)
      setAlert({ type: 'success', message: 'Python sandbox started' })
    } catch (err) {
      setAlert({ type: 'danger', message: `Failed to start container: ${err.message}` })
    } finally {
      setStarting(false)
    }
  }

  const handleStop = async () => {
    setStopping(true)
    try {
      const response = await fetch(API_DT_PYTHON_STOP_URL, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.status === 401) {
        logout()
        return
      }
      const data = await response.json()
      if (!response.ok) {
        setAlert({ type: 'danger', message: data.error || 'Failed to stop container' })
        return
      }
      setContainerStatus(data.container_status)
      setAlert({ type: 'success', message: 'Python sandbox stopped' })
    } catch (err) {
      setAlert({ type: 'danger', message: `Failed to stop container: ${err.message}` })
    } finally {
      setStopping(false)
    }
  }

  const handleRun = async (e) => {
    e.preventDefault()
    if (!code.trim()) return
    setRunning(true)
    setResult(null)
    try {
      const response = await fetch(API_DT_PYTHON_RUN_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ code: code.trim(), test: isTest })
      })
      if (response.status === 401) {
        logout()
        return
      }
      const data = await response.json()
      if (!response.ok) {
        setAlert({ type: 'danger', message: data.error || `HTTP ${response.status}` })
        return
      }
      setResult(data)
    } catch (err) {
      setAlert({ type: 'danger', message: `Execution failed: ${err.message}` })
    } finally {
      setRunning(false)
    }
  }

  const statusBadge =
    containerStatus === 'running' ? (
      <span className="badge badge-success">running</span>
    ) : containerStatus === 'exited' ? (
      <span className="badge badge-warning">exited</span>
    ) : containerStatus === 'not_found' ? (
      <span className="badge badge-secondary">not found</span>
    ) : containerStatus === 'stopped' ? (
      <span className="badge badge-secondary">stopped</span>
    ) : null

  return (
    <div className="Python">
      <h2>Python sandbox</h2>
      <p className="subtitle">Manage the Python sandbox container and execute code.</p>
      <hr />

      {alert && (
        <div className={`alert alert-${alert.type} alert-dismissible fade show`} role="alert">
          {alert.message}
          <button type="button" className="close" onClick={() => setAlert(null)}>
            <span>&times;</span>
          </button>
        </div>
      )}

      <div className="card mb-3">
        <div className="card-header d-flex justify-content-between align-items-center">
          <strong>Container status</strong>
          {loading ? (
            <span className="spinner-border spinner-border-sm" role="status" />
          ) : (
            statusBadge
          )}
        </div>
        <div className="card-body">
          <button
            className="btn btn-sm btn-success mr-2"
            onClick={handleStart}
            disabled={starting || stopping}
          >
            {starting ? (
              <>
                <span className="spinner-border spinner-border-sm mr-1" role="status" />
                Starting...
              </>
            ) : (
              'Start'
            )}
          </button>
          <button
            className="btn btn-sm btn-danger mr-2"
            onClick={handleStop}
            disabled={starting || stopping}
          >
            {stopping ? (
              <>
                <span className="spinner-border spinner-border-sm mr-1" role="status" />
                Stopping...
              </>
            ) : (
              'Stop'
            )}
          </button>
          <button
            className="btn btn-sm btn-outline-secondary"
            onClick={fetchStatus}
            disabled={loading}
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <strong>Code editor</strong>
        </div>
        <div className="card-body">
          <form onSubmit={handleRun}>
            <div className="form-group">
              <textarea
                className="form-control"
                rows="10"
                placeholder="Enter Python code..."
                value={code}
                onChange={(e) => setCode(e.target.value)}
                style={{ fontFamily: 'monospace' }}
              />
            </div>
            <div className="form-row align-items-center">
              <div className="col-auto mb-2">
                <div className="form-check">
                  <input
                    className="form-check-input"
                    type="checkbox"
                    id="python-test-flag"
                    checked={isTest}
                    onChange={(e) => setIsTest(e.target.checked)}
                  />
                  <label className="form-check-label" htmlFor="python-test-flag">
                    Run as test (pytest)
                  </label>
                </div>
              </div>
              <div className="col-auto mb-2">
                <button
                  className="btn btn-sm btn-primary"
                  type="submit"
                  disabled={running || !code.trim()}
                >
                  {running ? (
                    <>
                      <span className="spinner-border spinner-border-sm mr-1" role="status" />
                      Running...
                    </>
                  ) : (
                    'Run'
                  )}
                </button>
              </div>
            </div>
          </form>

          {result && (
            <div className="mt-2">
              <p>
                <strong>Exit code:</strong>{' '}
                <span
                  className={`badge ${result.exit_code === 0 ? 'badge-success' : 'badge-danger'}`}
                >
                  {result.exit_code}
                </span>
                {result.test && <span className="badge badge-info ml-2">pytest</span>}
              </p>
              <pre className="bg-light p-2 border rounded" style={{ maxHeight: '300px' }}>
                {result.output}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Python
