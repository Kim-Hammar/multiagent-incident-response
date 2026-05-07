/**
 * Reusable table for rendering feature-toggle configuration
 * in the same visual style as the Agents (rp-subagents-table) tab.
 *
 * Each row receives { id, label, description, checked, onChange, disabled }.
 */
function ConfigurationTable({ rows }) {
  return (
    <div style={{ marginTop: '16px' }}>
      <table className="rp-subagents-table">
        <thead>
          <tr>
            <th>Feature</th>
            <th style={{ width: '55%' }}>Description</th>
            <th style={{ width: '80px', textAlign: 'center' }}>Enabled</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td style={{ fontWeight: 500 }}>{row.label}</td>
              <td className="rp-config-description">{row.description}</td>
              <td style={{ textAlign: 'center' }}>
                <input
                  type="checkbox"
                  id={row.id}
                  checked={row.checked}
                  onChange={(e) => row.onChange(e.target.checked)}
                  disabled={row.disabled}
                  style={{
                    width: '15px',
                    height: '15px',
                    cursor: row.disabled ? 'default' : 'pointer'
                  }}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default ConfigurationTable
