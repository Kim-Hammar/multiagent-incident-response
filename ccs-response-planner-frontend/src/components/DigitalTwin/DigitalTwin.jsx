import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../contexts/AuthContext.jsx'
import { API_DIGITAL_TWIN_URL, API_DIGITAL_TWIN_RESET_URL } from '../Common/constants'
import ConfigTab from './ConfigTab.jsx'
import DeployTab from './DeployTab.jsx'
import './DigitalTwin.css'

/**
 * Digital twin page with Configuration and Deployment tabs.
 */
function DigitalTwin() {
  const { token, logout } = useAuth()
  const [hosts, setHosts] = useState([])
  const [links, setLinks] = useState([])
  const [alert, setAlert] = useState(null)
  const [activeTab, setActiveTab] = useState('config')

  const loadConfig = useCallback(async () => {
    try {
      const response = await fetch(API_DIGITAL_TWIN_URL, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.status === 401) {
        logout()
        return
      }
      const data = await response.json()
      setHosts(data.hosts || [])
      setLinks(data.links || [])
    } catch (err) {
      setAlert({ type: 'danger', message: `Failed to load configuration: ${err.message}` })
    }
  }, [token, logout])

  useEffect(() => {
    loadConfig()
  }, [loadConfig])

  useEffect(() => {
    if (!alert) return
    const timer = setTimeout(() => setAlert(null), 3000)
    return () => clearTimeout(timer)
  }, [alert])

  const saveConfig = async () => {
    try {
      const response = await fetch(API_DIGITAL_TWIN_URL, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ hosts, links })
      })
      if (response.status === 401) {
        logout()
        return
      }
      if (!response.ok) {
        const data = await response.json()
        setAlert({ type: 'danger', message: data.error || 'Failed to save' })
        return
      }
      setAlert({ type: 'success', message: 'Configuration saved successfully' })
    } catch (err) {
      setAlert({ type: 'danger', message: `Failed to save configuration: ${err.message}` })
    }
  }

  const resetConfig = async () => {
    try {
      const response = await fetch(API_DIGITAL_TWIN_RESET_URL, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.status === 401) {
        logout()
        return
      }
      const data = await response.json()
      setHosts(data.hosts || [])
      setLinks(data.links || [])
      setAlert({ type: 'success', message: 'Configuration reset to default' })
    } catch (err) {
      setAlert({ type: 'danger', message: `Failed to reset configuration: ${err.message}` })
    }
  }

  const addHost = () => {
    setHosts([...hosts, { id: '', name: '', docker_image: '', ip_addresses: [] }])
  }

  const updateHost = (index, field, value) => {
    const updated = hosts.map((h, i) => {
      if (i !== index) return h
      if (field === 'ip_addresses') {
        return { ...h, [field]: value.split(',').map((s) => s.trim()) }
      }
      return { ...h, [field]: value }
    })
    setHosts(updated)
  }

  const removeHost = (index) => {
    setHosts(hosts.filter((_, i) => i !== index))
  }

  const addLink = () => {
    setLinks([...links, { source: '', target: '' }])
  }

  const updateLink = (index, field, value) => {
    const updated = links.map((l, i) => (i === index ? { ...l, [field]: value } : l))
    setLinks(updated)
  }

  const removeLink = (index) => {
    setLinks(links.filter((_, i) => i !== index))
  }

  return (
    <div className="DigitalTwin">
      <h2>Digital twin</h2>
      <p className="subtitle">Configure and deploy the digital twin environment.</p>
      <hr />

      {alert && (
        <div className={`alert alert-${alert.type} alert-dismissible`} role="alert">
          {alert.message}
          <button type="button" className="close" aria-label="Close" onClick={() => setAlert(null)}>
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
      )}

      <ul className="nav nav-tabs dt-tabs">
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
            className={`nav-link${activeTab === 'deploy' ? ' active' : ''}`}
            onClick={() => setActiveTab('deploy')}
          >
            Deployment
          </button>
        </li>
      </ul>

      <div className="tab-content">
        {activeTab === 'config' && (
          <ConfigTab
            hosts={hosts}
            links={links}
            addHost={addHost}
            updateHost={updateHost}
            removeHost={removeHost}
            addLink={addLink}
            updateLink={updateLink}
            removeLink={removeLink}
            saveConfig={saveConfig}
            resetConfig={resetConfig}
          />
        )}
        {activeTab === 'deploy' && <DeployTab token={token} logout={logout} />}
      </div>
    </div>
  )
}

export default DigitalTwin
