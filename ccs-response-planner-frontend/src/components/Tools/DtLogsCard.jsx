import { useState, useEffect, useCallback } from 'react'
import { API_DT_LOGS_URL, API_DT_LOGS_FETCH_URL } from '../Common/constants'

const HOST_IDS = [
  'gateway',
  'firewall',
  'ids',
  'server_1',
  'server_2',
  'server_3',
  'server_4',
  'server_5',
  'server_6'
]

function DtLogsCard({ token, logout, setAlert }) {
  const [connStatus, setConnStatus] = useState('pending')
  const [connData, setConnData] = useState(null)
  const [connError, setConnError] = useState(null)

  const [container, setContainer] = useState(HOST_IDS[0])
  const [tail, setTail] = useState(100)
  const [fetching, setFetching] = useState(false)
  const [result, setResult] = useState(null)
  const [fetchError, setFetchError] = useState(null)

  const testConnection = useCallback(async () => {
    setConnStatus('pending')
    setConnData(null)
    setConnError(null)
    try {
      const response = await fetch(API_DT_LOGS_URL, {
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
        setAlert({ type: 'success', message: 'DT Logs connection successful' })
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

  const handleFetch = async (e) => {
    e.preventDefault()
    setFetching(true)
    setResult(null)
    setFetchError(null)
    try {
      const response = await fetch(API_DT_LOGS_FETCH_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ container, tail: Number(tail) })
      })
      if (response.status === 401) {
        logout()
        return
      }
      const json = await response.json()
      if (!response.ok) {
        setFetchError(json.error || `HTTP ${response.status}`)
        return
      }
      setResult(json)
    } catch (err) {
      setFetchError(err.message)
    } finally {
      setFetching(false)
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
        <strong>DT Container Logs</strong>
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
            <strong>Running containers:</strong> {connData.count}
          </p>
        )}

        {connStatus === 'error' && connError && <p className="text-danger">{connError}</p>}

        <button className="btn btn-sm btn-outline-secondary" onClick={testConnection}>
          Test connection
        </button>

        <hr />

        <form className="search-form" onSubmit={handleFetch}>
          <div className="form-row">
            <div className="col-md-3 mb-2">
              <select
                className="form-control"
                value={container}
                onChange={(e) => setContainer(e.target.value)}
              >
                {HOST_IDS.map((id) => (
                  <option key={id} value={id}>
                    {id}
                  </option>
                ))}
              </select>
            </div>
            <div className="col-md-3 mb-2">
              <input
                type="number"
                className="form-control"
                placeholder="Tail lines"
                value={tail}
                min="1"
                onChange={(e) => setTail(e.target.value)}
              />
            </div>
            <div className="col-md-2 mb-2">
              <button
                className="btn btn-sm btn-primary btn-block"
                type="submit"
                disabled={fetching}
              >
                {fetching ? (
                  <>
                    <span className="spinner-border spinner-border-sm mr-1" role="status" />
                    Fetching...
                  </>
                ) : (
                  'Fetch'
                )}
              </button>
            </div>
          </div>
        </form>

        {fetchError && <p className="text-danger mt-2">{fetchError}</p>}

        {result && (
          <div className="mt-2">
            <p>
              <strong>Lines:</strong> {result.lines}
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

export default DtLogsCard
