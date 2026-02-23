import { useState } from 'react'
import ReportAgent from './ReportAgent.jsx'
import ValidationAgent from './ValidationAgent.jsx'
import CodeAgent from './CodeAgent.jsx'
import CodeReviewerAgent from './CodeReviewerAgent.jsx'
import CodeManagerAgent from './CodeManagerAgent.jsx'
import PlanManagerAgent from './PlanManagerAgent.jsx'
import PlannerAgent from './PlannerAgent.jsx'
import ReportReviewerAgent from './ReportReviewerAgent.jsx'
import ReportManagerAgent from './ReportManagerAgent.jsx'
import OrchestratorAgent from './OrchestratorAgent.jsx'
import PentestAgent from './PentestAgent.jsx'
import HostAnalyzerAgent from './HostAnalyzerAgent.jsx'
import ActionValidatorAgent from './ActionValidatorAgent.jsx'
import './Agents.css'

/**
 * Agents page with dropdown selector for individual agents.
 */
function Agents() {
  const [selectedAgent, setSelectedAgent] = useState('report')

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
          onChange={(e) => setSelectedAgent(e.target.value)}
        >
          <option value="orchestrator">Orchestrator Agent</option>
          <option value="report">Report Agent</option>
          <option value="report-review">Report Reviewer Agent</option>
          <option value="report-manager">Report Manager Agent</option>
          <option value="validation">Validation Agent</option>
          <option value="code">Code Agent</option>
          <option value="code-review">Code Reviewer Agent</option>
          <option value="code-manager">Code Manager Agent</option>
          <option value="plan-manager">Plan Manager Agent</option>
          <option value="planner">Planner Agent</option>
          <option value="pentest">Pentest Agent</option>
          <option value="host-analyzer">Host Analyzer Agent</option>
          <option value="action-validator">Action Validator Agent</option>
        </select>
      </div>

      {selectedAgent === 'orchestrator' && <OrchestratorAgent />}
      {selectedAgent === 'report' && <ReportAgent />}
      {selectedAgent === 'report-review' && <ReportReviewerAgent />}
      {selectedAgent === 'report-manager' && <ReportManagerAgent />}
      {selectedAgent === 'validation' && <ValidationAgent />}
      {selectedAgent === 'code' && <CodeAgent />}
      {selectedAgent === 'code-review' && <CodeReviewerAgent />}
      {selectedAgent === 'code-manager' && <CodeManagerAgent />}
      {selectedAgent === 'plan-manager' && <PlanManagerAgent />}
      {selectedAgent === 'planner' && <PlannerAgent />}
      {selectedAgent === 'pentest' && <PentestAgent />}
      {selectedAgent === 'host-analyzer' && <HostAnalyzerAgent />}
      {selectedAgent === 'action-validator' && <ActionValidatorAgent />}
    </div>
  )
}

export default Agents
