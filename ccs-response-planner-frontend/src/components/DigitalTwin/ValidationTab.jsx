import { useState, useEffect, useCallback, useRef } from 'react'
import { API_DIGITAL_TWIN_VALIDATE_URL, API_DIGITAL_TWIN_STATUS_URL } from '../Common/constants'

/**
 * Validation tab for the digital twin.
 * Runs specification commands against the deployed DT and shows pass/fail results.
 */
function ValidationTab({ token, logout, specificationCommands }) {
  const [status, setStatus] = useState(null)
  const [validating, setValidating] = useState(false)
  const [logLines, setLogLines] = useState([])
  const [results, setResults] = useState([])
  const [lastTested, setLastTested] = useState(null)
  const intervalRef = useRef(null)
  const logEndRef = useRef(null)

  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch(API_DIGITAL_TWIN_STATUS_URL, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.status === 401) {
        logout()
        return
      }
      const data = await response.json()
      setStatus(data)
    } catch {
      /* polling failure is silent */
    }
  }, [token, logout])

  useEffect(() => {
    fetchStatus()
    intervalRef.current = setInterval(fetchStatus, 5000)
    return () => clearInterval(intervalRef.current)
  }, [fetchStatus])

  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logLines])

  const handleValidate = async () => {
    setValidating(true)
    setLogLines([])
    setResults([])
    try {
      const response = await fetch(API_DIGITAL_TWIN_VALIDATE_URL, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.status === 401) {
        logout()
        return
      }
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      const newResults = []
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()
        for (const line of lines) {
          if (!line.trim()) continue
          try {
            const parsed = JSON.parse(line)
            if (parsed.type === 'progress') {
              setLogLines((prev) => [...prev, parsed.message])
            } else if (parsed.type === 'result') {
              newResults.push(parsed)
              setResults([...newResults])
            } else if (parsed.type === 'error') {
              setLogLines((prev) => [...prev, `Error: ${parsed.message}`])
            } else if (parsed.type === 'done') {
              setLastTested(new Date())
            }
          } catch {
            /* skip malformed lines */
          }
        }
      }
    } catch {
      setLogLines((prev) => [...prev, 'Error: validation request failed'])
    } finally {
      setValidating(false)
    }
  }

  const deployed = status?.deployed || false

  if (status && !deployed) {
    return (
      <div className="validation-tab">
        <div className="alert alert-info" role="alert">
          The digital twin is not currently deployed. Switch to the <strong>Deployment</strong> tab
          to deploy it before running validation.
        </div>
      </div>
    )
  }

  const passCount = results.filter((r) => r.passed).length
  const failCount = results.filter((r) => !r.passed).length

  return (
    <div className="validation-tab">
      <div className="deploy-controls">
        <button
          type="button"
          className="btn btn-dark deploy-btn"
          onClick={handleValidate}
          disabled={validating}
        >
          {validating ? (
            <>
              <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />{' '}
              Validating...
            </>
          ) : (
            <>
              <i className="fa fa-check-circle" aria-hidden="true" /> Run validation
            </>
          )}
        </button>
        <span className={`badge badge-${deployed ? 'success' : 'secondary'} deploy-badge`}>
          {deployed ? 'Deployed' : 'Not deployed'}
        </span>
      </div>

      <div className="last-tested">
        {lastTested ? `Last tested: ${lastTested.toLocaleTimeString()}` : 'Not yet tested'}
      </div>

      {logLines.length > 0 && (
        <div className="activity-log">
          <div className="activity-log-header">
            <span>Activity</span>
            <button
              type="button"
              className="activity-log-clear"
              onClick={() => setLogLines([])}
              aria-label="Clear log"
            >
              &times;
            </button>
          </div>
          <div className="activity-log-body">
            {logLines.map((line, i) => (
              <div key={i} className="activity-log-line">
                <span className="activity-log-icon">&#8250;</span> {line}
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        </div>
      )}

      {results.length > 0 && (
        <>
          <div style={{ marginBottom: 8, fontSize: 13 }}>
            <span className="badge badge-success" style={{ marginRight: 6 }}>
              {passCount} passed
            </span>
            <span className="badge badge-danger">{failCount} failed</span>
          </div>
          <table className="table table-striped table-sm">
            <thead>
              <tr>
                <th>#</th>
                <th>Host</th>
                <th>Description</th>
                <th>Command</th>
                <th>Status</th>
                <th>Output</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r, i) => (
                <tr key={i}>
                  <td>{i + 1}</td>
                  <td>{r.host}</td>
                  <td>{r.description}</td>
                  <td>
                    <code>{r.command}</code>
                  </td>
                  <td>
                    <span className={`badge badge-${r.passed ? 'success' : 'danger'}`}>
                      {r.passed ? 'PASS' : 'FAIL'}
                    </span>
                  </td>
                  <td className="output-cell">
                    <code>{r.output}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {!validating && results.length === 0 && specificationCommands.length > 0 && (
        <p style={{ fontSize: 13, color: '#6c757d' }}>
          {specificationCommands.length} specification command
          {specificationCommands.length !== 1 ? 's' : ''} configured. Click{' '}
          <strong>Run validation</strong> to test them.
        </p>
      )}
    </div>
  )
}

export default ValidationTab
