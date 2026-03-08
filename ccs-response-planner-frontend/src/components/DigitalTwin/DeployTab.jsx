import IncidentDeployCard from './IncidentDeployCard.jsx'

/**
 * Deployment tab for the digital twin.
 * Renders one IncidentDeployCard per saved configuration for parallel deploy/stop.
 */
function DeployTab({ token, logout, savedConfigs }) {
  if (!savedConfigs || savedConfigs.length === 0) {
    return (
      <div className="deploy-tab">
        <div className="alert alert-info" role="alert">
          No saved configurations found. Go to the <strong>Configuration</strong> tab to load or
          create a configuration first.
        </div>
      </div>
    )
  }

  return (
    <div className="deploy-tab">
      {savedConfigs.map((cfg) => (
        <IncidentDeployCard
          key={cfg.id}
          configId={cfg.id}
          configName={cfg.name}
          exampleIncidentId={cfg.example_incident_id}
          token={token}
          logout={logout}
        />
      ))}
    </div>
  )
}

export default DeployTab
