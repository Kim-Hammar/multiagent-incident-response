import { useState } from 'react'
import {
  API_AGENTS_ORCHESTRATOR_PROMPT_URL,
  API_AGENTS_REPORT_MANAGER_PROMPT_URL,
  API_AGENTS_REPORT_PROMPT_URL,
  API_AGENTS_REPORT_REVIEW_PROMPT_URL,
  API_AGENTS_PLAN_MANAGER_PROMPT_URL,
  API_AGENTS_CODE_MANAGER_PROMPT_URL,
  API_AGENTS_CODE_PROMPT_URL,
  API_AGENTS_CODE_REVIEW_PROMPT_URL,
  API_AGENTS_PLANNER_PROMPT_URL,
  API_AGENTS_PLAN_VERIFIER_PROMPT_URL
} from '../Common/constants'
import PromptModal from '../Agents/shared/PromptModal.jsx'

/**
 * Agents configuration tab — table-based layout for configuring
 * LLM models and iteration limits per agent, with per-agent
 * "Show prompt" buttons.
 */
function SubAgentsTab({
  models,
  isAgentBusy,
  token,
  systemDescription,
  securityAlerts,
  operatorFeedback,
  orchestratorModel,
  setOrchestratorModel,
  reportManagerModel,
  setReportManagerModel,
  reportAgentModel,
  setReportAgentModel,
  reportVerifierModel,
  setReportVerifierModel,
  planManagerModel,
  setPlanManagerModel,
  codeManagerModel,
  setCodeManagerModel,
  codeAgentModel,
  setCodeAgentModel,
  codeVerifierModel,
  setCodeVerifierModel,
  plannerAgentModel,
  setPlannerAgentModel,
  planVerifierAgentModel,
  setPlanVerifierAgentModel,
  compactionModel,
  setCompactionModel,
  reportManagerIterations,
  setReportManagerIterations,
  planManagerIterations,
  setPlanManagerIterations,
  codeManagerIterations,
  setCodeManagerIterations,
  plannerTimeLimitMinutes,
  setPlannerTimeLimitMinutes,
  orchestratorCompaction,
  setOrchestratorCompaction,
  reportManagerCompaction,
  setReportManagerCompaction,
  reportAgentCompaction,
  setReportAgentCompaction,
  reportVerifierCompaction,
  setReportVerifierCompaction,
  planManagerCompaction,
  setPlanManagerCompaction,
  codeManagerCompaction,
  setCodeManagerCompaction,
  codeAgentCompaction,
  setCodeAgentCompaction,
  codeVerifierCompaction,
  setCodeVerifierCompaction,
  plannerAgentCompaction,
  setPlannerAgentCompaction,
  planVerifierAgentCompaction,
  setPlanVerifierAgentCompaction
}) {
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
        body: JSON.stringify({
          system_description: systemDescription,
          security_alerts: securityAlerts,
          operator_feedback: operatorFeedback
        })
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
      <option value="">Default (Gemini 3.1 Pro)</option>
      {models.map((m) => (
        <option key={m.name} value={m.name}>
          {m.display_name}
        </option>
      ))}
    </>
  )

  const rows = [
    {
      label: 'Orchestrator',
      model: orchestratorModel,
      setModel: setOrchestratorModel,
      promptUrl: API_AGENTS_ORCHESTRATOR_PROMPT_URL,
      iteration: null,
      compaction: orchestratorCompaction,
      setCompaction: setOrchestratorCompaction
    },
    {
      label: 'Report Manager',
      model: reportManagerModel,
      setModel: setReportManagerModel,
      promptUrl: API_AGENTS_REPORT_MANAGER_PROMPT_URL,
      iteration: {
        value: reportManagerIterations,
        set: setReportManagerIterations,
        min: 1,
        max: 10,
        suffix: 'iterations'
      },
      compaction: reportManagerCompaction,
      setCompaction: setReportManagerCompaction
    },
    {
      label: 'Report Agent',
      model: reportAgentModel,
      setModel: setReportAgentModel,
      promptUrl: API_AGENTS_REPORT_PROMPT_URL,
      iteration: null,
      compaction: reportAgentCompaction,
      setCompaction: setReportAgentCompaction
    },
    {
      label: 'Report Verifier',
      model: reportVerifierModel,
      setModel: setReportVerifierModel,
      promptUrl: API_AGENTS_REPORT_REVIEW_PROMPT_URL,
      iteration: null,
      compaction: reportVerifierCompaction,
      setCompaction: setReportVerifierCompaction
    },
    {
      label: 'Plan Manager',
      model: planManagerModel,
      setModel: setPlanManagerModel,
      promptUrl: API_AGENTS_PLAN_MANAGER_PROMPT_URL,
      iteration: {
        value: planManagerIterations,
        set: setPlanManagerIterations,
        min: 1,
        max: 5,
        suffix: 'iterations'
      },
      compaction: planManagerCompaction,
      setCompaction: setPlanManagerCompaction
    },
    {
      label: 'Code Manager',
      model: codeManagerModel,
      setModel: setCodeManagerModel,
      promptUrl: API_AGENTS_CODE_MANAGER_PROMPT_URL,
      iteration: {
        value: codeManagerIterations,
        set: setCodeManagerIterations,
        min: 1,
        max: 10,
        suffix: 'iterations'
      },
      compaction: codeManagerCompaction,
      setCompaction: setCodeManagerCompaction
    },
    {
      label: 'Code Agent',
      model: codeAgentModel,
      setModel: setCodeAgentModel,
      promptUrl: API_AGENTS_CODE_PROMPT_URL,
      iteration: null,
      compaction: codeAgentCompaction,
      setCompaction: setCodeAgentCompaction
    },
    {
      label: 'Code Verifier',
      model: codeVerifierModel,
      setModel: setCodeVerifierModel,
      promptUrl: API_AGENTS_CODE_REVIEW_PROMPT_URL,
      iteration: null,
      compaction: codeVerifierCompaction,
      setCompaction: setCodeVerifierCompaction
    },
    {
      label: 'Planner Agent',
      model: plannerAgentModel,
      setModel: setPlannerAgentModel,
      promptUrl: API_AGENTS_PLANNER_PROMPT_URL,
      iteration: {
        value: plannerTimeLimitMinutes,
        set: setPlannerTimeLimitMinutes,
        min: 1,
        max: 60,
        suffix: 'min time limit'
      },
      compaction: plannerAgentCompaction,
      setCompaction: setPlannerAgentCompaction
    },
    {
      label: 'Plan Verifier Agent',
      model: planVerifierAgentModel,
      setModel: setPlanVerifierAgentModel,
      promptUrl: API_AGENTS_PLAN_VERIFIER_PROMPT_URL,
      iteration: null,
      compaction: planVerifierAgentCompaction,
      setCompaction: setPlanVerifierAgentCompaction
    },
    {
      label: 'Compaction',
      model: compactionModel,
      setModel: setCompactionModel,
      promptUrl: null,
      iteration: null,
      compaction: null,
      setCompaction: null,
      defaultLabel: 'Default (same as agent)'
    }
  ]

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

export default SubAgentsTab
