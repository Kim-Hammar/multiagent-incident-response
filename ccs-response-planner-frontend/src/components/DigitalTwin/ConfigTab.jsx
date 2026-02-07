/**
 * Configuration tab for the digital twin editor.
 * Renders host and connection tables with add/remove/update controls.
 */
function ConfigTab({
  hosts,
  links,
  addHost,
  updateHost,
  removeHost,
  addLink,
  updateLink,
  removeLink,
  saveConfig,
  resetConfig
}) {
  return (
    <>
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
          {hosts.map((host, index) => (
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
                <input
                  type="text"
                  className="form-control form-control-sm"
                  value={(host.ip_addresses || []).join(', ')}
                  onChange={(e) => updateHost(index, 'ip_addresses', e.target.value)}
                  placeholder="e.g. 10.0.0.1, 10.0.0.2"
                />
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
          ))}
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
