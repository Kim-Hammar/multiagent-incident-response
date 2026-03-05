import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import ElapsedTimer from './ElapsedTimer.jsx'
import PromptModal from './PromptModal.jsx'
import ContextModal from './ContextModal.jsx'
import RewardChart from '../RewardChart.jsx'
import RlTrainResult from '../RlTrainResult.jsx'
import { formatToolArgs, toolLabel, toolIcon } from './toolUtils.js'
import {
  CodeReportBody,
  ReviewReportBody,
  AssessmentBody,
  IncidentReviewBody,
  PlanVerifierReportBody,
  PlanManagerReportBody,
  PentestReportBody,
  HostAnalysisBody,
  ActionVerificationBody,
  ACTION_OUTCOME_STYLES
} from './ReportBodies.jsx'
import PlannerAgentReport from '../PlannerAgentReport.jsx'
import CopyablePre from './CopyablePre.jsx'

const RL_STREAMING_TYPES = new Set(['progress', 'eval_progress', 'started', 'result', 'timeout'])

const ORCHESTRATOR_TOOLS = new Set([
  'run_code_agent',
  'run_code_verifier_agent',
  'produce_orchestrator_report',
  'run_code_manager',
  'run_planner_agent',
  'run_plan_verifier_agent',
  'produce_plan_manager_report',
  'run_report_agent',
  'run_report_verifier_agent',
  'produce_report_manager_report',
  'run_report_manager',
  'run_pentest_agent',
  'run_plan_manager',
  'produce_orchestrator_agent_report',
  'run_host_analyzers',
  'run_action_verifiers'
])

const TOOL_LABELS = {
  produce_assessment: 'assessment report',
  produce_plan_verifier_report: 'plan verifier report',
  produce_code_report: 'code report',
  produce_code_review: 'code review',
  produce_plan: 'plan',
  produce_rl_report: 'RL report',
  produce_orchestrator_report: 'orchestrator report',
  produce_orchestrator_agent_report: 'orchestrator report',
  produce_report_manager_report: 'report manager report',
  produce_plan_manager_report: 'plan manager report',
  produce_pentest_report: 'pentest report',
  produce_host_analysis: 'host analysis report',
  produce_action_verification: 'action verification report',
  run_host_analyzers: 'parallel host analysis',
  run_action_verifiers: 'parallel action verification'
}

/**
 * A collapsible section with a clickable header.
 */
function CollapsibleSection({ label, icon, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="ia-collapsible-section">
      <div className="ia-collapsible-header" onClick={() => setOpen(!open)}>
        <i className={`fa ${open ? 'fa-chevron-down' : 'fa-chevron-right'}`} aria-hidden="true" />
        {icon && <i className={`fa ${icon}`} aria-hidden="true" />}
        <span>{label}</span>
        <span className="ia-toggle-hint">{open ? 'collapse' : 'expand'}</span>
      </div>
      {open && <div className="ia-collapsible-content">{children}</div>}
    </div>
  )
}

/**
 * Render structured, collapsible args for orchestrator sub-agent tools.
 */
function renderOrchestratorArgs(toolName, args) {
  if (toolName === 'run_code_agent') {
    if (!args?.previous_code && !args?.review_feedback) {
      return (
        <div className="ia-orchestrator-args">
          <div className="ia-orchestrator-note">
            <i className="fa fa-info-circle" aria-hidden="true" />
            <span>Initial code generation — no prior code or review feedback</span>
          </div>
        </div>
      )
    }
    return (
      <div className="ia-orchestrator-args">
        {args.review_feedback && (
          <CollapsibleSection label="Review Feedback" icon="fa-comments">
            {(() => {
              try {
                const parsed =
                  typeof args.review_feedback === 'string'
                    ? JSON.parse(args.review_feedback)
                    : args.review_feedback
                if (parsed && typeof parsed === 'object' && parsed.findings) {
                  return <ReviewReportBody report={parsed} />
                }
              } catch {
                /* not JSON — fall through */
              }
              return (
                <div className="ia-arg-markdown">
                  <ReactMarkdown>{args.review_feedback}</ReactMarkdown>
                </div>
              )
            })()}
          </CollapsibleSection>
        )}
        {args.previous_code && (
          <CollapsibleSection
            label={`Previous Code (${args.previous_code.split('\n').length} lines)`}
            icon="fa-code"
          >
            <CopyablePre className="ia-arg-code" text={args.previous_code}>
              {args.previous_code}
            </CopyablePre>
          </CollapsibleSection>
        )}
      </div>
    )
  }

  if (toolName === 'run_code_verifier_agent') {
    return (
      <div className="ia-orchestrator-args">
        <div className="ia-orchestrator-note">
          <i className="fa fa-info-circle" aria-hidden="true" />
          <span>Code report extracted from conversation history</span>
        </div>
      </div>
    )
  }

  if (toolName === 'produce_orchestrator_report') {
    return (
      <div className="ia-orchestrator-args">
        {args.final_verdict && (
          <div className="ia-orchestrator-verdict-row">
            <span className="ia-proposal-arg-label">Verdict:</span>
            <span
              className={`badge badge-${args.final_verdict === 'pass' ? 'success' : args.final_verdict === 'major_issues' ? 'danger' : 'warning'}`}
            >
              {args.final_verdict}
            </span>
          </div>
        )}
        {args.iterations != null && (
          <div className="ia-orchestrator-verdict-row">
            <span className="ia-proposal-arg-label">Iterations:</span>
            <span className="ia-proposal-arg-value">{args.iterations}</span>
          </div>
        )}
        {args.executive_summary && (
          <CollapsibleSection label="Executive Summary" icon="fa-file-text" defaultOpen>
            <div className="ia-arg-markdown">
              <ReactMarkdown>{args.executive_summary}</ReactMarkdown>
            </div>
          </CollapsibleSection>
        )}
        {args.code_report_summary && (
          <CollapsibleSection label="Code Report Summary" icon="fa-code">
            <div className="ia-arg-markdown">
              <ReactMarkdown>{args.code_report_summary}</ReactMarkdown>
            </div>
          </CollapsibleSection>
        )}
        {args.review_report_summary && (
          <CollapsibleSection label="Review Report Summary" icon="fa-search">
            <div className="ia-arg-markdown">
              <ReactMarkdown>{args.review_report_summary}</ReactMarkdown>
            </div>
          </CollapsibleSection>
        )}
      </div>
    )
  }

  if (toolName === 'run_code_manager') {
    if (!args?.validation_feedback) {
      return (
        <div className="ia-orchestrator-args">
          <div className="ia-orchestrator-note">
            <i className="fa fa-info-circle" aria-hidden="true" />
            <span>Initial code generation — no validation feedback</span>
          </div>
        </div>
      )
    }
    return (
      <div className="ia-orchestrator-args">
        <CollapsibleSection label="Validation Feedback" icon="fa-comments">
          <div className="ia-arg-markdown">
            <ReactMarkdown>{args.validation_feedback}</ReactMarkdown>
          </div>
        </CollapsibleSection>
      </div>
    )
  }

  if (toolName === 'run_planner_agent' || toolName === 'run_plan_verifier_agent') {
    return (
      <div className="ia-orchestrator-args">
        <div className="ia-orchestrator-note">
          <i className="fa fa-info-circle" aria-hidden="true" />
          <span>Context extracted from conversation history</span>
        </div>
      </div>
    )
  }

  if (toolName === 'produce_plan_manager_report') {
    return (
      <div className="ia-orchestrator-args">
        {args.final_verdict && (
          <div className="ia-orchestrator-verdict-row">
            <span className="ia-proposal-arg-label">Verdict:</span>
            <span
              className={`badge badge-${args.final_verdict === 'pass' ? 'success' : args.final_verdict === 'major_issues' ? 'danger' : 'warning'}`}
            >
              {args.final_verdict}
            </span>
          </div>
        )}
        {args.iterations != null && (
          <div className="ia-orchestrator-verdict-row">
            <span className="ia-proposal-arg-label">Iterations:</span>
            <span className="ia-proposal-arg-value">{args.iterations}</span>
          </div>
        )}
        {args.executive_summary && (
          <CollapsibleSection label="Executive Summary" icon="fa-file-text" defaultOpen>
            <div className="ia-arg-markdown">
              <ReactMarkdown>{args.executive_summary}</ReactMarkdown>
            </div>
          </CollapsibleSection>
        )}
        {args.code_manager_summary && (
          <CollapsibleSection label="Code Manager Summary" icon="fa-cogs">
            <div className="ia-arg-markdown">
              <ReactMarkdown>{args.code_manager_summary}</ReactMarkdown>
            </div>
          </CollapsibleSection>
        )}
        {args.planner_agent_summary && (
          <CollapsibleSection label="Planner Agent Summary" icon="fa-line-chart">
            <div className="ia-arg-markdown">
              <ReactMarkdown>{args.planner_agent_summary}</ReactMarkdown>
            </div>
          </CollapsibleSection>
        )}
        {args.verification_summary && (
          <CollapsibleSection label="Verification Summary" icon="fa-check-circle">
            <div className="ia-arg-markdown">
              <ReactMarkdown>{args.verification_summary}</ReactMarkdown>
            </div>
          </CollapsibleSection>
        )}
      </div>
    )
  }

  if (toolName === 'run_report_agent') {
    if (!args?.previous_assessment && !args?.review_feedback) {
      return (
        <div className="ia-orchestrator-args">
          <div className="ia-orchestrator-note">
            <i className="fa fa-info-circle" aria-hidden="true" />
            <span>Initial report generation — no prior assessment or review feedback</span>
          </div>
        </div>
      )
    }
    return (
      <div className="ia-orchestrator-args">
        {args.review_feedback && (
          <CollapsibleSection label="Review Feedback" icon="fa-comments">
            {(() => {
              try {
                const parsed =
                  typeof args.review_feedback === 'string'
                    ? JSON.parse(args.review_feedback)
                    : args.review_feedback
                if (parsed && typeof parsed === 'object' && parsed.findings) {
                  return <IncidentReviewBody report={parsed} />
                }
              } catch {
                /* not JSON — fall through */
              }
              return (
                <div className="ia-arg-markdown">
                  <ReactMarkdown>{args.review_feedback}</ReactMarkdown>
                </div>
              )
            })()}
          </CollapsibleSection>
        )}
        {args.previous_assessment && (
          <CollapsibleSection label="Previous Assessment" icon="fa-file-text">
            {(() => {
              try {
                const parsed =
                  typeof args.previous_assessment === 'string'
                    ? JSON.parse(args.previous_assessment)
                    : args.previous_assessment
                if (parsed && typeof parsed === 'object') {
                  return <AssessmentBody report={parsed} />
                }
              } catch {
                /* not JSON — fall through */
              }
              return (
                <div className="ia-arg-markdown">
                  <ReactMarkdown>{args.previous_assessment}</ReactMarkdown>
                </div>
              )
            })()}
          </CollapsibleSection>
        )}
      </div>
    )
  }

  if (toolName === 'run_report_verifier_agent') {
    return (
      <div className="ia-orchestrator-args">
        <div className="ia-orchestrator-note">
          <i className="fa fa-info-circle" aria-hidden="true" />
          <span>Incident report and images extracted from conversation history</span>
        </div>
        {args.previous_review_summary && (
          <CollapsibleSection label="Previous Review Summary" icon="fa-search">
            <div className="ia-arg-markdown">
              <ReactMarkdown>{args.previous_review_summary}</ReactMarkdown>
            </div>
          </CollapsibleSection>
        )}
      </div>
    )
  }

  if (toolName === 'produce_report_manager_report') {
    return (
      <div className="ia-orchestrator-args">
        {args.final_verdict && (
          <div className="ia-orchestrator-verdict-row">
            <span className="ia-proposal-arg-label">Verdict:</span>
            <span
              className={`badge badge-${args.final_verdict === 'pass' ? 'success' : args.final_verdict === 'major_issues' ? 'danger' : 'warning'}`}
            >
              {args.final_verdict}
            </span>
          </div>
        )}
        {args.iterations != null && (
          <div className="ia-orchestrator-verdict-row">
            <span className="ia-proposal-arg-label">Iterations:</span>
            <span className="ia-proposal-arg-value">{args.iterations}</span>
          </div>
        )}
        {args.executive_summary && (
          <CollapsibleSection label="Executive Summary" icon="fa-file-text" defaultOpen>
            <div className="ia-arg-markdown">
              <ReactMarkdown>{args.executive_summary}</ReactMarkdown>
            </div>
          </CollapsibleSection>
        )}
        {args.report_summary && (
          <CollapsibleSection label="Report Summary" icon="fa-file-text-o">
            <div className="ia-arg-markdown">
              <ReactMarkdown>{args.report_summary}</ReactMarkdown>
            </div>
          </CollapsibleSection>
        )}
        {args.review_summary && (
          <CollapsibleSection label="Review Summary" icon="fa-search">
            <div className="ia-arg-markdown">
              <ReactMarkdown>{args.review_summary}</ReactMarkdown>
            </div>
          </CollapsibleSection>
        )}
      </div>
    )
  }

  if (toolName === 'run_host_analyzers') {
    const hosts = args?.hosts || []
    return (
      <div className="ia-orchestrator-args">
        <div className="ia-orchestrator-note">
          <i className="fa fa-server" aria-hidden="true" />
          <span>
            Analyzing {hosts.length} host{hosts.length !== 1 ? 's' : ''} in parallel
          </span>
        </div>
        {hosts.length > 0 && (
          <div style={{ marginTop: '6px' }}>
            {hosts.map((h, i) => (
              <div key={i} className="ia-orchestrator-verdict-row">
                <span className="ia-proposal-arg-label">{h.host_id}:</span>
                <span className="ia-proposal-arg-value">{h.host_description}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  if (toolName === 'run_action_verifiers') {
    const actions = args?.actions || []
    return (
      <div className="ia-orchestrator-args">
        <div className="ia-orchestrator-note">
          <i className="fa fa-check-circle" aria-hidden="true" />
          <span>
            Validating {actions.length} action{actions.length !== 1 ? 's' : ''} in parallel
          </span>
        </div>
        {actions.length > 0 && (
          <div style={{ marginTop: '6px' }}>
            {actions.map((a, i) => (
              <div key={i} className="ia-orchestrator-verdict-row">
                <span className="ia-proposal-arg-label">{a.action_name}:</span>
                <span className="ia-proposal-arg-value">{a.action_description}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  if (toolName === 'run_report_manager') {
    return (
      <div className="ia-orchestrator-args">
        <div className="ia-orchestrator-note">
          <i className="fa fa-info-circle" aria-hidden="true" />
          <span>Assessment generation — no prior feedback</span>
        </div>
      </div>
    )
  }

  if (toolName === 'run_pentest_agent') {
    return (
      <div className="ia-orchestrator-args">
        <div className="ia-orchestrator-note">
          <i className="fa fa-info-circle" aria-hidden="true" />
          <span>Attack path validation against digital twin</span>
        </div>
      </div>
    )
  }

  if (toolName === 'run_plan_manager') {
    return (
      <div className="ia-orchestrator-args">
        <div className="ia-orchestrator-note">
          <i className="fa fa-info-circle" aria-hidden="true" />
          <span>Response plan generation</span>
        </div>
      </div>
    )
  }

  if (toolName === 'produce_orchestrator_agent_report') {
    return (
      <div className="ia-orchestrator-args">
        {args.final_verdict && (
          <div className="ia-orchestrator-verdict-row">
            <span className="ia-proposal-arg-label">Verdict:</span>
            <span
              className={`badge badge-${args.final_verdict === 'pass' ? 'success' : args.final_verdict === 'major_issues' ? 'danger' : 'warning'}`}
            >
              {args.final_verdict}
            </span>
          </div>
        )}
        {args.iterations != null && (
          <div className="ia-orchestrator-verdict-row">
            <span className="ia-proposal-arg-label">Iterations:</span>
            <span className="ia-proposal-arg-value">{args.iterations}</span>
          </div>
        )}
        {args.executive_summary && (
          <CollapsibleSection label="Executive Summary" icon="fa-file-text" defaultOpen>
            <div className="ia-arg-markdown">
              <ReactMarkdown>{args.executive_summary}</ReactMarkdown>
            </div>
          </CollapsibleSection>
        )}
        {args.assessment_summary && (
          <CollapsibleSection label="Assessment Summary" icon="fa-clipboard">
            <div className="ia-arg-markdown">
              <ReactMarkdown>{args.assessment_summary}</ReactMarkdown>
            </div>
          </CollapsibleSection>
        )}
        {args.response_plan_summary && (
          <CollapsibleSection label="Response Plan Summary" icon="fa-shield">
            <div className="ia-arg-markdown">
              <ReactMarkdown>{args.response_plan_summary}</ReactMarkdown>
            </div>
          </CollapsibleSection>
        )}
      </div>
    )
  }

  return null
}

const TERMINAL_TOOLS = new Set(['dt_exec', 'python_exec', 'dt_python_exec', 'rl_train'])

function renderTerminalResult(toolName, result) {
  if (!result || typeof result !== 'object') return null

  if (toolName === 'gym_verify' && 'valid' in result) {
    return (
      <div className="ia-terminal-result">
        <div className="ia-terminal-meta">
          <span className={`badge badge-${result.valid ? 'success' : 'danger'}`}>
            {result.valid ? 'Valid' : 'Invalid'}
          </span>
        </div>
        {result.checks && result.checks.length > 0 && (
          <ul className="ia-gym-checks">
            {result.checks.map((check, i) => (
              <li key={i} className={check.passed ? 'passed' : 'failed'}>
                {check.passed ? '\u2713' : '\u2717'}{' '}
                {check.name ||
                  check.description ||
                  check.check ||
                  check.detail ||
                  (typeof check === 'string' ? check : JSON.stringify(check))}
              </li>
            ))}
          </ul>
        )}
        {result.error && (
          <CopyablePre className="ia-terminal-output error" text={result.error}>
            {result.error}
          </CopyablePre>
        )}
      </div>
    )
  }

  if (!TERMINAL_TOOLS.has(toolName) || !('exit_code' in result)) return null

  return (
    <div className="ia-terminal-result">
      <div className="ia-terminal-meta">
        {result.container && (
          <span className="ia-terminal-container">
            <i className="fa fa-server" aria-hidden="true" /> {result.container}
          </span>
        )}
        <span className={`badge badge-${result.exit_code === 0 ? 'success' : 'danger'}`}>
          exit {result.exit_code}
        </span>
      </div>
      {result.output != null && result.output !== '' ? (
        <CopyablePre className="ia-terminal-output" text={result.output}>
          {result.output}
        </CopyablePre>
      ) : (
        <span className="ia-terminal-empty">(no output)</span>
      )}
    </div>
  )
}

/**
 * Render a structured report from a sub-agent tool result
 * (code_report, review_report, orchestrator_report, etc.)
 * instead of falling back to raw JSON.
 */
function renderSubAgentReport(toolName, result) {
  if (!result || typeof result !== 'object') return null

  if (toolName === 'run_code_agent' && result.code_report) {
    return <CodeReportBody report={result.code_report} />
  }
  if (toolName === 'run_code_verifier_agent' && result.review_report) {
    return <ReviewReportBody report={result.review_report} />
  }
  if (toolName === 'run_code_manager' && result.orchestrator_report) {
    const r = result.orchestrator_report
    return (
      <div style={{ marginTop: '10px' }}>
        {r.executive_summary && (
          <div className="ia-assessment-section">
            <div className="ia-assessment-label">Code Manager Summary</div>
            <p className="ia-assessment-body mb-0">{r.executive_summary}</p>
          </div>
        )}
        {result.code_report && (
          <div className="ia-assessment-section">
            <div className="ia-assessment-label">Final Code Report</div>
            <CodeReportBody report={result.code_report} />
          </div>
        )}
      </div>
    )
  }
  if (toolName === 'run_planner_agent' && result.planner_report) {
    return (
      <PlannerAgentReport
        entry={{ type: 'planner_report', planner_report: result.planner_report }}
        index="sub-planner"
        isExpanded={true}
        toggleEntry={() => {}}
      />
    )
  }
  if (toolName === 'run_plan_verifier_agent' && result.plan_verifier_report) {
    return <PlanVerifierReportBody report={result.plan_verifier_report} />
  }
  if (toolName === 'run_report_agent' && result.assessment) {
    const assessment = result.attack_path_image
      ? { ...result.assessment, attack_path_image: result.attack_path_image }
      : result.assessment
    return <AssessmentBody report={assessment} />
  }
  if (toolName === 'run_report_verifier_agent' && result.report_review) {
    return <IncidentReviewBody report={result.report_review} />
  }
  if (toolName === 'run_report_manager' && result.report_manager_report) {
    const r = result.report_manager_report
    return (
      <div style={{ marginTop: '10px' }}>
        {r.executive_summary && (
          <div className="ia-assessment-section">
            <div className="ia-assessment-label">Report Manager Summary</div>
            <p className="ia-assessment-body mb-0">{r.executive_summary}</p>
          </div>
        )}
        {result.assessment && (
          <div className="ia-assessment-section">
            <div className="ia-assessment-label">Final Assessment</div>
            <AssessmentBody
              report={
                result.attack_path_image
                  ? { ...result.assessment, attack_path_image: result.attack_path_image }
                  : result.assessment
              }
            />
          </div>
        )}
      </div>
    )
  }
  if (toolName === 'run_pentest_agent' && result.pentest_report) {
    return <PentestReportBody report={result.pentest_report} />
  }
  if (toolName === 'run_plan_manager' && result.plan_manager_report) {
    return <PlanManagerReportBody result={result} />
  }
  if (toolName === 'run_host_analyzers' && result.host_analyses) {
    const analyses = result.host_analyses
    return (
      <div style={{ marginTop: '10px' }}>
        {Object.entries(analyses).map(([hostId, analysis]) => (
          <CollapsibleSection key={hostId} label={`Analysis of host ${hostId}`} icon="fa-server">
            <HostAnalysisBody report={analysis} />
          </CollapsibleSection>
        ))}
      </div>
    )
  }
  if (toolName === 'run_action_verifiers' && result.action_verifications) {
    const verifications = result.action_verifications
    return (
      <div style={{ marginTop: '10px' }}>
        {Object.entries(verifications).map(([actionId, verification]) => (
          <CollapsibleSection
            key={actionId}
            label={`Verification of ${actionId}`}
            icon="fa-check-circle"
          >
            {verification.error ? (
              <div className="text-danger">{verification.error}</div>
            ) : (
              <ActionVerificationBody report={verification} />
            )}
          </CollapsibleSection>
        ))}
      </div>
    )
  }
  return null
}

const SEARCH_TOOLS = new Set([
  'tavily_search',
  'nvd_search',
  'mitre_search',
  'virustotal_scan',
  'abuseipdb_check',
  'otx_search'
])

/**
 * Render structured results for search / threat-intel tools
 * instead of falling back to raw JSON.
 */
function renderSearchToolResult(toolName, result) {
  if (!result || typeof result !== 'object') return null
  if (!SEARCH_TOOLS.has(toolName)) return null

  if (toolName === 'tavily_search') {
    const items = result.results || []
    return (
      <div className="ia-search-results" style={{ marginTop: '8px' }}>
        {result.query && (
          <div style={{ fontSize: '11px', color: '#666', marginBottom: '6px' }}>
            Query: <strong>{result.query}</strong>
            {result.response_time != null && <span> ({result.response_time}s)</span>}
          </div>
        )}
        {items.length === 0 && <div className="text-muted">No results found.</div>}
        {items.map((r, i) => (
          <div key={i} className="ia-assessment-section" style={{ marginBottom: '8px' }}>
            <div className="ia-assessment-label" style={{ display: 'flex', alignItems: 'center' }}>
              <a href={r.url} target="_blank" rel="noopener noreferrer">
                {r.title || r.url}
              </a>
              {r.score != null && (
                <span className="badge badge-secondary ml-2" style={{ fontSize: '10px' }}>
                  {Math.round(r.score * 100)}%
                </span>
              )}
            </div>
            {r.content && <p className="ia-assessment-body mb-0">{r.content}</p>}
          </div>
        ))}
      </div>
    )
  }

  if (toolName === 'nvd_search') {
    const items = result.results || []
    return (
      <div className="ia-search-results" style={{ marginTop: '8px' }}>
        {result.query && (
          <div style={{ fontSize: '11px', color: '#666', marginBottom: '6px' }}>
            Query: <strong>{result.query}</strong>
          </div>
        )}
        {items.length === 0 && <div className="text-muted">No results found.</div>}
        {items.map((r, i) => (
          <div key={i} className="ia-assessment-section" style={{ marginBottom: '8px' }}>
            <div className="ia-assessment-label" style={{ display: 'flex', alignItems: 'center' }}>
              <a href={r.url} target="_blank" rel="noopener noreferrer">
                {r.id}
              </a>
              {r.score != null && (
                <span
                  className={`badge badge-${r.score >= 9 ? 'danger' : r.score >= 7 ? 'warning' : r.score >= 4 ? 'info' : 'success'} ml-2`}
                  style={{ fontSize: '10px' }}
                >
                  CVSS {r.score}
                </span>
              )}
            </div>
            {r.description && <p className="ia-assessment-body mb-0">{r.description}</p>}
            {r.published && (
              <div style={{ fontSize: '10px', color: '#888', marginTop: '2px' }}>
                Published: {r.published}
              </div>
            )}
          </div>
        ))}
      </div>
    )
  }

  if (toolName === 'mitre_search') {
    const items = result.results || []
    return (
      <div className="ia-search-results" style={{ marginTop: '8px' }}>
        {result.query && (
          <div style={{ fontSize: '11px', color: '#666', marginBottom: '6px' }}>
            Query: <strong>{result.query}</strong>
          </div>
        )}
        {items.length === 0 && <div className="text-muted">No results found.</div>}
        {items.map((r, i) => (
          <div key={i} className="ia-assessment-section" style={{ marginBottom: '8px' }}>
            <div className="ia-assessment-label" style={{ display: 'flex', alignItems: 'center' }}>
              <a href={r.url} target="_blank" rel="noopener noreferrer">
                {r.id} — {r.name}
              </a>
            </div>
            {r.tactics && r.tactics.length > 0 && (
              <div style={{ marginBottom: '4px' }}>
                {r.tactics.map((t, j) => (
                  <span key={j} className="badge badge-dark mr-1" style={{ fontSize: '10px' }}>
                    {t}
                  </span>
                ))}
              </div>
            )}
            {r.description && <p className="ia-assessment-body mb-0">{r.description}</p>}
          </div>
        ))}
      </div>
    )
  }

  if (toolName === 'virustotal_scan') {
    const r = result.result || {}
    const stats = r.last_analysis_stats || {}
    return (
      <div className="ia-search-results" style={{ marginTop: '8px' }}>
        <div style={{ fontSize: '11px', color: '#666', marginBottom: '6px' }}>
          <strong>{r.type}</strong>: {r.value}
        </div>
        {r.reputation != null && (
          <div className="ia-assessment-section">
            <div className="ia-assessment-label">Reputation</div>
            <span
              className={`badge badge-${r.reputation < 0 ? 'danger' : r.reputation === 0 ? 'secondary' : 'success'}`}
            >
              {r.reputation}
            </span>
          </div>
        )}
        {Object.keys(stats).length > 0 && (
          <div className="ia-assessment-section">
            <div className="ia-assessment-label">Analysis Stats</div>
            <div>
              {Object.entries(stats).map(([k, v]) => (
                <span key={k} className="mr-2" style={{ fontSize: '12px' }}>
                  <span
                    className={`badge badge-${k === 'malicious' ? 'danger' : k === 'suspicious' ? 'warning' : k === 'harmless' ? 'success' : 'secondary'}`}
                  >
                    {k}: {v}
                  </span>
                </span>
              ))}
            </div>
          </div>
        )}
        {r.last_analysis_date && (
          <div style={{ fontSize: '10px', color: '#888', marginTop: '4px' }}>
            Last analysis: {r.last_analysis_date}
          </div>
        )}
      </div>
    )
  }

  if (toolName === 'abuseipdb_check') {
    const r = result.result || {}
    const score = r.abuse_confidence_score
    return (
      <div className="ia-search-results" style={{ marginTop: '8px' }}>
        <div style={{ fontSize: '11px', color: '#666', marginBottom: '6px' }}>
          IP: <strong>{r.ip}</strong>
          {r.country_code && <span> ({r.country_code})</span>}
          {r.isp && <span> — {r.isp}</span>}
        </div>
        {score != null && (
          <div className="ia-assessment-section">
            <div className="ia-assessment-label">Abuse Confidence Score</div>
            <span
              className={`badge badge-${score >= 80 ? 'danger' : score >= 40 ? 'warning' : score > 0 ? 'info' : 'success'}`}
              style={{ fontSize: '14px', padding: '4px 10px' }}
            >
              {score}%
            </span>
          </div>
        )}
        <div style={{ fontSize: '12px', marginTop: '4px' }}>
          <span className="mr-3">
            Total reports: <strong>{r.total_reports || 0}</strong>
          </span>
          {r.last_reported_at && <span>Last reported: {r.last_reported_at}</span>}
        </div>
      </div>
    )
  }

  if (toolName === 'otx_search') {
    const r = result.result || {}
    const pulses = r.pulses || []
    return (
      <div className="ia-search-results" style={{ marginTop: '8px' }}>
        <div style={{ fontSize: '11px', color: '#666', marginBottom: '6px' }}>
          <strong>{r.type}</strong>: {r.value}
          {r.pulse_count != null && <span> — {r.pulse_count} pulse(s)</span>}
        </div>
        {pulses.length > 0 && (
          <div className="ia-assessment-section">
            <div className="ia-assessment-label">Threat Pulses</div>
            {pulses.map((p, j) => (
              <div key={j} style={{ marginBottom: '6px' }}>
                <div style={{ fontWeight: 600, fontSize: '12px' }}>{p.name || p.id}</div>
                {p.description && (
                  <p className="ia-assessment-body mb-0" style={{ fontSize: '12px' }}>
                    {p.description}
                  </p>
                )}
                {p.tags && p.tags.length > 0 && (
                  <div style={{ marginTop: '2px' }}>
                    {p.tags.map((t, k) => (
                      <span
                        key={k}
                        className="badge badge-secondary mr-1"
                        style={{ fontSize: '9px' }}
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  return null
}

/**
 * Accumulate streaming deltas into display-ready entries.
 * Consecutive `thinking_delta` events merge into a single `reasoning` entry,
 * consecutive `text_delta` events merge into a single `text` entry.
 * Other event types pass through unchanged with `_startTime` set from `_ts`.
 */
function accumulateSubEvents(events) {
  const result = []
  for (const ev of events) {
    if (ev.type === 'thinking_delta') {
      const last = result[result.length - 1]
      if (last && last.type === 'reasoning') {
        last.text += ev.text || ''
      } else {
        result.push({
          ...ev,
          type: 'reasoning',
          text: ev.text || '',
          _startTime: ev._ts || Date.now()
        })
      }
    } else if (ev.type === 'text_delta') {
      const last = result[result.length - 1]
      if (last && last.type === 'text') {
        last.text += ev.text || ''
      } else {
        result.push({
          ...ev,
          type: 'text',
          text: ev.text || '',
          _startTime: ev._ts || Date.now()
        })
      }
    } else {
      result.push({ ...ev, _startTime: ev._ts || ev._startTime })
    }
  }
  return result
}

/**
 * Render parallel sub-agent events grouped by agent_id.
 * Each agent gets its own CollapsibleSection with a status indicator.
 */
function ParallelSubAgentLog({
  hosts,
  subEvents,
  active,
  onViewPrompt,
  onViewContext,
  livenessStatus,
  heartbeatStatus,
  lastHeartbeatTime
}) {
  const grouped = {}
  const doneSet = new Set()
  for (const ev of subEvents || []) {
    const aid = ev.agent_id
    if (!aid) continue
    if (ev.type === 'agent_done') {
      doneSet.add(aid)
      continue
    }
    if (!grouped[aid]) grouped[aid] = []
    grouped[aid].push(ev)
  }
  const hostList = hosts || Object.keys(grouped).map((id) => ({ agent_id: id, agent_label: id }))

  return (
    <div className="ia-sub-agent-log" style={{ marginTop: '8px' }}>
      {hostList.map((h) => {
        const aid = h.agent_id
        const isDone = doneSet.has(aid)
        const events = grouped[aid] || []
        const icon = isDone ? 'fa-check-circle' : active ? 'fa-spinner fa-spin' : 'fa-circle-o'
        const promptEv = [...events].reverse().find((e) => e.type === 'prompt')
        const ctxEv = [...events].reverse().find((e) => e.type === 'context_usage')
        const modelEv = [...events].reverse().find((e) => e.type === 'model_name')
        const accumulated = accumulateSubEvents(events)
        const displayEvents = accumulated.filter(
          (e) => e.type !== 'prompt' && e.type !== 'context_usage' && e.type !== 'model_name'
        )
        return (
          <CollapsibleSection
            key={aid}
            label={h.agent_label || aid}
            icon={icon}
            defaultOpen={!isDone && active}
          >
            {promptEv && onViewPrompt && (
              <div style={{ marginBottom: '6px' }}>
                <button
                  type="button"
                  className="btn btn-outline-dark btn-sm"
                  style={{ fontSize: '10px', padding: '1px 8px' }}
                  onClick={() => onViewPrompt(promptEv.text, promptEv.images || [])}
                >
                  <i className="fa fa-file-text-o" aria-hidden="true" /> Prompt
                </button>
                {onViewContext && events.length > 0 && (
                  <button
                    type="button"
                    className="btn btn-outline-dark btn-sm"
                    style={{ fontSize: '10px', padding: '1px 8px', marginLeft: '4px' }}
                    onClick={() => onViewContext(events)}
                  >
                    <i className="fa fa-database" aria-hidden="true" /> Context
                  </button>
                )}
              </div>
            )}
            {displayEvents.length > 0 ? (
              <SubAgentLog
                subEvents={displayEvents}
                agentLabel={h.agent_label || aid}
                active={active && !isDone}
                modelName={modelEv?.model_name}
                contextUsage={ctxEv}
                onViewPrompt={onViewPrompt}
                onViewContext={onViewContext}
                livenessStatus={livenessStatus}
                heartbeatStatus={heartbeatStatus}
                lastHeartbeatTime={lastHeartbeatTime}
              />
            ) : (
              <div className="ia-sub-entry">
                <i className="fa fa-hourglass-half" aria-hidden="true" />
                <span style={{ marginLeft: '6px', opacity: 0.6 }}>Waiting to start...</span>
              </div>
            )}
          </CollapsibleSection>
        )
      })}
    </div>
  )
}

/**
 * Render sub-agent activity events inside a nested container.
 */
function SubAgentLog({
  subEvents,
  agentLabel,
  active,
  modelName,
  onViewPrompt,
  onViewContext,
  contextUsage,
  livenessStatus,
  heartbeatStatus,
  lastHeartbeatTime
}) {
  const [expanded, setExpanded] = useState({})
  const toggle = (i, value) =>
    setExpanded((prev) => ({ ...prev, [i]: value !== undefined ? value : !prev[i] }))
  const statusText =
    heartbeatStatus ||
    (livenessStatus === 'alive' ? 'Connected' : livenessStatus === 'error' ? 'Error' : 'No signal')
  const timeStr = lastHeartbeatTime ? new Date(lastHeartbeatTime).toLocaleTimeString() : ''
  const dotTooltip = timeStr ? `${statusText} (${timeStr})` : statusText

  if (!subEvents || subEvents.length === 0) return null

  const lastIndex = subEvents.length - 1

  const progressData = subEvents.filter((e) => e.type === 'progress')
  const lastEvalProgress = subEvents.filter((e) => e.type === 'eval_progress').pop() || null

  return (
    <div className="ia-sub-agent-log">
      <div className="ia-sub-agent-header">
        <i className="fa fa-sitemap" aria-hidden="true" />
        <span>{agentLabel} activity</span>
        {modelName && (
          <span style={{ fontSize: '10px', color: '#888', marginLeft: '8px' }}>
            <i className="fa fa-microchip" aria-hidden="true" /> {modelName}
          </span>
        )}
        {contextUsage && contextUsage.context_limit > 0 && (
          <span
            className={`ia-context-indicator${contextUsage.total_tokens / contextUsage.context_limit > 0.8 ? ' high-usage' : ''}`}
            style={{ marginLeft: '8px' }}
          >
            {contextUsage.total_tokens.toLocaleString()} /{' '}
            {contextUsage.context_limit.toLocaleString()} tokens (
            {Math.round((contextUsage.total_tokens / contextUsage.context_limit) * 100)}%)
          </span>
        )}
      </div>
      {progressData.length > 0 && (
        <div style={{ padding: '4px 12px' }}>
          <RewardChart data={progressData} completed={!active} evalProgress={lastEvalProgress} />
        </div>
      )}
      {subEvents.map((ev, i) => {
        if (RL_STREAMING_TYPES.has(ev.type)) return null
        const isLast = active && i === lastIndex
        if (ev.type === 'dt_redeploy') {
          const hasDetails = ev.details && ev.details.length > 0
          const isOpen = expanded[i] ?? !ev.done
          return (
            <div key={i} className="ia-sub-entry ia-sub-dt-redeploy">
              <div
                className="ia-sub-entry-header"
                style={{ cursor: hasDetails ? 'pointer' : 'default' }}
                onClick={() => hasDetails && toggle(i, !isOpen)}
              >
                {ev.done ? (
                  <i
                    className="fa fa-check-circle"
                    style={{ color: '#38a169' }}
                    aria-hidden="true"
                  />
                ) : (
                  <div className="spinner-border spinner-border-sm" role="status">
                    <span className="sr-only">Loading...</span>
                  </div>
                )}
                <i className="fa fa-server" style={{ marginLeft: '6px' }} aria-hidden="true" />
                <span>{ev.message}</span>
                {!ev.done && <ElapsedTimer startTime={ev._startTime} />}
                {hasDetails && (
                  <i
                    className={`fa fa-chevron-${isOpen ? 'up' : 'down'}`}
                    style={{ marginLeft: 'auto', opacity: 0.5 }}
                    aria-hidden="true"
                  />
                )}
              </div>
              {isOpen && hasDetails && (
                <div style={{ marginTop: '8px', fontSize: '0.85em', opacity: 0.8 }}>
                  {ev.details.map((line, j) => (
                    <div key={j} style={{ fontFamily: 'monospace', padding: '1px 0' }}>
                      {line}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        }
        if (ev.type === 'reasoning') {
          const isOpen = !!expanded[i]
          return (
            <div key={i} className="ia-sub-entry ia-sub-reasoning">
              <div className="ia-sub-entry-header" onClick={() => toggle(i)}>
                {isLast && (
                  <>
                    <span
                      className={`ia-liveness-dot ${livenessStatus}`}
                      data-tooltip={dotTooltip}
                    />
                    <div className="spinner-border spinner-border-sm" role="status">
                      <span className="sr-only">Loading...</span>
                    </div>
                    <ElapsedTimer startTime={ev._startTime} />
                  </>
                )}
                <i className="fa fa-lightbulb-o" aria-hidden="true" />
                <span>Agent reasoning</span>
                <span className="ia-toggle-hint">{isOpen ? 'collapse' : 'expand'}</span>
              </div>
              {isOpen && (
                <div className="ia-thinking-trace">
                  <ReactMarkdown>{ev.text}</ReactMarkdown>
                </div>
              )}
            </div>
          )
        }
        if (ev.type === 'text') {
          const isOpen = !!expanded[i]
          return (
            <div key={i} className="ia-sub-entry ia-sub-text">
              <div className="ia-sub-entry-header" onClick={() => toggle(i)}>
                {isLast && (
                  <>
                    <span
                      className={`ia-liveness-dot ${livenessStatus}`}
                      data-tooltip={dotTooltip}
                    />
                    <div className="spinner-border spinner-border-sm" role="status">
                      <span className="sr-only">Loading...</span>
                    </div>
                    <ElapsedTimer startTime={ev._startTime} />
                  </>
                )}
                <i className="fa fa-comment-o" aria-hidden="true" />
                <span>Agent output</span>
                <span className="ia-toggle-hint">{isOpen ? 'collapse' : 'expand'}</span>
              </div>
              {isOpen && (
                <div className="ia-thinking-trace">
                  <ReactMarkdown>{ev.text}</ReactMarkdown>
                </div>
              )}
            </div>
          )
        }
        if (ev.type === 'tool_call') {
          const isOpen = expanded[i] ?? isLast
          const isOrchTool = ORCHESTRATOR_TOOLS.has(ev.tool_name)
          const argPairs = isOrchTool ? null : formatToolArgs(ev.tool_name, ev.tool_args)
          return (
            <div key={i} className="ia-sub-entry ia-sub-tool-call">
              <div className="ia-sub-entry-header" onClick={() => toggle(i, !isOpen)}>
                {isLast && (
                  <>
                    <span
                      className={`ia-liveness-dot ${livenessStatus}`}
                      data-tooltip={dotTooltip}
                    />
                    <div className="spinner-border spinner-border-sm" role="status">
                      <span className="sr-only">Loading...</span>
                    </div>
                    <ElapsedTimer startTime={ev._startTime} />
                  </>
                )}
                <i className={`fa ${toolIcon(ev.tool_name)}`} aria-hidden="true" />
                <span>
                  {isOrchTool ? 'Running agent' : 'Running'} {toolLabel(ev.tool_name)}
                </span>
                {ev._prompt && onViewPrompt && (
                  <button
                    type="button"
                    className="btn btn-outline-dark btn-sm"
                    style={{ fontSize: '10px', padding: '1px 8px', marginLeft: '8px' }}
                    onClick={(e) => {
                      e.stopPropagation()
                      onViewPrompt(ev._prompt, ev._promptImages)
                    }}
                  >
                    <i className="fa fa-file-text-o" aria-hidden="true" /> Prompt
                  </button>
                )}
                {ev.subEvents?.length > 0 && onViewContext && (
                  <button
                    type="button"
                    className="btn btn-outline-dark btn-sm"
                    style={{ fontSize: '10px', padding: '1px 8px', marginLeft: '4px' }}
                    onClick={(e) => {
                      e.stopPropagation()
                      onViewContext(ev.subEvents)
                    }}
                  >
                    <i className="fa fa-database" aria-hidden="true" /> Context
                  </button>
                )}
                <span className="ia-toggle-hint">{isOpen ? 'collapse' : 'expand'}</span>
              </div>
              {isOpen && (
                <>
                  <div className="ia-proposal-details">
                    {isOrchTool
                      ? renderOrchestratorArgs(ev.tool_name, ev.tool_args)
                      : argPairs.map(([label, value, isCode], j) => (
                          <div key={j} className="ia-proposal-arg-row">
                            <span className="ia-proposal-arg-label">{label}:</span>
                            {isCode ? (
                              <CopyablePre className="ia-arg-code" text={value}>
                                {value}
                              </CopyablePre>
                            ) : (
                              <span className="ia-proposal-arg-value">{value}</span>
                            )}
                          </div>
                        ))}
                  </div>
                  {ev.subEvents?.length > 0 &&
                    (ev._parallelHosts ||
                    ev.tool_name === 'run_host_analyzers' ||
                    ev.tool_name === 'run_action_verifiers' ? (
                      <ParallelSubAgentLog
                        hosts={ev._parallelHosts}
                        subEvents={ev.subEvents}
                        active={isLast}
                        onViewPrompt={onViewPrompt}
                        onViewContext={onViewContext}
                        livenessStatus={livenessStatus}
                        heartbeatStatus={heartbeatStatus}
                        lastHeartbeatTime={lastHeartbeatTime}
                      />
                    ) : (
                      <SubAgentLog
                        subEvents={ev.subEvents}
                        agentLabel={toolLabel(ev.tool_name)}
                        active={isLast}
                        modelName={ev._modelName}
                        onViewPrompt={onViewPrompt}
                        onViewContext={onViewContext}
                        contextUsage={ev._contextUsage}
                        livenessStatus={livenessStatus}
                        heartbeatStatus={heartbeatStatus}
                        lastHeartbeatTime={lastHeartbeatTime}
                      />
                    ))}
                </>
              )}
            </div>
          )
        }
        if (ev.type === 'tool_result') {
          const isOpen = !!expanded[i]
          const isRlTrain = ev.tool_name === 'rl_train'
          const rlProgressData = isRlTrain
            ? (ev.subEvents || []).filter((e) => e.type === 'progress')
            : []
          const rlMeta = isRlTrain
            ? (() => {
                const call = [...subEvents.slice(0, i)]
                  .reverse()
                  .find((e) => e.type === 'tool_call' && e.tool_name === 'rl_train')
                return {
                  algorithm: call?.tool_args?.algorithm || '',
                  hyperparameters: call?.tool_args?.hyperparameters || '',
                  started: true
                }
              })()
            : {}
          const terminal = renderTerminalResult(ev.tool_name, ev.result)
          const report = renderSubAgentReport(ev.tool_name, ev.result)
          return (
            <div key={i} className="ia-sub-entry ia-sub-tool-result">
              <div className="ia-sub-entry-header" onClick={() => toggle(i)}>
                <i className={`fa ${toolIcon(ev.tool_name)}`} aria-hidden="true" />
                <span>{toolLabel(ev.tool_name)} result</span>
                {ev.result && 'exit_code' in ev.result && (
                  <span
                    className={`badge badge-${ev.result.exit_code === 0 ? 'success' : 'danger'} ml-2`}
                  >
                    exit {ev.result.exit_code}
                  </span>
                )}
                {ev.result?.error && !('exit_code' in (ev.result || {})) && (
                  <span className="badge badge-danger ml-2">error</span>
                )}
                <span className="ia-toggle-hint">{isOpen ? 'collapse' : 'expand'}</span>
              </div>
              {isOpen && (
                <>
                  {isRlTrain && rlProgressData.length > 0 ? (
                    <RlTrainResult
                      trainingData={rlProgressData}
                      trainingMeta={rlMeta}
                      result={{ result: ev.result }}
                      policyData={ev.result?.policy_data}
                    />
                  ) : isRlTrain && ev.result?.error ? (
                    <div className="ia-terminal-result">
                      <div className="ia-terminal-meta">
                        <span className="badge badge-danger">Training Error</span>
                      </div>
                      <CopyablePre
                        className="ia-terminal-output error"
                        text={ev.result.stderr || ev.result.error}
                      >
                        {ev.result.stderr || ev.result.error}
                      </CopyablePre>
                    </div>
                  ) : (
                    <>
                      {ev.result?.image ? (
                        <img
                          src={ev.result.image}
                          alt="Generated attack path"
                          style={{
                            maxWidth: '100%',
                            border: '1px solid #dee2e6',
                            borderRadius: '4px',
                            marginTop: '8px'
                          }}
                        />
                      ) : (
                        terminal ||
                        report ||
                        renderSearchToolResult(ev.tool_name, ev.result) || (
                          <CopyablePre
                            className="ia-result-data mb-0"
                            text={JSON.stringify(ev.result, null, 2)}
                          >
                            {JSON.stringify(ev.result, null, 2)}
                          </CopyablePre>
                        )
                      )}
                    </>
                  )}
                  {ev.subEvents?.length > 0 &&
                    (ev._parallelHosts ||
                    ev.tool_name === 'run_host_analyzers' ||
                    ev.tool_name === 'run_action_verifiers' ? (
                      <ParallelSubAgentLog
                        hosts={ev._parallelHosts}
                        subEvents={ev.subEvents}
                        active={false}
                        onViewPrompt={onViewPrompt}
                        onViewContext={onViewContext}
                      />
                    ) : (
                      <SubAgentLog
                        subEvents={ev.subEvents}
                        agentLabel={toolLabel(ev.tool_name)}
                        active={false}
                        onViewPrompt={onViewPrompt}
                        onViewContext={onViewContext}
                      />
                    ))}
                </>
              )}
            </div>
          )
        }
        if (ev.type === 'context_compaction') {
          return (
            <div key={i} className="ia-sub-entry">
              <div className="mb-1">
                <i className="fa fa-compress" aria-hidden="true" />
                <span className="badge badge-info ml-1" style={{ fontSize: '10px' }}>
                  Context Compacted
                </span>
                <span style={{ fontSize: '10px', color: '#666', marginLeft: '4px' }}>
                  {ev.original_tokens?.toLocaleString()} &rarr;{' '}
                  {ev.compacted_tokens?.toLocaleString()} tokens
                </span>
              </div>
            </div>
          )
        }
        if (ev.type === 'report') {
          if (ev.host_analysis) {
            const a = ev.host_analysis
            const isOpen = !!expanded[i]
            const statusClass = {
              'Confirmed Compromised': 'danger',
              'Likely Compromised': 'warning',
              'Possibly Compromised': 'info',
              'No Evidence of Compromise': 'success'
            }
            return (
              <div key={i} className="card ia-entry border-dark" style={{ marginTop: '8px' }}>
                <div className="card-body">
                  <div className="ia-result-header" onClick={() => toggle(i)}>
                    <span className="badge badge-dark">Host Analysis</span>
                    <span className="ia-tool-name">{a.host_name || 'Host Analysis Report'}</span>
                    {a.compromise_status && (
                      <span
                        className={`badge badge-${statusClass[a.compromise_status] || 'secondary'}`}
                        style={{ marginLeft: '8px' }}
                      >
                        {a.compromise_status}
                      </span>
                    )}
                    <span className="ia-toggle-hint">{isOpen ? 'collapse' : 'expand'}</span>
                  </div>
                  {isOpen && <HostAnalysisBody report={a} />}
                </div>
              </div>
            )
          }
          if (ev.action_verification) {
            const a = ev.action_verification
            const isOpen = !!expanded[i]
            return (
              <div key={i} className="card ia-entry border-dark" style={{ marginTop: '8px' }}>
                <div className="card-body">
                  <div className="ia-result-header" onClick={() => toggle(i)}>
                    <span className="badge badge-dark">Action Verification</span>
                    <span className="ia-tool-name">
                      {a.action_name || 'Action Verification Report'}
                    </span>
                    {a.outcome && (
                      <span
                        className={`badge badge-${ACTION_OUTCOME_STYLES[a.outcome] || 'secondary'}`}
                        style={{ marginLeft: '8px' }}
                      >
                        {a.outcome}
                      </span>
                    )}
                    <span className="ia-toggle-hint">{isOpen ? 'collapse' : 'expand'}</span>
                  </div>
                  {isOpen && <ActionVerificationBody report={a} />}
                </div>
              </div>
            )
          }
          return (
            <div key={i} className="ia-sub-entry ia-sub-report">
              <i className="fa fa-check-circle" style={{ color: '#38a169' }} aria-hidden="true" />
              <span>Report produced</span>
            </div>
          )
        }
        return null
      })}
      {active &&
        (() => {
          const lastEv = subEvents[subEvents.length - 1]
          const lastShowsSpinner =
            lastEv &&
            (lastEv.type === 'reasoning' ||
              lastEv.type === 'text' ||
              lastEv.type === 'tool_call' ||
              lastEv.type === 'tool_result' ||
              lastEv.type === 'dt_redeploy' ||
              lastEv.type === 'sandbox_start' ||
              RL_STREAMING_TYPES.has(lastEv.type))
          if (lastShowsSpinner) return null
          return (
            <div className="ia-sub-entry ia-sub-reasoning">
              <div className="ia-sub-entry-header">
                <span className={`ia-liveness-dot ${livenessStatus}`} data-tooltip={dotTooltip} />
                <div className="spinner-border spinner-border-sm" role="status">
                  <span className="sr-only">Loading...</span>
                </div>
                <ElapsedTimer startTime={lastEv?._startTime} />
                <i className="fa fa-hourglass-half" aria-hidden="true" />
                <span>Preparing next step...</span>
              </div>
            </div>
          )
        })()}
    </div>
  )
}

/**
 * Shared activity log component for all agents.
 * Uses a render prop (renderFinalReport) for the agent-specific final report entry.
 */
function AgentActivityLog({
  conversationHistory,
  expandedEntries,
  toggleEntry,
  pendingProposal,
  executingTool,
  handleApprove,
  handleDeny,
  contextUsage,
  hasNewActivity,
  scrollToBottom,
  logEndRef,
  streamingTraceRef,
  renderFinalReport,
  renderExecutingTool,
  renderToolResult,
  livenessStatus,
  lastHeartbeatTime,
  heartbeatStatus,
  savingHistory
}) {
  const [promptModalText, setPromptModalText] = useState(null)
  const [promptModalImages, setPromptModalImages] = useState([])
  const [contextModalHistory, setContextModalHistory] = useState(null)
  return (
    <div style={{ marginTop: '28px' }}>
      <div className="ia-log-header">
        <p className="ia-log-title">Activity log</p>
        {contextUsage && (
          <span
            className={`ia-context-indicator${contextUsage.total_tokens / contextUsage.context_limit > 0.8 ? ' high-usage' : ''}`}
          >
            Context management: {contextUsage.total_tokens.toLocaleString()} /{' '}
            {contextUsage.context_limit.toLocaleString()} tokens (
            {Math.round((contextUsage.total_tokens / contextUsage.context_limit) * 100)}%)
          </span>
        )}
      </div>
      <div className="ia-log">
        {conversationHistory.map((entry, index) => {
          if (entry.type === 'dt_redeploy') {
            const hasDetails = entry.details && entry.details.length > 0
            const isOpen = expandedEntries[index] ?? !entry.done
            return (
              <div
                key={index}
                className={`card ia-entry ${entry.done ? 'ia-result-entry' : 'ia-streaming-entry'}`}
              >
                <div
                  className="card-body"
                  style={{ padding: '10px 14px', cursor: hasDetails ? 'pointer' : 'default' }}
                  onClick={() => hasDetails && toggleEntry(index, !isOpen)}
                >
                  <div className="ia-thinking-header">
                    {entry.done ? (
                      <i
                        className="fa fa-check-circle"
                        style={{ color: '#38a169' }}
                        aria-hidden="true"
                      />
                    ) : (
                      <div className="spinner-border spinner-border-sm" role="status">
                        <span className="sr-only">Loading...</span>
                      </div>
                    )}
                    <i className="fa fa-server" style={{ marginLeft: '6px' }} aria-hidden="true" />
                    <span className="ia-thinking-title">{entry.message}</span>
                    {!entry.done && <ElapsedTimer startTime={entry._startTime} />}
                    {hasDetails && (
                      <i
                        className={`fa fa-chevron-${isOpen ? 'up' : 'down'}`}
                        style={{ marginLeft: 'auto', opacity: 0.5 }}
                        aria-hidden="true"
                      />
                    )}
                  </div>
                  {isOpen && hasDetails && (
                    <div
                      className="ia-dt-log"
                      style={{ marginTop: '8px', fontSize: '0.85em', opacity: 0.8 }}
                    >
                      {entry.details.map((line, i) => (
                        <div key={i} style={{ fontFamily: 'monospace', padding: '1px 0' }}>
                          {line}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )
          }

          if (entry.type === 'sandbox_start') {
            return (
              <div
                key={index}
                className={`card ia-entry ${entry.done ? 'ia-result-entry' : 'ia-streaming-entry'}`}
              >
                <div className="card-body" style={{ padding: '10px 14px' }}>
                  <div className="ia-thinking-header">
                    {entry.done ? (
                      <i
                        className="fa fa-check-circle"
                        style={{ color: '#38a169' }}
                        aria-hidden="true"
                      />
                    ) : (
                      <div className="spinner-border spinner-border-sm" role="status">
                        <span className="sr-only">Loading...</span>
                      </div>
                    )}
                    <i
                      className="fa fa-terminal"
                      style={{ marginLeft: '6px' }}
                      aria-hidden="true"
                    />
                    <span className="ia-thinking-title">{entry.message}</span>
                    {!entry.done && <ElapsedTimer startTime={entry._startTime} />}
                  </div>
                </div>
              </div>
            )
          }

          if (entry.type === 'streaming') {
            const isStale = livenessStatus === 'stale'
            const isError = livenessStatus === 'error'
            const staleElapsed =
              (isStale || isError) && lastHeartbeatTime
                ? Math.round((Date.now() - lastHeartbeatTime) / 1000)
                : null
            const statusText =
              heartbeatStatus ||
              (livenessStatus === 'alive'
                ? 'Connected'
                : livenessStatus === 'error'
                  ? 'Error'
                  : 'No signal')
            const timeStr = lastHeartbeatTime
              ? new Date(lastHeartbeatTime).toLocaleTimeString()
              : ''
            const dotTooltip = timeStr ? `${statusText} (${timeStr})` : statusText
            const toolLabel = entry.generatingTool
              ? TOOL_LABELS[entry.generatingTool] || entry.generatingTool
              : null
            const headerText = isError
              ? 'Agent error'
              : isStale
                ? 'Agent may be unresponsive...'
                : toolLabel
                  ? `Generating ${toolLabel}...`
                  : 'Agent is thinking...'
            return (
              <div key={index} className="card ia-entry ia-streaming-entry">
                <div className="card-body">
                  <div className="ia-thinking-header">
                    <span
                      className={`ia-liveness-dot ${livenessStatus}`}
                      data-tooltip={dotTooltip}
                    />
                    <div className="spinner-border spinner-border-sm" role="status">
                      <span className="sr-only">Loading...</span>
                    </div>
                    <span className="ia-thinking-title">{headerText}</span>
                    {staleElapsed !== null && (
                      <span className="ia-heartbeat-info">Last signal: {staleElapsed}s ago</span>
                    )}
                    <ElapsedTimer startTime={entry._startTime} />
                  </div>
                  {entry.generatingTool && entry.text && (
                    <details className="ia-collapsed-reasoning">
                      <summary>Agent reasoning</summary>
                      <div className="ia-streaming-trace">
                        <ReactMarkdown>{entry.text}</ReactMarkdown>
                      </div>
                    </details>
                  )}
                  {entry.toolInput ? (
                    <div className="ia-streaming-trace" ref={streamingTraceRef}>
                      <CopyablePre className="ia-tool-input-pre" text={entry.toolInput}>
                        {entry.toolInput}
                      </CopyablePre>
                    </div>
                  ) : (
                    entry.text &&
                    !entry.generatingTool && (
                      <div className="ia-streaming-trace" ref={streamingTraceRef}>
                        <ReactMarkdown>{entry.text}</ReactMarkdown>
                      </div>
                    )
                  )}
                </div>
              </div>
            )
          }

          if (entry.type === 'reasoning') {
            const isExpanded = expandedEntries[index]
            return (
              <div key={index} className="card ia-entry ia-reasoning-entry">
                <div className="card-body">
                  <div className="ia-reasoning-header" onClick={() => toggleEntry(index)}>
                    <i className="fa fa-lightbulb-o" aria-hidden="true" />
                    <span className="ia-reasoning-label">Agent reasoning</span>
                    <span className="ia-toggle-hint">{isExpanded ? 'collapse' : 'expand'}</span>
                  </div>
                  {isExpanded && (
                    <div className="ia-thinking-trace">
                      <ReactMarkdown>{entry.text}</ReactMarkdown>
                    </div>
                  )}
                </div>
              </div>
            )
          }

          if (entry.type === 'tool_proposal') {
            const isCurrentPending = pendingProposal && index === conversationHistory.length - 1
            const isExpanded = isCurrentPending || expandedEntries[index]
            const isOrchTool = ORCHESTRATOR_TOOLS.has(entry.tool_name)
            const argPairs = isOrchTool ? null : formatToolArgs(entry.tool_name, entry.tool_args)
            return (
              <div key={index} className="card ia-entry ia-proposal-entry">
                <div className="card-body">
                  <div
                    className="ia-proposal-header"
                    onClick={!isCurrentPending ? () => toggleEntry(index) : undefined}
                  >
                    <i className={`fa ${toolIcon(entry.tool_name)}`} aria-hidden="true" />
                    <span className="ia-proposal-label">
                      {isCurrentPending
                        ? isOrchTool
                          ? 'The agent wants to invoke agent'
                          : 'The agent wants to call tool'
                        : isOrchTool
                          ? 'Invoked agent'
                          : 'Called tool'}
                    </span>
                    <span className="ia-proposal-tool-inline">{toolLabel(entry.tool_name)}</span>
                    {!isCurrentPending && (
                      <span className="ia-toggle-hint">{isExpanded ? 'collapse' : 'expand'}</span>
                    )}
                  </div>
                  {isExpanded && (
                    <div className="ia-proposal-details">
                      <div className="ia-proposal-tool">
                        {isOrchTool ? 'Agent' : 'Tool'}: {toolLabel(entry.tool_name)}
                      </div>
                      {isOrchTool
                        ? renderOrchestratorArgs(entry.tool_name, entry.tool_args)
                        : argPairs.map(([label, value, isCode], i) => (
                            <div key={i} className="ia-proposal-arg-row">
                              <span className="ia-proposal-arg-label">{label}:</span>
                              {isCode ? (
                                <CopyablePre className="ia-arg-code" text={value}>
                                  {value}
                                </CopyablePre>
                              ) : (
                                <span className="ia-proposal-arg-value">{value}</span>
                              )}
                            </div>
                          ))}
                      {isCurrentPending && (
                        <div className="ia-proposal-actions">
                          <button
                            type="button"
                            className="btn btn-dark btn-sm"
                            onClick={handleApprove}
                            disabled={executingTool}
                          >
                            {executingTool ? 'Executing...' : 'Approve'}
                          </button>
                          <button
                            type="button"
                            className="btn btn-outline-secondary btn-sm"
                            onClick={handleDeny}
                            disabled={executingTool}
                          >
                            Deny
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )
          }

          if (entry.type === 'tool_streaming') {
            const hasSubEvents = entry.subEvents && entry.subEvents.length > 0
            const isOpen = expandedEntries[index] ?? !entry.stopped
            const agentLabel = toolLabel(entry.tool_name)
            const tsStatusText =
              heartbeatStatus ||
              (livenessStatus === 'alive'
                ? 'Connected'
                : livenessStatus === 'error'
                  ? 'Error'
                  : 'No signal')
            const tsTimeStr = lastHeartbeatTime
              ? new Date(lastHeartbeatTime).toLocaleTimeString()
              : ''
            const tsDotTooltip = tsTimeStr ? `${tsStatusText} (${tsTimeStr})` : tsStatusText
            return (
              <div
                key={index}
                className={`card ia-entry ${entry.stopped ? 'ia-result-entry' : 'ia-streaming-entry'}`}
              >
                <div className="card-body">
                  <div
                    className="ia-thinking-header"
                    style={{ cursor: 'pointer' }}
                    onClick={() => toggleEntry(index, !isOpen)}
                  >
                    {entry.stopped ? (
                      <span className="badge badge-secondary">Completed</span>
                    ) : (
                      <>
                        <span
                          className={`ia-liveness-dot ${livenessStatus}`}
                          data-tooltip={tsDotTooltip}
                        />
                        <div className="spinner-border spinner-border-sm" role="status">
                          <span className="sr-only">Loading...</span>
                        </div>
                        <ElapsedTimer startTime={entry._startTime} />
                      </>
                    )}
                    <i className={`fa ${toolIcon(entry.tool_name)}`} aria-hidden="true" />
                    <span className="ia-thinking-title">
                      {entry.stopped
                        ? toolLabel(entry.tool_name)
                        : `Executing ${toolLabel(entry.tool_name)}...`}
                    </span>
                    {entry._modelName && (
                      <span style={{ fontSize: '10px', color: '#888', marginLeft: '6px' }}>
                        <i className="fa fa-microchip" aria-hidden="true" /> {entry._modelName}
                      </span>
                    )}
                    <span className="ia-toggle-hint">{isOpen ? 'collapse' : 'expand'}</span>
                  </div>
                  {isOpen && (
                    <>
                      <div style={{ marginTop: '8px' }}>
                        {entry.prompt && (
                          <button
                            type="button"
                            className="btn btn-outline-dark btn-sm"
                            style={{ fontSize: '11px', padding: '2px 10px' }}
                            onClick={(e) => {
                              e.stopPropagation()
                              setPromptModalText(entry.prompt)
                              setPromptModalImages(entry.promptImages || [])
                            }}
                          >
                            <i className="fa fa-file-text-o" aria-hidden="true" /> Prompt
                          </button>
                        )}
                        {hasSubEvents && (
                          <button
                            type="button"
                            className="btn btn-outline-dark btn-sm"
                            style={{ fontSize: '11px', padding: '2px 10px', marginLeft: '4px' }}
                            onClick={(e) => {
                              e.stopPropagation()
                              setContextModalHistory(entry.subEvents)
                            }}
                          >
                            <i className="fa fa-database" aria-hidden="true" /> Context
                          </button>
                        )}
                      </div>
                      {(hasSubEvents && entry.tool_name === 'run_host_analyzers') ||
                      entry.tool_name === 'run_action_verifiers' ? (
                        <ParallelSubAgentLog
                          hosts={entry._parallelHosts}
                          subEvents={entry.subEvents}
                          active={!entry.stopped}
                          onViewPrompt={(text, images) => {
                            setPromptModalText(text)
                            setPromptModalImages(images || [])
                          }}
                          onViewContext={(history) => setContextModalHistory(history)}
                          livenessStatus={livenessStatus}
                          heartbeatStatus={heartbeatStatus}
                          lastHeartbeatTime={lastHeartbeatTime}
                        />
                      ) : hasSubEvents ? (
                        <SubAgentLog
                          subEvents={entry.subEvents}
                          agentLabel={agentLabel}
                          active={!entry.stopped}
                          modelName={entry._modelName}
                          onViewPrompt={(text, images) => {
                            setPromptModalText(text)
                            setPromptModalImages(images || [])
                          }}
                          onViewContext={(history) => setContextModalHistory(history)}
                          contextUsage={entry.contextUsage}
                          livenessStatus={livenessStatus}
                          heartbeatStatus={heartbeatStatus}
                          lastHeartbeatTime={lastHeartbeatTime}
                        />
                      ) : (
                        <>
                          {entry.output && (
                            <CopyablePre
                              className="ia-terminal-output"
                              style={{ maxHeight: '400px', overflow: 'auto' }}
                              text={entry.output}
                            >
                              {entry.output}
                            </CopyablePre>
                          )}
                          {!entry.stopped && (
                            <div className="ia-sub-entry ia-sub-reasoning">
                              <div className="ia-sub-entry-header">
                                <span
                                  className={`ia-liveness-dot ${livenessStatus}`}
                                  data-tooltip={tsDotTooltip}
                                />
                                <div className="spinner-border spinner-border-sm" role="status">
                                  <span className="sr-only">Loading...</span>
                                </div>
                                <i className="fa fa-hourglass-half" aria-hidden="true" />
                                <span>Waiting for agent response...</span>
                              </div>
                            </div>
                          )}
                        </>
                      )}
                    </>
                  )}
                </div>
              </div>
            )
          }

          if (entry.type === 'tool_approval') {
            const isExpanded = expandedEntries[index]
            const argPairs =
              entry.tool_args && !ORCHESTRATOR_TOOLS.has(entry.tool_name)
                ? formatToolArgs(entry.tool_name, entry.tool_args)
                : null
            return (
              <div key={index} className="card ia-entry ia-approval-entry">
                <div className="card-body">
                  <div
                    className="ia-entry-header"
                    style={{ cursor: argPairs ? 'pointer' : 'default' }}
                    onClick={argPairs ? () => toggleEntry(index) : undefined}
                  >
                    <span className={`badge badge-${entry.approved ? 'success' : 'danger'}`}>
                      {entry.approved ? 'Approved' : 'Denied'}
                    </span>
                    <span className="ia-approval-tool">{toolLabel(entry.tool_name)}</span>
                    {argPairs && (
                      <span className="ia-toggle-hint">{isExpanded ? 'collapse' : 'expand'}</span>
                    )}
                  </div>
                  {isExpanded && argPairs && (
                    <div className="ia-proposal-details">
                      {argPairs.map(([label, value, isCode], i) => (
                        <div key={i} className="ia-proposal-arg-row">
                          <span className="ia-proposal-arg-label">{label}:</span>
                          {isCode ? (
                            <CopyablePre className="ia-arg-code" text={value}>
                              {value}
                            </CopyablePre>
                          ) : (
                            <span className="ia-proposal-arg-value">{value}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )
          }

          if (entry.type === 'tool_result') {
            const isExpanded = expandedEntries[index]
            const hasImage = entry.result?.image
            const hasSubEvents = entry.subEvents && entry.subEvents.length > 0
            const customRender = renderToolResult && renderToolResult(entry)
            const displayResult = hasImage
              ? { status: 'success', message: 'Attack path image generated successfully' }
              : entry.result
            return (
              <div key={index} className="card ia-entry ia-result-entry">
                <div className="card-body">
                  <div className="ia-result-header" onClick={() => toggleEntry(index)}>
                    <i className={`fa ${toolIcon(entry.tool_name)}`} aria-hidden="true" />
                    <span className="ia-result-label">{toolLabel(entry.tool_name)} result</span>
                    {entry._modelName && (
                      <span style={{ fontSize: '10px', color: '#888', marginLeft: '6px' }}>
                        <i className="fa fa-microchip" aria-hidden="true" /> {entry._modelName}
                      </span>
                    )}
                    <span className="ia-toggle-hint">{isExpanded ? 'collapse' : 'expand'}</span>
                  </div>
                  {isExpanded && (
                    <>
                      {(hasSubEvents && entry.tool_name === 'run_host_analyzers') ||
                      entry.tool_name === 'run_action_verifiers' ? (
                        <ParallelSubAgentLog
                          hosts={entry._parallelHosts}
                          subEvents={entry.subEvents}
                          active={false}
                          onViewPrompt={(text, images) => {
                            setPromptModalText(text)
                            setPromptModalImages(images || [])
                          }}
                          onViewContext={(history) => setContextModalHistory(history)}
                        />
                      ) : hasSubEvents ? (
                        <SubAgentLog
                          subEvents={entry.subEvents}
                          agentLabel={toolLabel(entry.tool_name)}
                          active={false}
                          onViewPrompt={(text, images) => {
                            setPromptModalText(text)
                            setPromptModalImages(images || [])
                          }}
                          onViewContext={(history) => setContextModalHistory(history)}
                        />
                      ) : null}
                      {customRender ||
                        renderTerminalResult(entry.tool_name, displayResult) ||
                        renderSubAgentReport(entry.tool_name, displayResult) ||
                        renderSearchToolResult(entry.tool_name, displayResult) || (
                          <>
                            <CopyablePre
                              className="ia-result-data mb-0"
                              text={JSON.stringify(displayResult, null, 2)}
                            >
                              {JSON.stringify(displayResult, null, 2)}
                            </CopyablePre>
                            {hasImage && (
                              <img
                                src={entry.result.image}
                                alt="Generated attack path"
                                style={{
                                  maxWidth: '100%',
                                  border: '1px solid #dee2e6',
                                  borderRadius: '4px',
                                  marginTop: '8px'
                                }}
                              />
                            )}
                          </>
                        )}
                    </>
                  )}
                </div>
              </div>
            )
          }

          if (entry.type === 'error') {
            const d = entry.errorDetail
            const errorType = d?.error_type || ''
            const isLLMTimeout = errorType === 'AgentTimeoutError'
            const isNetworkTimeout =
              !isLLMTimeout &&
              (/timeout|timed.out/i.test(errorType) || /timeout|timed.out/i.test(entry.message))
            const headerLabel = isLLMTimeout
              ? 'LLM call timed out'
              : isNetworkTimeout
                ? 'Connection to server timed out'
                : errorType
                  ? `Error: ${errorType}`
                  : 'Agent step failed'
            return (
              <div key={index} className="card ia-entry border-danger">
                <div className="card-body">
                  <div className="ia-entry-header">
                    <span className="badge badge-danger">Error</span>
                    <span className="ia-tool-name">{headerLabel}</span>
                  </div>
                  <p className="ia-error-message mb-0">{entry.message}</p>
                  {isNetworkTimeout && (
                    <p className="text-muted mb-0" style={{ fontSize: '12px' }}>
                      The server may still be processing. Try refreshing the page to reconnect.
                    </p>
                  )}
                  {d && (
                    <div className="ia-error-detail">
                      {d.agent_name && (
                        <span className="ia-error-detail-item">
                          <strong>Agent:</strong> {d.agent_name}
                        </span>
                      )}
                      {d.step_number > 0 && (
                        <span className="ia-error-detail-item">
                          <strong>Step:</strong> {d.step_number}
                        </span>
                      )}
                      {d.model_name && (
                        <span className="ia-error-detail-item">
                          <strong>Model:</strong> {d.model_name}
                        </span>
                      )}
                      {d.last_status && (
                        <span className="ia-error-detail-item">
                          <strong>Last status:</strong> {d.last_status}
                        </span>
                      )}
                      {d.elapsed_seconds != null && (
                        <span className="ia-error-detail-item">
                          <strong>Elapsed:</strong> {d.elapsed_seconds}s
                        </span>
                      )}
                      {d.error_type && (
                        <span className="ia-error-detail-item">
                          <strong>Type:</strong> {d.error_type}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )
          }

          if (entry.type === 'context_compaction') {
            return (
              <div key={index} className="card ia-entry">
                <div className="card-body">
                  <i className="fa fa-compress" aria-hidden="true" />
                  <span className="badge badge-info ml-2">Context Compacted</span>
                  <span style={{ fontSize: '11px', color: '#666', marginLeft: '8px' }}>
                    {entry.original_tokens?.toLocaleString()} &rarr;{' '}
                    {entry.compacted_tokens?.toLocaleString()} tokens
                  </span>
                  {entry.compaction_model && (
                    <span style={{ fontSize: '10px', color: '#888', marginLeft: '8px' }}>
                      via {entry.compaction_model}
                    </span>
                  )}
                </div>
              </div>
            )
          }

          if (renderFinalReport) {
            return renderFinalReport(entry, index, !!expandedEntries[index])
          }

          return null
        })}
        {executingTool &&
          !conversationHistory.some((e) => e.type === 'tool_streaming') &&
          (renderExecutingTool && renderExecutingTool(executingTool) ? (
            renderExecutingTool(executingTool)
          ) : (
            <div className="card ia-entry ia-streaming-entry">
              <div className="card-body">
                <div className="ia-thinking-header">
                  <div className="spinner-border spinner-border-sm" role="status">
                    <span className="sr-only">Loading...</span>
                  </div>
                  <i className={`fa ${toolIcon(executingTool)}`} aria-hidden="true" />
                  <span className="ia-thinking-title">Executing {toolLabel(executingTool)}...</span>
                  <ElapsedTimer />
                </div>
              </div>
            </div>
          ))}
        {savingHistory && (
          <div className="ia-entry">
            <div className="ia-entry-header" style={{ cursor: 'default' }}>
              <div
                className="spinner-border spinner-border-sm"
                role="status"
                style={{ width: '12px', height: '12px', marginRight: '8px' }}
              >
                <span className="sr-only">Saving...</span>
              </div>
              <span className="ia-thinking-title">Saving to history...</span>
            </div>
          </div>
        )}
        <div ref={logEndRef} />
        {hasNewActivity && (
          <button type="button" className="ia-new-activity-btn" onClick={scrollToBottom}>
            <i className="fa fa-arrow-down" aria-hidden="true" /> New activity
          </button>
        )}
      </div>
      <PromptModal
        show={!!promptModalText}
        promptText={promptModalText || ''}
        promptImages={promptModalImages}
        onClose={() => {
          setPromptModalText(null)
          setPromptModalImages([])
        }}
      />
      <ContextModal
        show={!!contextModalHistory}
        conversationHistory={contextModalHistory || []}
        onClose={() => setContextModalHistory(null)}
      />
    </div>
  )
}

export default AgentActivityLog
