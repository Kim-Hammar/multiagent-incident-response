import { useState } from 'react'
import ReportAgent from './ReportAgent.jsx'
import PlanVerifierAgent from './PlanVerifierAgent.jsx'
import CodeAgent from './CodeAgent.jsx'
import CodeVerifierAgent from './CodeVerifierAgent.jsx'
import CodeManagerAgent from './CodeManagerAgent.jsx'
import PlanManagerAgent from './PlanManagerAgent.jsx'
import PlannerAgent from './PlannerAgent.jsx'
import ReportVerifierAgent from './ReportVerifierAgent.jsx'
import ReportManagerAgent from './ReportManagerAgent.jsx'
import OrchestratorAgent from './OrchestratorAgent.jsx'
import AttackPathVerifierAgent from './AttackPathVerifierAgent.jsx'
import HostAnalyzerAgent from './HostAnalyzerAgent.jsx'
import ActionVerifierAgent from './ActionVerifierAgent.jsx'
import './Agents.css'

/**
 * Agents page with dropdown selector for individual agents.
 */
function Agents() {
  const [selectedAgent, setSelectedAgent] = useState(
    () => localStorage.getItem('selectedAgent') || 'report'
  )

  const handleAgentChange = (value) => {
    setSelectedAgent(value)
    localStorage.setItem('selectedAgent', value)
  }

  return (
    <div className="Agents">
      <h2>Agents</h2>
      <p className="subtitle">Agents that work collectively for incident response planning.</p>
      <hr />

      <div className="ia-agent-selector">
        <label htmlFor="agent-select">Agent:</label>
        <select
          id="agent-select"
          className="form-control form-control-sm"
          value={selectedAgent}
          onChange={(e) => handleAgentChange(e.target.value)}
        >
          <option value="orchestrator">Orchestrator Agent</option>
          <option value="report">Report Agent</option>
          <option value="report-review">Report Verifier Agent</option>
          <option value="report-manager">Report Manager Agent</option>
          <option value="plan-verifier">Plan Verifier Agent</option>
          <option value="code">Code Agent</option>
          <option value="code-review">Code Verifier Agent</option>
          <option value="code-manager">Code Manager Agent</option>
          <option value="plan-manager">Plan Manager Agent</option>
          <option value="planner">Planner Agent</option>
          <option value="attack-path-verifier">Attack Path Verifier Agent</option>
          <option value="host-analyzer">Host Analyzer Agent</option>
          <option value="action-verifier">Action Verifier Agent</option>
        </select>
      </div>

      {selectedAgent === 'orchestrator' && <OrchestratorAgent />}
      {selectedAgent === 'report' && <ReportAgent />}
      {selectedAgent === 'report-review' && <ReportVerifierAgent />}
      {selectedAgent === 'report-manager' && <ReportManagerAgent />}
      {selectedAgent === 'plan-verifier' && <PlanVerifierAgent />}
      {selectedAgent === 'code' && <CodeAgent />}
      {selectedAgent === 'code-review' && <CodeVerifierAgent />}
      {selectedAgent === 'code-manager' && <CodeManagerAgent />}
      {selectedAgent === 'plan-manager' && <PlanManagerAgent />}
      {selectedAgent === 'planner' && <PlannerAgent />}
      {selectedAgent === 'attack-path-verifier' && <AttackPathVerifierAgent />}
      {selectedAgent === 'host-analyzer' && <HostAnalyzerAgent />}
      {selectedAgent === 'action-verifier' && <ActionVerifierAgent />}
    </div>
  )
}

export default Agents
