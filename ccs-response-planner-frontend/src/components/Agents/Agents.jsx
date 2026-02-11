import { useState } from 'react'
import InformationAgent from './InformationAgent.jsx'
import PenetrationTestAgent from './PenetrationTestAgent.jsx'
import ValidationAgent from './ValidationAgent.jsx'
import CodeAgent from './CodeAgent.jsx'
import './Agents.css'

/**
 * Agents page with dropdown selector for individual agents.
 */
function Agents() {
  const [selectedAgent, setSelectedAgent] = useState('information')

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
          <option value="information">Information Agent</option>
          <option value="pentest">Penetration Test Agent</option>
          <option value="validation">Validation Agent</option>
          <option value="code">Code Agent</option>
        </select>
      </div>

      {selectedAgent === 'information' && <InformationAgent />}
      {selectedAgent === 'pentest' && <PenetrationTestAgent />}
      {selectedAgent === 'validation' && <ValidationAgent />}
      {selectedAgent === 'code' && <CodeAgent />}
    </div>
  )
}

export default Agents
