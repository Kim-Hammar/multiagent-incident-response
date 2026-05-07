import { useState, useEffect, useCallback } from 'react'
import { API_OTX_URL, API_OTX_SEARCH_URL } from '../Common/constants'

function formatTimestamp(iso) {
  const d = new Date(iso)
  const year = d.getFullYear()
  const month = d.toLocaleString('en-US', { month: 'short' })
  const day = String(d.getDate()).padStart(2, '0')
  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

function OtxCard({ token, logout, setAlert }) {
  const [connStatus, setConnStatus] = useState('pending')
  const [connData, setConnData] = useState(null)
  const [connError, setConnError] = useState(null)

  const [indicatorType, setIndicatorType] = useState('IPv4')
  const [value, setValue] = useState('')
  const [searching, setSearching] = useState(false)
  const [searchResult, setSearchResult] = useState(null)
  const [searchError, setSearchError] = useState(null)

  const testConnection = useCallback(async () => {
    setConnStatus('pending')
    setConnData(null)
    setConnError(null)
    try {
      const response = await fetch(API_OTX_URL, {
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
        setAlert({ type: 'success', message: 'OTX connection successful' })
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

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!value.trim()) return
    setSearching(true)
    setSearchResult(null)
    setSearchError(null)
    try {
      const response = await fetch(API_OTX_SEARCH_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ type: indicatorType, value: value.trim() })
      })
      if (response.status === 401) {
        logout()
        return
      }
      const json = await response.json()
      if (!response.ok) {
        setSearchError(json.error || `HTTP ${response.status}`)
        return
      }
      setSearchResult(json.result)
    } catch (err) {
      setSearchError(err.message)
    } finally {
      setSearching(false)
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
        <strong>AlienVault OTX</strong>
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

        <form className="search-form" onSubmit={handleSearch}>
          <div className="form-row">
            <div className="col-md-3 mb-2">
              <select
                className="form-control"
                value={indicatorType}
                onChange={(e) => setIndicatorType(e.target.value)}
              >
                <option value="IPv4">IPv4</option>
                <option value="IPv6">IPv6</option>
                <option value="domain">Domain</option>
                <option value="hostname">Hostname</option>
                <option value="url">URL</option>
                <option value="hash">File Hash (SHA256)</option>
                <option value="cve">CVE</option>
              </select>
            </div>
            <div className="col-md-7 mb-2">
              <input
                type="text"
                className="form-control"
                placeholder="Enter indicator value..."
                value={value}
                onChange={(e) => setValue(e.target.value)}
              />
            </div>
            <div className="col-md-2 mb-2">
              <button
                className="btn btn-sm btn-primary btn-block"
                type="submit"
                disabled={searching || !value.trim()}
              >
                {searching ? (
                  <>
                    <span className="spinner-border spinner-border-sm mr-1" role="status" />
                    Searching...
                  </>
                ) : (
                  'Search'
                )}
              </button>
            </div>
          </div>
        </form>

        {searchError && <p className="text-danger mt-2">{searchError}</p>}

        {searchResult && (
          <>
            <p className="mt-2">
              <strong>Pulses:</strong> {searchResult.pulse_count}
              {searchResult.reputation != null && (
                <>
                  {' | '}
                  <strong>Reputation:</strong> {searchResult.reputation}
                </>
              )}
            </p>
            {searchResult.pulses && searchResult.pulses.length > 0 && (
              <div className="table-responsive results-table">
                <table className="table table-sm table-striped">
                  <thead>
                    <tr>
                      <th>Pulse Name</th>
                      <th>Description</th>
                      <th>Created</th>
                      <th>Tags</th>
                    </tr>
                  </thead>
                  <tbody>
                    {searchResult.pulses.map((p, i) => (
                      <tr key={i}>
                        <td>{p.name}</td>
                        <td className="snippet">{p.description}</td>
                        <td>{p.created}</td>
                        <td>{(p.tags || []).join(', ')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default OtxCard
