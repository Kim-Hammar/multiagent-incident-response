/**
 * Renders a table of execution statistics (tokens, function calls, time)
 * for each agent in the orchestrator pipeline, with expandable per-tool
 * breakdown rows.
 */
import { useState } from 'react'

const AGENT_ORDER = [
  'orchestrator',
  'report_manager',
  'report_agent',
  'report_reviewer_agent',
  'pentest_agent',
  'plan_manager',
  'code_manager',
  'code_agent',
  'code_reviewer_agent',
  'planner_agent',
  'validation_agent'
]

function formatAgentName(name) {
  return name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function formatTime(seconds) {
  if (seconds == null || seconds === 0) return '-'
  if (seconds < 60) return `${Math.round(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}m ${s}s`
}

function formatNumber(n) {
  if (n == null || n === 0) return '-'
  return n.toLocaleString()
}

function ExecutionStatsView({ stats }) {
  const [expandedAgents, setExpandedAgents] = useState({})

  if (!stats || !stats.agents) return null

  const agents = stats.agents
  const totals = stats.totals || {}
  const sortedAgents = AGENT_ORDER.filter((name) => agents[name])
  const extraAgents = Object.keys(agents)
    .filter((name) => !AGENT_ORDER.includes(name))
    .sort()
  const allAgents = [...sortedAgents, ...extraAgents]

  if (allAgents.length === 0) return null

  const toggleAgent = (name) => {
    setExpandedAgents((prev) => ({ ...prev, [name]: !prev[name] }))
  }

  return (
    <div className="ia-assessment-section">
      <div className="ia-assessment-label">Execution Statistics</div>
      <div style={{ overflowX: 'auto' }}>
        <table className="table table-sm table-bordered mb-0" style={{ fontSize: '12px' }}>
          <thead>
            <tr>
              <th>Agent</th>
              <th className="text-right">Prompt Tokens</th>
              <th className="text-right">Output Tokens</th>
              <th
                className="text-right"
                title="Sum of prompt (input) tokens and output tokens"
                style={{ cursor: 'help' }}
              >
                Total Tokens
              </th>
              <th className="text-right">Function Calls</th>
              <th className="text-right">LLM Calls</th>
              <th className="text-right">Time</th>
            </tr>
          </thead>
          <tbody>
            {allAgents.map((name) => {
              const a = agents[name]
              const tools = a.tools || {}
              const toolNames = Object.keys(tools).sort()
              const hasTools = toolNames.length > 0
              const isExpanded = !!expandedAgents[name]

              return (
                <>
                  <tr
                    key={name}
                    onClick={hasTools ? () => toggleAgent(name) : undefined}
                    style={hasTools ? { cursor: 'pointer' } : undefined}
                  >
                    <td>
                      {hasTools && (
                        <span style={{ marginRight: '4px', display: 'inline-block', width: '10px' }}>
                          {isExpanded ? '\u25BC' : '\u25B6'}
                        </span>
                      )}
                      {!hasTools && (
                        <span style={{ marginRight: '4px', display: 'inline-block', width: '10px' }} />
                      )}
                      {formatAgentName(name)}
                    </td>
                    <td className="text-right">{formatNumber(a.prompt_tokens)}</td>
                    <td className="text-right">{formatNumber(a.candidates_tokens)}</td>
                    <td className="text-right">{formatNumber(a.total_tokens)}</td>
                    <td className="text-right">{formatNumber(a.function_calls)}</td>
                    <td className="text-right">{formatNumber(a.steps)}</td>
                    <td className="text-right">{formatTime(a.wall_time_seconds)}</td>
                  </tr>
                  {isExpanded &&
                    toolNames.map((toolName) => {
                      const t = tools[toolName]
                      return (
                        <tr
                          key={`${name}-${toolName}`}
                          style={{ background: '#f8f9fa', fontSize: '11px' }}
                        >
                          <td style={{ paddingLeft: '28px' }}>
                            <code>{toolName}</code>
                          </td>
                          <td className="text-right">{formatNumber(t.prompt_tokens)}</td>
                          <td className="text-right">{formatNumber(t.candidates_tokens)}</td>
                          <td className="text-right">{formatNumber(t.total_tokens)}</td>
                          <td className="text-right">{formatNumber(t.calls)}</td>
                          <td className="text-right">-</td>
                          <td className="text-right">-</td>
                        </tr>
                      )
                    })}
                </>
              )
            })}
          </tbody>
          <tfoot>
            <tr style={{ fontWeight: 'bold' }}>
              <td>Total</td>
              <td className="text-right">{formatNumber(totals.prompt_tokens)}</td>
              <td className="text-right">{formatNumber(totals.candidates_tokens)}</td>
              <td className="text-right">{formatNumber(totals.total_tokens)}</td>
              <td className="text-right">{formatNumber(totals.function_calls)}</td>
              <td className="text-right">{formatNumber(totals.steps)}</td>
              <td className="text-right">{formatTime(stats.total_wall_time_seconds)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}

export default ExecutionStatsView
