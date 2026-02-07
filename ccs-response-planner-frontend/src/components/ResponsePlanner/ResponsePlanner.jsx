import { useState } from 'react'
import { API_EXAMPLE_URL, API_PLAN_URL } from '../Common/constants'
import { useAuth } from '../../contexts/AuthContext.jsx'
import ConfigTab from './ConfigTab.jsx'
import PlanningTab from './PlanningTab.jsx'
import './ResponsePlanner.css'

/**
 * The response planner page with Configuration and Planning process tabs.
 */
function ResponsePlanner() {
  const [systemDescription, setSystemDescription] = useState('')
  const [securityAlerts, setSecurityAlerts] = useState('')
  const [operatorFeedback, setOperatorFeedback] = useState('')
  const [systemDescriptionImages, setSystemDescriptionImages] = useState([])
  const [securityAlertsImages, setSecurityAlertsImages] = useState([])
  const [operatorFeedbackImages, setOperatorFeedbackImages] = useState([])
  const [activeTab, setActiveTab] = useState('config')
  const [planResult, setPlanResult] = useState(null)
  const [generating, setGenerating] = useState(false)
  const { token, logout } = useAuth()

  const handlePaste = (setImages) => (event) => {
    const items = event.clipboardData?.items
    if (!items) return
    for (const item of items) {
      if (item.type.startsWith('image/')) {
        event.preventDefault()
        const file = item.getAsFile()
        const reader = new FileReader()
        reader.onload = (e) => {
          setImages((prev) => [...prev, e.target.result])
        }
        reader.readAsDataURL(file)
      }
    }
  }

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
    setSystemDescriptionImages(data.system_description_images || [])
  }

  const handleClear = () => {
    setSystemDescription('')
    setSecurityAlerts('')
    setOperatorFeedback('')
    setSystemDescriptionImages([])
    setSecurityAlertsImages([])
    setOperatorFeedbackImages([])
  }

  const handleGenerate = async () => {
    setGenerating(true)
    setActiveTab('planning')
    try {
      const allImages = [
        ...systemDescriptionImages,
        ...securityAlertsImages,
        ...operatorFeedbackImages
      ]
      const incidentDescription = [systemDescription, securityAlerts, operatorFeedback]
        .filter(Boolean)
        .join('\n\n')
      const res = await fetch(API_PLAN_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          incident_description: incidentDescription,
          images: allImages
        })
      })
      if (res.status === 401) {
        logout()
        return
      }
      const data = await res.json()
      setPlanResult(data)
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="ResponsePlanner">
      <h2>Response planner</h2>
      <p className="subtitle">
        Provide system details, security alerts, and operator input to generate an incident response
        plan.
      </p>
      <hr />

      <ul className="nav nav-tabs rp-tabs">
        <li className="nav-item">
          <button
            type="button"
            className={`nav-link${activeTab === 'config' ? ' active' : ''}`}
            onClick={() => setActiveTab('config')}
          >
            Configuration
          </button>
        </li>
        <li className="nav-item">
          <button
            type="button"
            className={`nav-link${activeTab === 'planning' ? ' active' : ''}`}
            onClick={() => setActiveTab('planning')}
          >
            Planning process
          </button>
        </li>
      </ul>

      <div className="tab-content">
        {activeTab === 'config' && (
          <ConfigTab
            systemDescription={systemDescription}
            setSystemDescription={setSystemDescription}
            securityAlerts={securityAlerts}
            setSecurityAlerts={setSecurityAlerts}
            operatorFeedback={operatorFeedback}
            setOperatorFeedback={setOperatorFeedback}
            systemDescriptionImages={systemDescriptionImages}
            setSystemDescriptionImages={setSystemDescriptionImages}
            securityAlertsImages={securityAlertsImages}
            setSecurityAlertsImages={setSecurityAlertsImages}
            operatorFeedbackImages={operatorFeedbackImages}
            setOperatorFeedbackImages={setOperatorFeedbackImages}
            handlePaste={handlePaste}
            fetchExample={fetchExample}
            onClear={handleClear}
            onGenerate={handleGenerate}
            generating={generating}
          />
        )}
        {activeTab === 'planning' && (
          <PlanningTab planResult={planResult} generating={generating} />
        )}
      </div>
    </div>
  )
}

export default ResponsePlanner
