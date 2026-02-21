import { useState } from 'react'
import PromptModal from './PromptModal.jsx'
import { DEFAULT_MODEL_NAME } from '../../Common/constants.js'

/**
 * Reusable table for configuring LLM models, iteration limits,
 * compaction thresholds, and per-agent prompts. Used by all 12
 * agent pages in the Agents section.
 */
function AgentConfigTable({ rows, models, isAgentBusy, token, getPromptBody }) {
  const [showPromptModal, setShowPromptModal] = useState(false)
  const [promptText, setPromptText] = useState('')
  const [promptImages, setPromptImages] = useState([])
  const [loadingAgent, setLoadingAgent] = useState(null)

  const fetchPrompt = async (url, label) => {
    setLoadingAgent(label)
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(getPromptBody())
      })
      if (!res.ok) return
      const data = await res.json()
      setPromptText(data.prompt || '')
      setPromptImages([])
      setShowPromptModal(true)
    } catch {
      /* ignore */
    } finally {
      setLoadingAgent(null)
    }
  }

  const modelOptions = (
    <>
      <option value="">Default ({DEFAULT_MODEL_NAME})</option>
      {models.map((m) => (
        <option key={m.name} value={m.name}>
          {m.display_name}
        </option>
      ))}
    </>
  )

  return (
    <div style={{ marginTop: '16px' }}>
      <table className="rp-subagents-table">
        <thead>
          <tr>
            <th>Agent</th>
            <th>LLM</th>
            <th>Iterations / Limit</th>
            <th>Compaction %</th>
            <th>Prompt</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label}>
              <td>{row.label}</td>
              <td>
                <select
                  className="form-control form-control-sm"
                  value={row.model}
                  onChange={(e) => row.setModel(e.target.value)}
                  disabled={isAgentBusy}
                >
                  {row.defaultLabel ? (
                    <>
                      <option value="">{row.defaultLabel}</option>
                      {models.map((m) => (
                        <option key={m.name} value={m.name}>
                          {m.display_name}
                        </option>
                      ))}
                    </>
                  ) : (
                    modelOptions
                  )}
                </select>
              </td>
              <td>
                {row.iteration ? (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <input
                      type="number"
                      className="form-control form-control-sm"
                      style={{ width: '70px' }}
                      min={row.iteration.min}
                      max={row.iteration.max}
                      value={row.iteration.value}
                      onChange={(e) => {
                        const v = parseInt(e.target.value, 10)
                        if (v >= row.iteration.min && v <= row.iteration.max) row.iteration.set(v)
                      }}
                      disabled={isAgentBusy}
                    />
                    <span className="rp-iter-suffix">{row.iteration.suffix}</span>
                  </span>
                ) : (
                  <span style={{ color: '#999' }}>&mdash;</span>
                )}
              </td>
              <td>
                {row.compaction != null ? (
                  <input
                    type="number"
                    className="form-control form-control-sm"
                    style={{ width: '70px' }}
                    min={10}
                    max={100}
                    value={row.compaction}
                    onChange={(e) => {
                      const v = parseInt(e.target.value, 10) || 80
                      row.setCompaction(Math.max(10, Math.min(100, v)))
                    }}
                    disabled={isAgentBusy}
                  />
                ) : (
                  <span style={{ color: '#999' }}>&mdash;</span>
                )}
              </td>
              <td>
                {row.promptUrl ? (
                  <button
                    type="button"
                    className="btn btn-outline-dark btn-sm"
                    onClick={() => fetchPrompt(row.promptUrl, row.label)}
                    disabled={loadingAgent != null}
                  >
                    <i className="fa fa-file-text-o" aria-hidden="true" />{' '}
                    {loadingAgent === row.label ? 'Loading...' : 'Show'}
                  </button>
                ) : (
                  <span style={{ color: '#999' }}>&mdash;</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <PromptModal
        show={showPromptModal}
        promptText={promptText}
        promptImages={promptImages}
        onClose={() => setShowPromptModal(false)}
      />
    </div>
  )
}

export default AgentConfigTable
