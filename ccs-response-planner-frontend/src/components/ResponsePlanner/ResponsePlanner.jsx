import './ResponsePlanner.css'

/**
 * The response planner page component
 */
function ResponsePlanner() {
  return (
    <div className="ResponsePlanner">
      <h2>Response planner</h2>
      <p className="subtitle">
        Provide system details, security alerts, and operator feedback to
        generate an incident response plan.
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
            rows="4"
            placeholder="e.g., The system consists of a web server (Apache on 10.0.0.1), a database server (PostgreSQL on 10.0.0.2), and a firewall..."
          />
        </div>
        <div className="input-section">
          <label htmlFor="securityAlerts">Security alerts and logs</label>
          <p className="input-hint">
            Paste relevant security alerts, IDS logs, or other indicators of
            compromise.
          </p>
          <textarea
            className="form-control planner-textarea"
            id="securityAlerts"
            rows="4"
            placeholder="e.g., [ALERT] Brute-force SSH login detected on 10.0.0.1 from 192.168.1.50 (200 attempts in 5 min)..."
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
            rows="3"
            placeholder="e.g., The proposed isolation of 10.0.0.1 is not feasible because it hosts a critical customer-facing service..."
          />
        </div>
        <button type="submit" className="btn btn-dark btn-sm btn-generate">
          <i className="fa fa-bolt" aria-hidden="true" /> Generate plan
        </button>
      </form>
    </div>
  )
}

export default ResponsePlanner
