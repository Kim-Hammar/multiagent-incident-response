import { useState, useEffect, useCallback } from 'react'
import { API_DT_PYTHON_URL, API_DT_PYTHON_RUN_URL } from '../Common/constants'

function DtPythonCard({ token, logout, setAlert }) {
  const [connStatus, setConnStatus] = useState('pending')
  const [connData, setConnData] = useState(null)
  const [connError, setConnError] = useState(null)

  const [code, setCode] = useState('')
  const [isTest, setIsTest] = useState(false)
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
        setAlert({ type: 'success', message: 'DT Python Sandbox connection successful' })
      } else {
        setConnStatus('error')
        setConnError(json.error || 'Unknown error')
        setConnData(json)
      }
    } catch (err) {
      setConnStatus('error')
      setConnError(err.message)
    }
  }, [token, logout, setAlert])

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
        body: JSON.stringify({ code: code.trim(), test: isTest })
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

        <form className="search-form" onSubmit={handleRun}>
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
                  id="dt-python-test-flag"
                  checked={isTest}
                  onChange={(e) => setIsTest(e.target.checked)}
                />
                <label className="form-check-label" htmlFor="dt-python-test-flag">
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
              {result.test && <span className="badge badge-info ml-2">pytest</span>}
            </p>
            <pre className="bg-light p-2 border rounded" style={{ maxHeight: '300px' }}>
              {result.output}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}

export default DtPythonCard
