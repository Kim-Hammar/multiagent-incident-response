import './LLM.css'
import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../contexts/AuthContext.jsx'
import { API_LLM_URL } from '../Common/constants'

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
 * LLM status page that tests the connection to the Gemini API
 * and displays available model information.
 */
function Llm() {
  const { token, logout } = useAuth()
  const [status, setStatus] = useState('pending')
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  const testConnection = useCallback(async () => {
    setStatus('pending')
    setData(null)
    setError(null)
    try {
      const response = await fetch(API_LLM_URL, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.status === 401) {
        logout()
        return
      }
      if (!response.ok) {
        setStatus('error')
        setError(`HTTP ${response.status}`)
        return
      }
      const json = await response.json()
      if (json.status === 'connected') {
        setStatus('connected')
        setData(json)
      } else {
        setStatus('error')
        setError(json.error || 'Unknown error')
        setData(json)
      }
    } catch (err) {
      setStatus('error')
      setError(err.message)
    }
  }, [token])

  useEffect(() => {
    testConnection()
  }, [testConnection])

  return (
    <div className="Llm">
      <h2>LLM Status</h2>
      <hr />

      {status === 'pending' && (
        <p>
          <span className="spinner-border spinner-border-sm mr-2" role="status" />
          Testing connection...
        </p>
      )}

      {status === 'connected' && (
        <>
          <p>
            <span className="badge badge-success">Connected</span>
          </p>
          {data && (
            <>
              <p>
                <strong>Last tested:</strong> {formatTimestamp(data.timestamp)}
              </p>
              {data.models && data.models.length > 0 && (
                <table className="table table-striped table-sm">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Description</th>
                      <th>Input token limit</th>
                      <th>Output token limit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.models.map((m) => (
                      <tr key={m.name}>
                        <td>{m.display_name}</td>
                        <td>{m.description}</td>
                        <td>{m.input_token_limit?.toLocaleString()}</td>
                        <td>{m.output_token_limit?.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </>
          )}
        </>
      )}

      {status === 'error' && (
        <>
          <p>
            <span className="badge badge-danger">Not connected</span>
          </p>
          {error && <p className="text-danger">{error}</p>}
          {data && data.timestamp && (
            <p>
              <strong>Last tested:</strong> {formatTimestamp(data.timestamp)}
            </p>
          )}
        </>
      )}

      <button className="btn btn-sm btn-outline-secondary mt-3" onClick={testConnection}>
        Test connection
      </button>
    </div>
  )
}

export default Llm
