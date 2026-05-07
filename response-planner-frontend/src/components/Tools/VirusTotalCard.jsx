import { useState, useEffect, useCallback } from 'react'
import { API_VIRUSTOTAL_URL, API_VIRUSTOTAL_SCAN_URL } from '../Common/constants'

function formatTimestamp(iso) {
  const d = new Date(iso)
  const year = d.getFullYear()
  const month = d.toLocaleString('en-US', { month: 'short' })
  const day = String(d.getDate()).padStart(2, '0')
  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

function VirusTotalCard({ token, logout, setAlert }) {
  const [connStatus, setConnStatus] = useState('pending')
  const [connData, setConnData] = useState(null)
  const [connError, setConnError] = useState(null)

  const [scanType, setScanType] = useState('ip')
  const [scanValue, setScanValue] = useState('')
  const [scanning, setScanning] = useState(false)
  const [scanResult, setScanResult] = useState(null)
  const [scanError, setScanError] = useState(null)

  const testConnection = useCallback(async () => {
    setConnStatus('pending')
    setConnData(null)
    setConnError(null)
    try {
      const response = await fetch(API_VIRUSTOTAL_URL, {
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
        setAlert({ type: 'success', message: 'VirusTotal connection successful' })
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

  const handleScan = async (e) => {
    e.preventDefault()
    if (!scanValue.trim()) return
    setScanning(true)
    setScanResult(null)
    setScanError(null)
    try {
      const response = await fetch(API_VIRUSTOTAL_SCAN_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ type: scanType, value: scanValue.trim() })
      })
      if (response.status === 401) {
        logout()
        return
      }
      const json = await response.json()
      if (!response.ok) {
        setScanError(json.error || `HTTP ${response.status}`)
        return
      }
      setScanResult(json.result)
    } catch (err) {
      setScanError(err.message)
    } finally {
      setScanning(false)
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
        <strong>VirusTotal</strong>
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

        <form className="search-form" onSubmit={handleScan}>
          <div className="form-row">
            <div className="col-md-3 mb-2">
              <select
                className="form-control"
                value={scanType}
                onChange={(e) => setScanType(e.target.value)}
              >
                <option value="ip">IP Address</option>
                <option value="domain">Domain</option>
                <option value="url">URL</option>
                <option value="hash">File Hash</option>
              </select>
            </div>
            <div className="col-md-7 mb-2">
              <input
                type="text"
                className="form-control"
                placeholder="Enter value to scan..."
                value={scanValue}
                onChange={(e) => setScanValue(e.target.value)}
              />
            </div>
            <div className="col-md-2 mb-2">
              <button
                className="btn btn-sm btn-primary btn-block"
                type="submit"
                disabled={scanning || !scanValue.trim()}
              >
                {scanning ? (
                  <>
                    <span className="spinner-border spinner-border-sm mr-1" role="status" />
                    Scanning...
                  </>
                ) : (
                  'Scan'
                )}
              </button>
            </div>
          </div>
        </form>

        {scanError && <p className="text-danger mt-2">{scanError}</p>}

        {scanResult && (
          <div className="table-responsive results-table">
            <table className="table table-sm table-striped">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Value</th>
                  <th>Reputation</th>
                  <th>Detection Stats</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>{scanResult.type}</td>
                  <td>{scanResult.value}</td>
                  <td>{scanResult.reputation != null ? scanResult.reputation : 'N/A'}</td>
                  <td>
                    {scanResult.last_analysis_stats
                      ? Object.entries(scanResult.last_analysis_stats)
                          .map(([k, v]) => `${k}: ${v}`)
                          .join(', ')
                      : 'N/A'}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default VirusTotalCard
