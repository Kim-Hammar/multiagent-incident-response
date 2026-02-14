export const TOOL_LABELS = {
  tavily_search: { label: 'Web Search', icon: 'fa-search' },
  nvd_search: { label: 'Vulnerability Database (NVD)', icon: 'fa-shield' },
  mitre_search: { label: 'MITRE ATT&CK Lookup', icon: 'fa-crosshairs' },
  virustotal_scan: { label: 'VirusTotal Scan', icon: 'fa-bug' },
  abuseipdb_check: { label: 'AbuseIPDB Check', icon: 'fa-exclamation-triangle' },
  otx_search: { label: 'Threat Intelligence (OTX)', icon: 'fa-globe' },
  dt_exec: { label: 'Digital Twin Terminal', icon: 'fa-terminal' },
  dt_python_exec: {
    label: 'Python script to execute in the digital twin sandbox',
    icon: 'fa-code'
  },
  pentest_exec: { label: 'Attacker Terminal', icon: 'fa-terminal' },
  python_exec: { label: 'Python Sandbox', icon: 'fa-code' },
  rl_train: { label: 'RL Training', icon: 'fa-line-chart' },
  dp_solve: { label: 'DP Value Iteration', icon: 'fa-line-chart' },
  gym_verify: { label: 'Gymnasium Verify', icon: 'fa-check-circle' },
  query_policy: { label: 'Query RL Policy', icon: 'fa-brain' },
  run_code_agent: { label: 'Code Agent', icon: 'fa-cogs' },
  run_code_reviewer_agent: { label: 'Code Reviewer Agent', icon: 'fa-search' },
  produce_orchestrator_report: { label: 'Code Manager Report', icon: 'fa-file-text' }
}

export function formatToolArgs(toolName, args) {
  if (!args) return []
  switch (toolName) {
    case 'tavily_search':
      return [['Query', args.query || '']]
    case 'nvd_search':
      if (args.cve_id) return [['CVE ID', args.cve_id]]
      return [['Keyword', args.keyword || '']]
    case 'mitre_search':
      if (args.technique_id) return [['Technique ID', args.technique_id]]
      return [['Search', args.search || '']]
    case 'virustotal_scan':
      return [
        ['Type', args.scan_type || ''],
        ['Value', args.value || '']
      ]
    case 'abuseipdb_check':
      return [['IP address', args.ip || '']]
    case 'otx_search':
      return [
        ['Indicator type', args.indicator_type || ''],
        ['Value', args.value || '']
      ]
    case 'dt_exec':
      return [
        ['Container', args.container || ''],
        ['Command', args.command || '']
      ]
    case 'dt_python_exec':
      return [['Code', args.code || '']]
    case 'pentest_exec':
      return [['Command', args.command || '']]
    case 'python_exec':
      return [['Code', args.code || '']]
    case 'rl_train':
      return [
        ['Code', args.code || ''],
        ['Time limit', `${args.time_limit_minutes || 5} min`]
      ]
    case 'dp_solve':
      return [
        ['Code', args.code || ''],
        ['Time limit', `${args.time_limit_minutes || 5} min`]
      ]
    case 'gym_verify':
      return [['Code', args.code || '']]
    case 'query_policy':
      return [['State vector', JSON.stringify(args.state || [])]]
    default:
      return [['Arguments', JSON.stringify(args)]]
  }
}

export function toolLabel(name) {
  return (TOOL_LABELS[name] || { label: name, icon: 'fa-cog' }).label
}

export function toolIcon(name) {
  return (TOOL_LABELS[name] || { label: name, icon: 'fa-cog' }).icon
}
