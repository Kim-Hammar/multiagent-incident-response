import './Tools.css'
import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../contexts/AuthContext.jsx'
import { API_TAVILY_URL, API_TAVILY_SEARCH_URL } from '../Common/constants'

function formatTimestamp(iso) {
  const d = new Date(iso)
  const year = d.getFullYear()
  const month = d.toLocaleString('en-US', { month: 'short' })
  const day = String(d.getDate()).padStart(2, '0')
  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

/**
 * Tools page listing all connected external tools.
 */
function Tools() {
  const { token, logout } = useAuth()

  const [connStatus, setConnStatus] = useState('pending')
  const [connData, setConnData] = useState(null)
  const [connError, setConnError] = useState(null)

  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [searchResults, setSearchResults] = useState(null)
  const [searchError, setSearchError] = useState(null)
  const [searchTime, setSearchTime] = useState(null)

  const [alert, setAlert] = useState(null)

  useEffect(() => {
    if (!alert) return
    const timer = setTimeout(() => setAlert(null), 3000)
    return () => clearTimeout(timer)
  }, [alert])

  const testConnection = useCallback(async () => {
    setConnStatus('pending')
    setConnData(null)
    setConnError(null)
    try {
      const response = await fetch(API_TAVILY_URL, {
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
        setAlert({ type: 'success', message: 'Tavily connection successful' })
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

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return
    setSearching(true)
    setSearchResults(null)
    setSearchError(null)
    setSearchTime(null)
    try {
      const response = await fetch(API_TAVILY_SEARCH_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ query: query.trim(), max_results: 5 })
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
      setSearchResults(json.results)
      setSearchTime(json.response_time)
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
    <div className="Tools">
      <h2>Tools</h2>
      <hr />

      {alert && (
        <div className={`alert alert-${alert.type} alert-dismissible fade show`} role="alert">
          {alert.message}
          <button type="button" className="close" onClick={() => setAlert(null)}>
            <span>&times;</span>
          </button>
        </div>
      )}

      <div className="card">
        <div className="card-header d-flex justify-content-between align-items-center">
          <strong>Tavily Search API</strong>
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
            <>
              <p>
                <strong>Last tested:</strong> {formatTimestamp(connData.timestamp)}
              </p>
              {connData.response_time != null && (
                <p>
                  <strong>Response time:</strong> {connData.response_time.toFixed(2)}s
                </p>
              )}
            </>
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
            <div className="input-group">
              <input
                type="text"
                className="form-control"
                placeholder="Search query..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <div className="input-group-append">
                <button
                  className="btn btn-primary"
                  type="submit"
                  disabled={searching || !query.trim()}
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

          {searchResults && (
            <>
              {searchTime != null && (
                <p className="mt-2 text-muted">
                  {searchResults.length} result(s) in {searchTime.toFixed(2)}s
                </p>
              )}
              {searchResults.length === 0 ? (
                <p className="mt-2">No results found.</p>
              ) : (
                <div className="table-responsive results-table">
                  <table className="table table-sm table-striped">
                    <thead>
                      <tr>
                        <th>Title</th>
                        <th>URL</th>
                        <th>Snippet</th>
                      </tr>
                    </thead>
                    <tbody>
                      {searchResults.map((r, i) => (
                        <tr key={i}>
                          <td>
                            <a href={r.url} target="_blank" rel="noopener noreferrer">
                              {r.title}
                            </a>
                          </td>
                          <td>
                            <small>{r.url}</small>
                          </td>
                          <td className="snippet">{r.content}</td>
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
    </div>
  )
}

export default Tools
