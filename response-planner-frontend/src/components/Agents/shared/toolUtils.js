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
  python_exec: { label: 'Python Sandbox', icon: 'fa-code' },
  rl_train: { label: 'RL Training', icon: 'fa-line-chart' },
  gym_verify: { label: 'Gymnasium Verify', icon: 'fa-check-circle' },
  query_policy: { label: 'Query RL Policy', icon: 'fa-brain' },
  run_code_agent: { label: 'Code Agent', icon: 'fa-cogs' },
  run_code_verifier_agent: { label: 'Code Verifier Agent', icon: 'fa-search' },
  produce_orchestrator_report: { label: 'Code Manager Report', icon: 'fa-file-text' },
  run_code_manager: { label: 'Code Manager', icon: 'fa-sitemap' },
  run_planner_agent: { label: 'Planner Agent', icon: 'fa-line-chart' },
  run_plan_verifier_agent: { label: 'Plan Verifier Agent', icon: 'fa-check-circle' },
  produce_plan_manager_report: { label: 'Plan Manager Report', icon: 'fa-flag-checkered' },
  generate_attack_image: { label: 'Attack Path Image', icon: 'fa-image' },
  run_host_analyzers: { label: 'Parallel Host Analysis', icon: 'fa-server' },
  run_attack_path_verifier_agent: { label: 'Attack Path Verifier Agent', icon: 'fa-crosshairs' },
  context_compaction: { label: 'Context Compaction', icon: 'fa-compress' }
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
      return [['Code', args.code || '', true]]
    case 'python_exec':
      return [['Code', args.code || '', true]]
    case 'rl_train':
      return [
        ['Code', args.code || '', true],
        ['Time limit', `${args.time_limit_minutes || 10} min`]
      ]
    case 'gym_verify':
      return [['Code', args.code || '', true]]
    case 'query_policy':
      return [['State vector', JSON.stringify(args.state || [])]]
    case 'generate_attack_image':
      return [['Prompt', args.prompt || '', true]]
    case 'run_host_analyzers':
      return [
        [
          'Hosts',
          (args.hosts || []).map((h) => `${h.host_id}: ${h.host_description}`).join('\n'),
          true
        ]
      ]
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
