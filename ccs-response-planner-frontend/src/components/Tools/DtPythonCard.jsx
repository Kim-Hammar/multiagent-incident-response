import { useState, useEffect, useCallback } from 'react'
import { API_DT_PYTHON_URL, API_DT_PYTHON_RUN_URL } from '../Common/constants'

/**
 * Small status card for the Python sandbox on the Tools page.
 */
function DtPythonCard({ token, logout }) {
  const [connStatus, setConnStatus] = useState('pending')
  const [connData, setConnData] = useState(null)
  const [connError, setConnError] = useState(null)

  const [code, setCode] = useState('')
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState(null)
  const [runError, setRunError] = useState(null)

  const testConnection = useCallback(async () => {
    setConnStatus('pending')
    setConnData(null)
    setConnError(null)
    try {
      const response = await fetch(API_DT_PYTHON_URL, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.status === 401) {
        logout()
        return
      }
      if (!response.ok) {
        setConnStatus('error')
        setConnError(`HTTP ${response.status}`)
        return
      }
      const json = await response.json()
      if (json.status === 'connected') {
        setConnStatus('connected')
        setConnData(json)
      } else {
        setConnStatus('error')
        setConnError(json.error || 'Unknown error')
        setConnData(json)
      }
    } catch (err) {
      setConnStatus('error')
      setConnError(err.message)
    }
  }, [token, logout])

  useEffect(() => {
    testConnection()
  }, [testConnection])

  const handleRun = async (e) => {
    e.preventDefault()
    if (!code.trim()) return
    setRunning(true)
    setResult(null)
    setRunError(null)
    try {
      const response = await fetch(API_DT_PYTHON_RUN_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ code: code.trim() })
      })
      if (response.status === 401) {
        logout()
        return
      }
      const json = await response.json()
      if (!response.ok) {
        setRunError(json.error || `HTTP ${response.status}`)
        return
      }
      setResult(json)
    } catch (err) {
      setRunError(err.message)
    } finally {
      setRunning(false)
    }
  }

  const statusBadge =
    connStatus === 'connected' ? (
      <span className="badge badge-success">Connected</span>
    ) : connStatus === 'error' ? (
      <span className="badge badge-danger">Error</span>
    ) : (
      <span className="badge badge-secondary">Pending</span>
    )

  return (
    <div className="card">
      <div className="card-header d-flex justify-content-between align-items-center">
        <strong>DT Python Sandbox</strong>
        {statusBadge}
      </div>
      <div className="card-body">
        {connStatus === 'pending' && (
          <p>
            <span className="spinner-border spinner-border-sm mr-2" role="status" />
            Testing connection...
          </p>
        )}

        {connStatus === 'connected' && connData && (
          <p>
            <strong>Container status:</strong> {connData.container_status}
          </p>
        )}

        {connStatus === 'error' && connError && <p className="text-danger">{connError}</p>}

        <button className="btn btn-sm btn-outline-secondary" onClick={testConnection}>
          Test connection
        </button>

        <hr />

        <form onSubmit={handleRun}>
          <div className="input-group">
            <input
              type="text"
              className="form-control"
              placeholder="Python one-liner, e.g. print(2+2)"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              style={{ fontFamily: 'monospace' }}
            />
            <div className="input-group-append">
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

        {runError && <p className="text-danger mt-2">{runError}</p>}

        {result && (
          <div className="mt-2">
            <p>
              <strong>Exit code:</strong>{' '}
              <span
                className={`badge ${result.exit_code === 0 ? 'badge-success' : 'badge-danger'}`}
              >
                {result.exit_code}
              </span>
            </p>
            <pre className="bg-light p-2 border rounded" style={{ maxHeight: '150px' }}>
              {result.output}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}

export default DtPythonCard
