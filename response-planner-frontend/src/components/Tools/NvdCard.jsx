import { useState, useEffect, useCallback } from 'react'
import { API_NVD_URL, API_NVD_SEARCH_URL } from '../Common/constants'

function formatTimestamp(iso) {
  const d = new Date(iso)
  const year = d.getFullYear()
  const month = d.toLocaleString('en-US', { month: 'short' })
  const day = String(d.getDate()).padStart(2, '0')
  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

function NvdCard({ token, logout, setAlert }) {
  const [connStatus, setConnStatus] = useState('pending')
  const [connData, setConnData] = useState(null)
  const [connError, setConnError] = useState(null)

  const [cveId, setCveId] = useState('')
  const [keyword, setKeyword] = useState('')
  const [searching, setSearching] = useState(false)
  const [searchResults, setSearchResults] = useState(null)
  const [searchError, setSearchError] = useState(null)

  const testConnection = useCallback(async () => {
    setConnStatus('pending')
    setConnData(null)
    setConnError(null)
    try {
      const response = await fetch(API_NVD_URL, {
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
        setAlert({ type: 'success', message: 'NVD connection successful' })
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
    if (!cveId.trim() && !keyword.trim()) return
    setSearching(true)
    setSearchResults(null)
    setSearchError(null)
    try {
      const body = {}
      if (cveId.trim()) body.cve_id = cveId.trim()
      else body.keyword = keyword.trim()
      const response = await fetch(API_NVD_SEARCH_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(body)
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
        <strong>NVD / CVE Database</strong>
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
            <div className="col-md-5 mb-2">
              <input
                type="text"
                className="form-control"
                placeholder="CVE ID (e.g. CVE-2021-44228)"
                value={cveId}
                onChange={(e) => setCveId(e.target.value)}
              />
            </div>
            <div className="col-md-5 mb-2">
              <input
                type="text"
                className="form-control"
                placeholder="Keyword search..."
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
              />
            </div>
            <div className="col-md-2 mb-2">
              <button
                className="btn btn-sm btn-primary btn-block"
                type="submit"
                disabled={searching || (!cveId.trim() && !keyword.trim())}
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
            {searchResults.length === 0 ? (
              <p className="mt-2">No results found.</p>
            ) : (
              <div className="table-responsive results-table">
                <table className="table table-sm table-striped">
                  <thead>
                    <tr>
                      <th>CVE ID</th>
                      <th>Description</th>
                      <th>CVSS Score</th>
                      <th>Published</th>
                    </tr>
                  </thead>
                  <tbody>
                    {searchResults.map((r, i) => (
                      <tr key={i}>
                        <td>
                          <a href={r.url} target="_blank" rel="noopener noreferrer">
                            {r.id}
                          </a>
                        </td>
                        <td className="snippet">{r.description}</td>
                        <td>{r.score != null ? r.score : 'N/A'}</td>
                        <td>{r.published}</td>
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

export default NvdCard
