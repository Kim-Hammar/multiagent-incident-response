import { useState } from 'react'
import InformationAgent from './InformationAgent.jsx'
import PenetrationTestAgent from './PenetrationTestAgent.jsx'
import ValidationAgent from './ValidationAgent.jsx'
import './Agents.css'

/**
 * Agents page with sub-tabs for individual agents.
 */
function Agents() {
  const [activeTab, setActiveTab] = useState('information')

  return (
    <div className="Agents">
      <h2>Agents</h2>
      <p className="subtitle">Agents that work collectively for incident response planning.</p>
      <hr />

      <ul className="nav nav-tabs agents-tabs">
        <li className="nav-item">
          <button
            type="button"
            className={`nav-link${activeTab === 'information' ? ' active' : ''}`}
            onClick={() => setActiveTab('information')}
          >
            Information Agent
          </button>
        </li>
        <li className="nav-item">
          <button
            type="button"
            className={`nav-link${activeTab === 'pentest' ? ' active' : ''}`}
            onClick={() => setActiveTab('pentest')}
          >
            Penetration Test Agent
          </button>
        </li>
        <li className="nav-item">
          <button
            type="button"
            className={`nav-link${activeTab === 'validation' ? ' active' : ''}`}
            onClick={() => setActiveTab('validation')}
          >
            Validation Agent
          </button>
        </li>
      </ul>

      <div className="tab-content">
        {activeTab === 'information' && <InformationAgent />}
        {activeTab === 'pentest' && <PenetrationTestAgent />}
        {activeTab === 'validation' && <ValidationAgent />}
      </div>
    </div>
  )
}

export default Agents
