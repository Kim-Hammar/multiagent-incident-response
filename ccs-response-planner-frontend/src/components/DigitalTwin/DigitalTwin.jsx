import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../contexts/AuthContext.jsx'
import {
  API_DIGITAL_TWIN_URL,
  API_DIGITAL_TWIN_RESET_URL,
  API_DIGITAL_TWIN_CONFIGS_URL
} from '../Common/constants'
import ConfigTab from './ConfigTab.jsx'
import DeployTab from './DeployTab.jsx'
import ValidationTab from './ValidationTab.jsx'
import './DigitalTwin.css'

/**
 * Digital twin page with Configuration and Deployment tabs.
 */
function DigitalTwin() {
  const { token, logout } = useAuth()
  const [networks, setNetworks] = useState([])
  const [hosts, setHosts] = useState([])
  const [links, setLinks] = useState([])
  const [specificationCommands, setSpecificationCommands] = useState([])
  const [alert, setAlert] = useState(null)
  const [activeTab, setActiveTab] = useState('config')
  const [savedConfigs, setSavedConfigs] = useState([])
  const [selectedConfigId, setSelectedConfigId] = useState('')

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
      setNetworks(data.networks || [])
      setHosts(data.hosts || [])
      setLinks(data.links || [])
      setSpecificationCommands(data.specification_commands || [])
    } catch (err) {
      setAlert({ type: 'danger', message: `Failed to load configuration: ${err.message}` })
    }
  }, [token, logout])

  useEffect(() => {
    loadConfig()
  }, [loadConfig])

  useEffect(() => {
    fetch(API_DIGITAL_TWIN_CONFIGS_URL, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => setSavedConfigs(data))
      .catch(() => {})
  }, [token])

  const loadSelectedConfig = async (configId) => {
    if (!configId) return
    try {
      const res = await fetch(`${API_DIGITAL_TWIN_CONFIGS_URL}/${configId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.status === 401) {
        logout()
        return
      }
      if (!res.ok) return
      const data = await res.json()
      const cfg = data.config || {}
      setNetworks(cfg.networks || [])
      setHosts(cfg.hosts || [])
      setLinks(cfg.links || [])
      setSpecificationCommands(cfg.specification_commands || [])
      setAlert({ type: 'success', message: `Loaded config: ${data.name}` })
    } catch (err) {
      setAlert({ type: 'danger', message: `Failed to load config: ${err.message}` })
    }
  }

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
        body: JSON.stringify({
          networks,
          hosts,
          links,
          specification_commands: specificationCommands
        })
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
      setNetworks(data.networks || [])
      setHosts(data.hosts || [])
      setLinks(data.links || [])
      setSpecificationCommands(data.specification_commands || [])
      setAlert({ type: 'success', message: 'Configuration reset to default' })
    } catch (err) {
      setAlert({ type: 'danger', message: `Failed to reset configuration: ${err.message}` })
    }
  }

  const addNetwork = () => {
    setNetworks([...networks, { id: '', name: '', subnet: '', gateway: '' }])
  }

  const updateNetwork = (index, field, value) => {
    const updated = networks.map((n, i) => (i === index ? { ...n, [field]: value } : n))
    setNetworks(updated)
  }

  const removeNetwork = (index) => {
    setNetworks(networks.filter((_, i) => i !== index))
  }

  const addHost = () => {
    setHosts([...hosts, { id: '', name: '', docker_image: '', ip_addresses: {} }])
  }

  const updateHost = (index, field, value) => {
    const updated = hosts.map((h, i) => (i === index ? { ...h, [field]: value } : h))
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

  const addSpecCommand = () => {
    setSpecificationCommands([...specificationCommands, { host: '', command: '', description: '' }])
  }

  const updateSpecCommand = (index, field, value) => {
    const updated = specificationCommands.map((c, i) =>
      i === index ? { ...c, [field]: value } : c
    )
    setSpecificationCommands(updated)
  }

  const removeSpecCommand = (index) => {
    setSpecificationCommands(specificationCommands.filter((_, i) => i !== index))
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
        <li className="nav-item">
          <button
            type="button"
            className={`nav-link${activeTab === 'validate' ? ' active' : ''}`}
            onClick={() => setActiveTab('validate')}
          >
            Validation
          </button>
        </li>
      </ul>

      <div className="tab-content">
        {activeTab === 'config' && (
          <ConfigTab
            networks={networks}
            hosts={hosts}
            links={links}
            specificationCommands={specificationCommands}
            addNetwork={addNetwork}
            updateNetwork={updateNetwork}
            removeNetwork={removeNetwork}
            addHost={addHost}
            updateHost={updateHost}
            removeHost={removeHost}
            addLink={addLink}
            updateLink={updateLink}
            removeLink={removeLink}
            addSpecCommand={addSpecCommand}
            updateSpecCommand={updateSpecCommand}
            removeSpecCommand={removeSpecCommand}
            saveConfig={saveConfig}
            resetConfig={resetConfig}
            savedConfigs={savedConfigs}
            selectedConfigId={selectedConfigId}
            setSelectedConfigId={setSelectedConfigId}
            loadSelectedConfig={loadSelectedConfig}
          />
        )}
        {activeTab === 'deploy' && <DeployTab token={token} logout={logout} />}
        {activeTab === 'validate' && (
          <ValidationTab
            token={token}
            logout={logout}
            specificationCommands={specificationCommands}
          />
        )}
      </div>
    </div>
  )
}

export default DigitalTwin
