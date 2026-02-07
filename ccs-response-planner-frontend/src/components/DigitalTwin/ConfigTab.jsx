/**
 * Configuration tab for the digital twin editor.
 * Renders network, host, and connection tables with add/remove/update controls.
 */
function ConfigTab({
  networks,
  hosts,
  links,
  specificationCommands,
  addNetwork,
  updateNetwork,
  removeNetwork,
  addHost,
  updateHost,
  removeHost,
  addLink,
  updateLink,
  removeLink,
  addSpecCommand,
  updateSpecCommand,
  removeSpecCommand,
  saveConfig,
  resetConfig
}) {
  const setHostIp = (hostIndex, netId, ip) => {
    const current = hosts[hostIndex].ip_addresses || {}
    const updated = { ...current, [netId]: ip }
    updateHost(hostIndex, 'ip_addresses', updated)
  }

  const removeHostIp = (hostIndex, netId) => {
    const current = { ...(hosts[hostIndex].ip_addresses || {}) }
    delete current[netId]
    updateHost(hostIndex, 'ip_addresses', current)
  }

  const addHostIp = (hostIndex) => {
    const current = hosts[hostIndex].ip_addresses || {}
    const usedNets = Object.keys(current)
    const available = networks.filter((n) => n.id && !usedNets.includes(n.id))
    if (available.length === 0) return
    updateHost(hostIndex, 'ip_addresses', { ...current, [available[0].id]: '' })
  }

  return (
    <>
      <div className="section-header">
        <h5>Networks</h5>
        <button type="button" className="btn btn-sm btn-outline-dark" onClick={addNetwork}>
          <i className="fa fa-plus" aria-hidden="true" /> Add network
        </button>
      </div>
      <table className="table table-striped table-sm">
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Subnet</th>
            <th>Gateway</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {networks.map((net, index) => (
            <tr key={index}>
              <td>
                <input
                  type="text"
                  className="form-control form-control-sm"
                  value={net.id}
                  onChange={(e) => updateNetwork(index, 'id', e.target.value)}
                  placeholder="e.g. zone1"
                />
              </td>
              <td>
                <input
                  type="text"
                  className="form-control form-control-sm"
                  value={net.name}
                  onChange={(e) => updateNetwork(index, 'name', e.target.value)}
                  placeholder="e.g. Zone 1"
                />
              </td>
              <td>
                <input
                  type="text"
                  className="form-control form-control-sm"
                  value={net.subnet}
                  onChange={(e) => updateNetwork(index, 'subnet', e.target.value)}
                  placeholder="e.g. 10.0.2.0/24"
                />
              </td>
              <td>
                <input
                  type="text"
                  className="form-control form-control-sm"
                  value={net.gateway || ''}
                  onChange={(e) => updateNetwork(index, 'gateway', e.target.value)}
                  placeholder="e.g. 10.0.2.100"
                />
              </td>
              <td>
                <button
                  type="button"
                  className="btn btn-sm btn-outline-danger"
                  onClick={() => removeNetwork(index)}
                >
                  <i className="fa fa-trash" aria-hidden="true" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="section-header">
        <h5>Hosts</h5>
        <button type="button" className="btn btn-sm btn-outline-dark" onClick={addHost}>
          <i className="fa fa-plus" aria-hidden="true" /> Add host
        </button>
      </div>
      <table className="table table-striped table-sm">
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Docker Image</th>
            <th>IP Addresses</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {hosts.map((host, index) => {
            const ipAddrs = host.ip_addresses || {}
            const ipEntries = Object.entries(ipAddrs)
            const usedNets = Object.keys(ipAddrs)
            const availableNets = networks.filter((n) => n.id && !usedNets.includes(n.id))

            return (
              <tr key={index}>
                <td>
                  <input
                    type="text"
                    className="form-control form-control-sm"
                    value={host.id}
                    onChange={(e) => updateHost(index, 'id', e.target.value)}
                    placeholder="e.g. server_1"
                  />
                </td>
                <td>
                  <input
                    type="text"
                    className="form-control form-control-sm"
                    value={host.name}
                    onChange={(e) => updateHost(index, 'name', e.target.value)}
                    placeholder="e.g. Server 1"
                  />
                </td>
                <td>
                  <input
                    type="text"
                    className="form-control form-control-sm"
                    value={host.docker_image}
                    onChange={(e) => updateHost(index, 'docker_image', e.target.value)}
                    placeholder="e.g. debian:9.2"
                  />
                </td>
                <td>
                  {ipEntries.map(([netId, ip]) => (
                    <div key={netId} className="ip-row">
                      <span className="ip-net-label">{netId}</span>
                      <input
                        type="text"
                        className="form-control form-control-sm ip-input"
                        value={ip}
                        onChange={(e) => setHostIp(index, netId, e.target.value)}
                        placeholder="e.g. 10.0.2.1"
                      />
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-danger ip-remove"
                        onClick={() => removeHostIp(index, netId)}
                      >
                        <i className="fa fa-times" aria-hidden="true" />
                      </button>
                    </div>
                  ))}
                  {availableNets.length > 0 && (
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-secondary ip-add"
                      onClick={() => addHostIp(index)}
                    >
                      <i className="fa fa-plus" aria-hidden="true" /> Add IP
                    </button>
                  )}
                </td>
                <td>
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-danger"
                    onClick={() => removeHost(index)}
                  >
                    <i className="fa fa-trash" aria-hidden="true" />
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>

      <div className="section-header">
        <h5>Connections</h5>
        <button type="button" className="btn btn-sm btn-outline-dark" onClick={addLink}>
          <i className="fa fa-plus" aria-hidden="true" /> Add connection
        </button>
      </div>
      <table className="table table-striped table-sm">
        <thead>
          <tr>
            <th>Source</th>
            <th>Target</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {links.map((link, index) => (
            <tr key={index}>
              <td>
                <select
                  className="form-control form-control-sm"
                  value={link.source}
                  onChange={(e) => updateLink(index, 'source', e.target.value)}
                >
                  <option value="">-- select --</option>
                  {hosts.map((h) => (
                    <option key={h.id} value={h.id}>
                      {h.name || h.id}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <select
                  className="form-control form-control-sm"
                  value={link.target}
                  onChange={(e) => updateLink(index, 'target', e.target.value)}
                >
                  <option value="">-- select --</option>
                  {hosts.map((h) => (
                    <option key={h.id} value={h.id}>
                      {h.name || h.id}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <button
                  type="button"
                  className="btn btn-sm btn-outline-danger"
                  onClick={() => removeLink(index)}
                >
                  <i className="fa fa-trash" aria-hidden="true" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="section-header">
        <h5>Specification</h5>
        <button type="button" className="btn btn-sm btn-outline-dark" onClick={addSpecCommand}>
          <i className="fa fa-plus" aria-hidden="true" /> Add command
        </button>
      </div>
      <table className="table table-striped table-sm">
        <thead>
          <tr>
            <th>Host</th>
            <th>Command</th>
            <th>Description</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {specificationCommands.map((cmd, index) => (
            <tr key={index}>
              <td>
                <select
                  className="form-control form-control-sm"
                  value={cmd.host || ''}
                  onChange={(e) => updateSpecCommand(index, 'host', e.target.value)}
                >
                  <option value="">-- select --</option>
                  {hosts.map((h) => (
                    <option key={h.id} value={h.id}>
                      {h.name || h.id}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <input
                  type="text"
                  className="form-control form-control-sm"
                  value={cmd.command}
                  onChange={(e) => updateSpecCommand(index, 'command', e.target.value)}
                  placeholder="e.g. curl -s http://10.0.2.2:21"
                />
              </td>
              <td>
                <input
                  type="text"
                  className="form-control form-control-sm"
                  value={cmd.description}
                  onChange={(e) => updateSpecCommand(index, 'description', e.target.value)}
                  placeholder="e.g. Verify FTP is reachable"
                />
              </td>
              <td>
                <button
                  type="button"
                  className="btn btn-sm btn-outline-danger"
                  onClick={() => removeSpecCommand(index)}
                >
                  <i className="fa fa-trash" aria-hidden="true" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="action-buttons">
        <button type="button" className="btn btn-dark btn-sm" onClick={saveConfig}>
          <i className="fa fa-save" aria-hidden="true" /> Save configuration
        </button>
        <button type="button" className="btn btn-outline-dark btn-sm" onClick={resetConfig}>
          <i className="fa fa-undo" aria-hidden="true" /> Reset to default
        </button>
      </div>
    </>
  )
}

export default ConfigTab
