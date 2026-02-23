import CopyablePre from './CopyablePre.jsx'

/**
 * Modal dialog that displays the raw conversation history (context)
 * sent to the LLM, with size statistics for debugging.
 */
function ContextModal({ show, conversationHistory, onClose }) {
  if (!show) return null

  const entries = conversationHistory || []
  const totalEntries = entries.length

  const typeCounts = {}
  const typeSizes = {}
  const toolResults = []
  let totalSize = 0

  entries.forEach((entry) => {
    const t = entry.type || 'unknown'
    const size = JSON.stringify(entry).length
    typeCounts[t] = (typeCounts[t] || 0) + 1
    typeSizes[t] = (typeSizes[t] || 0) + size
    totalSize += size

    if (t === 'tool_result') {
      const resultSize = entry.result ? JSON.stringify(entry.result).length : 0
      toolResults.push({ name: entry.tool_name || 'unknown', size: resultSize })
    }
  })

  toolResults.sort((a, b) => b.size - a.size)

  const fmt = (n) => {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
    return String(n)
  }

  const sortedTypes = Object.keys(typeCounts).sort((a, b) => typeSizes[b] - typeSizes[a])

  return (
    <div className="ia-modal-backdrop" onClick={onClose}>
      <div className="ia-modal" onClick={(e) => e.stopPropagation()}>
        <div className="ia-modal-header">
          <span className="ia-modal-title">Conversation Context</span>
          <button type="button" className="close" aria-label="Close" onClick={onClose}>
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <div className="ia-modal-body">
          <div style={{ marginBottom: '16px', fontSize: '13px' }}>
            <strong>Summary</strong>
            <div style={{ marginTop: '4px' }}>
              Total entries: {totalEntries} &mdash; Approx size: {fmt(totalSize)} chars
            </div>

            <table
              className="table table-sm table-bordered"
              style={{ marginTop: '8px', fontSize: '12px' }}
            >
              <thead>
                <tr>
                  <th>Type</th>
                  <th style={{ textAlign: 'right' }}>Count</th>
                  <th style={{ textAlign: 'right' }}>Size (chars)</th>
                </tr>
              </thead>
              <tbody>
                {sortedTypes.map((t) => (
                  <tr key={t}>
                    <td>
                      <code>{t}</code>
                    </td>
                    <td style={{ textAlign: 'right' }}>{typeCounts[t]}</td>
                    <td style={{ textAlign: 'right' }}>{fmt(typeSizes[t])}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {toolResults.length > 0 && (
              <>
                <strong>Tool results by size</strong>
                <table
                  className="table table-sm table-bordered"
                  style={{ marginTop: '4px', fontSize: '12px' }}
                >
                  <thead>
                    <tr>
                      <th>Tool</th>
                      <th style={{ textAlign: 'right' }}>Result size (chars)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {toolResults.map((tr, i) => (
                      <tr key={i}>
                        <td>
                          <code>{tr.name}</code>
                        </td>
                        <td style={{ textAlign: 'right' }}>{fmt(tr.size)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </div>

          <CopyablePre
            className="ia-prompt-text"
            text={JSON.stringify(
              entries,
              (key, value) => {
                if (
                  typeof value === 'string' &&
                  value.startsWith('data:image/') &&
                  value.length > 200
                ) {
                  return '(base64 image omitted)'
                }
                return value
              },
              2
            )}
          >
            {JSON.stringify(
              entries,
              (key, value) => {
                if (
                  typeof value === 'string' &&
                  value.startsWith('data:image/') &&
                  value.length > 200
                ) {
                  return '(base64 image omitted)'
                }
                return value
              },
              2
            )}
          </CopyablePre>
        </div>
      </div>
    </div>
  )
}

export default ContextModal
