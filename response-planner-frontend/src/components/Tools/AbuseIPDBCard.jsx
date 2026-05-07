import { useState, useEffect, useCallback } from 'react'
import { API_ABUSEIPDB_URL, API_ABUSEIPDB_CHECK_URL } from '../Common/constants'

function formatTimestamp(iso) {
  const d = new Date(iso)
  const year = d.getFullYear()
  const month = d.toLocaleString('en-US', { month: 'short' })
  const day = String(d.getDate()).padStart(2, '0')
  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

function AbuseIPDBCard({ token, logout, setAlert }) {
  const [connStatus, setConnStatus] = useState('pending')
  const [connData, setConnData] = useState(null)
  const [connError, setConnError] = useState(null)

  const [ip, setIp] = useState('')
  const [checking, setChecking] = useState(false)
  const [checkResult, setCheckResult] = useState(null)
  const [checkError, setCheckError] = useState(null)

  const testConnection = useCallback(async () => {
    setConnStatus('pending')
    setConnData(null)
    setConnError(null)
    try {
      const response = await fetch(API_ABUSEIPDB_URL, {
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
        setAlert({ type: 'success', message: 'AbuseIPDB connection successful' })
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

  const handleCheck = async (e) => {
    e.preventDefault()
    if (!ip.trim()) return
    setChecking(true)
    setCheckResult(null)
    setCheckError(null)
    try {
      const response = await fetch(API_ABUSEIPDB_CHECK_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ ip: ip.trim() })
      })
      if (response.status === 401) {
        logout()
        return
      }
      const json = await response.json()
      if (!response.ok) {
        setCheckError(json.error || `HTTP ${response.status}`)
        return
      }
      setCheckResult(json.result)
    } catch (err) {
      setCheckError(err.message)
    } finally {
      setChecking(false)
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
        <strong>AbuseIPDB</strong>
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
            <strong>Last tested:</strong> {formatTimestamp(connData.timestamp)}
          </p>
        )}

        {connStatus === 'error' && (
          <>
            {connError && <p className="text-danger">{connError}</p>}
            {connData && connData.timestamp && (
              <p>
                <strong>Last tested:</strong> {formatTimestamp(connData.timestamp)}
              </p>
            )}
          </>
        )}

        <button className="btn btn-sm btn-outline-secondary" onClick={testConnection}>
          Test connection
        </button>

        <hr />

        <form className="search-form" onSubmit={handleCheck}>
          <div className="input-group">
            <input
              type="text"
              className="form-control"
              placeholder="IP address (e.g. 1.2.3.4)"
              value={ip}
              onChange={(e) => setIp(e.target.value)}
            />
            <div className="input-group-append">
              <button
                className="btn btn-sm btn-primary"
                type="submit"
                disabled={checking || !ip.trim()}
              >
                {checking ? (
                  <>
                    <span className="spinner-border spinner-border-sm mr-1" role="status" />
                    Checking...
                  </>
                ) : (
                  'Check'
                )}
              </button>
            </div>
          </div>
        </form>

        {checkError && <p className="text-danger mt-2">{checkError}</p>}

        {checkResult && (
          <div className="table-responsive results-table">
            <table className="table table-sm table-striped">
              <thead>
                <tr>
                  <th>IP</th>
                  <th>Abuse Score</th>
                  <th>ISP</th>
                  <th>Country</th>
                  <th>Reports</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>{checkResult.ip}</td>
                  <td>{checkResult.abuse_confidence_score}</td>
                  <td>{checkResult.isp}</td>
                  <td>{checkResult.country_code}</td>
                  <td>{checkResult.total_reports}</td>
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default AbuseIPDBCard
