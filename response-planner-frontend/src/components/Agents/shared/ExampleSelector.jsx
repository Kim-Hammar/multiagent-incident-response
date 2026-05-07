import { useState, useEffect } from 'react'
import { useAuth } from '../../../contexts/AuthContext.jsx'
import { API_EXAMPLES_URL } from '../../Common/constants'

/**
 * Dropdown + Load button for selecting an example incident.
 */
function ExampleSelector({ onLoad, disabled }) {
  const { token } = useAuth()
  const [examples, setExamples] = useState([])
  const [selectedId, setSelectedId] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetch(API_EXAMPLES_URL, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => setExamples(data))
      .catch(() => {})
  }, [token])

  const handleLoad = async () => {
    setLoading(true)
    try {
      await onLoad(selectedId)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <select
        className="form-control form-control-sm ia-model-select"
        value={selectedId}
        onChange={(e) => setSelectedId(e.target.value)}
        disabled={disabled || loading}
        style={{ width: '180px', display: 'inline-block', marginRight: '4px' }}
      >
        <option value="">Select an incident...</option>
        {examples.map((ex) => (
          <option key={ex.id} value={ex.id}>
            {ex.name}
          </option>
        ))}
      </select>
      <button
        type="button"
        className="btn btn-outline-dark btn-sm ia-btn"
        onClick={handleLoad}
        disabled={!selectedId || disabled || loading}
      >
        {loading ? (
          <i className="fa fa-spinner fa-spin" aria-hidden="true" />
        ) : (
          <i className="fa fa-download" aria-hidden="true" />
        )}
        {loading ? ' Loading...' : ' Load example'}
      </button>
    </>
  )
}

export default ExampleSelector
