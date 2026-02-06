import './ResponsePlanner.css'

/**
 * The response planner page component
 */
function ResponsePlanner() {
  return (
    <div className="ResponsePlanner">
      <h2>Response Planner</h2>
      <p className="text-muted mb-4">
        Describe a cyber-security incident to generate a response plan.
      </p>
      <form>
        <div className="form-group mb-3">
          <label htmlFor="incidentDescription">Incident Description</label>
          <textarea
            className="form-control"
            id="incidentDescription"
            rows="5"
            placeholder="Describe the incident..."
          />
        </div>
        <button type="submit" className="btn btn-dark">
          Generate Plan
        </button>
      </form>
    </div>
  )
}

export default ResponsePlanner
