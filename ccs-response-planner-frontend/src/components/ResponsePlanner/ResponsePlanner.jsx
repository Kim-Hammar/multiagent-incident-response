import { useState } from 'react'
import { API_EXAMPLE_URL } from '../Common/constants'
import { useAuth } from '../../contexts/AuthContext.jsx'
import './ResponsePlanner.css'

/**
 * The response planner page component
 */
function ResponsePlanner() {
  const [systemDescription, setSystemDescription] = useState('')
  const [securityAlerts, setSecurityAlerts] = useState('')
  const [operatorFeedback, setOperatorFeedback] = useState('')
  const { token, logout } = useAuth()

  const fetchExample = async () => {
    const res = await fetch(API_EXAMPLE_URL, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (res.status === 401) {
      logout()
      return
    }
    const data = await res.json()
    setSystemDescription(data.system_description)
    setSecurityAlerts(data.security_alerts)
    setOperatorFeedback(data.operator_feedback)
  }

  return (
    <div className="ResponsePlanner">
      <h2>Response planner</h2>
      <p className="subtitle">
        Provide system details, security alerts, and operator feedback to generate an incident
        response plan.
      </p>
      <hr />
      <form>
        <div className="input-section">
          <label htmlFor="systemDescription">System description</label>
          <p className="input-hint">
            Describe the target system, its architecture, hosts, and services.
          </p>
          <textarea
            className="form-control planner-textarea"
            id="systemDescription"
            rows="8"
            placeholder="e.g., The system consists of a web server (Apache on 10.0.0.1), a database server (PostgreSQL on 10.0.0.2), and a firewall..."
            value={systemDescription}
            onChange={(e) => setSystemDescription(e.target.value)}
          />
        </div>
        <div className="input-section">
          <label htmlFor="securityAlerts">Security alerts and logs</label>
          <p className="input-hint">
            Paste relevant security alerts, IDS logs, or other indicators of compromise.
          </p>
          <textarea
            className="form-control planner-textarea"
            id="securityAlerts"
            rows="8"
            placeholder="e.g., [ALERT] Brute-force SSH login detected on 10.0.0.1 from 192.168.1.50 (200 attempts in 5 min)..."
            value={securityAlerts}
            onChange={(e) => setSecurityAlerts(e.target.value)}
          />
        </div>
        <div className="input-section">
          <label htmlFor="operatorFeedback">Operator feedback</label>
          <p className="input-hint">
            Optionally provide feedback to refine a previously generated plan.
          </p>
          <textarea
            className="form-control planner-textarea"
            id="operatorFeedback"
            rows="6"
            placeholder="e.g., The proposed isolation of 10.0.0.1 is not feasible because it hosts a critical customer-facing service..."
            value={operatorFeedback}
            onChange={(e) => setOperatorFeedback(e.target.value)}
          />
        </div>
        <button type="submit" className="btn btn-dark btn-sm btn-generate">
          <i className="fa fa-bolt" aria-hidden="true" /> Generate plan
        </button>
        <button
          type="button"
          className="btn btn-outline-dark btn-sm btn-example"
          onClick={fetchExample}
        >
          <i className="fa fa-download" aria-hidden="true" /> Fetch example incident
        </button>
        <button
          type="button"
          className="btn btn-outline-secondary btn-sm btn-clear"
          onClick={() => {
            setSystemDescription('')
            setSecurityAlerts('')
            setOperatorFeedback('')
          }}
        >
          <i className="fa fa-eraser" aria-hidden="true" /> Clear all
        </button>
      </form>
    </div>
  )
}

export default ResponsePlanner
