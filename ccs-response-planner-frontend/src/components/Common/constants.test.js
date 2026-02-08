import { describe, it, expect } from 'vitest'
import {
  LOGIN_RESOURCE,
  ABOUT_RESOURCE,
  RESPONSE_PLANNER_RESOURCE,
  LLM_RESOURCE,
  NOT_FOUND_RESOURCE,
  API_BASE_URL,
  API_HEALTH_URL,
  API_PLAN_URL,
  API_EXAMPLE_URL,
  API_LOGIN_URL,
  API_LLM_URL,
  TOOLS_RESOURCE,
  API_TAVILY_URL,
  API_TAVILY_SEARCH_URL,
  API_NVD_URL,
  API_NVD_SEARCH_URL,
  API_MITRE_URL,
  API_MITRE_SEARCH_URL,
  API_VIRUSTOTAL_URL,
  API_VIRUSTOTAL_SCAN_URL,
  API_ABUSEIPDB_URL,
  API_ABUSEIPDB_CHECK_URL,
  API_OTX_URL,
  API_OTX_SEARCH_URL,
  DIGITAL_TWIN_RESOURCE,
  API_DIGITAL_TWIN_URL,
  API_DIGITAL_TWIN_RESET_URL,
  API_DIGITAL_TWIN_DEPLOY_URL,
  API_DIGITAL_TWIN_STOP_URL,
  API_DIGITAL_TWIN_STATUS_URL,
  API_DIGITAL_TWIN_VALIDATE_URL,
  API_DT_EXEC_URL,
  API_DT_EXEC_RUN_URL,
  API_DT_LOGS_URL,
  API_DT_LOGS_FETCH_URL,
  PYTHON_RESOURCE,
  API_DT_PYTHON_URL,
  API_DT_PYTHON_RUN_URL,
  API_DT_PYTHON_START_URL,
  API_DT_PYTHON_STOP_URL,
  AGENTS_RESOURCE,
  API_AGENTS_INFO_STEP_URL,
  API_AGENTS_INFO_TOOL_URL,
  API_AGENTS_INFO_PROMPT_URL
} from './constants'

describe('constants', () => {
  it('LOGIN_RESOURCE is the login route', () => {
    expect(LOGIN_RESOURCE).toBe('login')
  })

  it('ABOUT_RESOURCE is the about route', () => {
    expect(ABOUT_RESOURCE).toBe('about')
  })

  it('RESPONSE_PLANNER_RESOURCE is the response planner route', () => {
    expect(RESPONSE_PLANNER_RESOURCE).toBe('response-planner')
  })

  it('NOT_FOUND_RESOURCE is the wildcard route', () => {
    expect(NOT_FOUND_RESOURCE).toBe('*')
  })

  it('API_BASE_URL starts with /api', () => {
    expect(API_BASE_URL).toBe('/api')
  })

  it('API_HEALTH_URL starts with API_BASE_URL', () => {
    expect(API_HEALTH_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_HEALTH_URL).toBe('/api/health')
  })

  it('API_PLAN_URL starts with API_BASE_URL', () => {
    expect(API_PLAN_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_PLAN_URL).toBe('/api/plan')
  })

  it('API_EXAMPLE_URL starts with API_BASE_URL', () => {
    expect(API_EXAMPLE_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_EXAMPLE_URL).toBe('/api/example')
  })

  it('API_LOGIN_URL starts with API_BASE_URL', () => {
    expect(API_LOGIN_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_LOGIN_URL).toBe('/api/login')
  })

  it('LLM_RESOURCE is the llm route', () => {
    expect(LLM_RESOURCE).toBe('llm')
  })

  it('API_LLM_URL starts with API_BASE_URL', () => {
    expect(API_LLM_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_LLM_URL).toBe('/api/llm')
  })

  it('TOOLS_RESOURCE is the tools route', () => {
    expect(TOOLS_RESOURCE).toBe('tools')
  })

  it('API_TAVILY_URL starts with API_BASE_URL', () => {
    expect(API_TAVILY_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_TAVILY_URL).toBe('/api/tavily')
  })

  it('API_TAVILY_SEARCH_URL starts with API_BASE_URL', () => {
    expect(API_TAVILY_SEARCH_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_TAVILY_SEARCH_URL).toBe('/api/tavily/search')
  })

  it('API_NVD_URL starts with API_BASE_URL', () => {
    expect(API_NVD_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_NVD_URL).toBe('/api/nvd')
  })

  it('API_NVD_SEARCH_URL starts with API_BASE_URL', () => {
    expect(API_NVD_SEARCH_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_NVD_SEARCH_URL).toBe('/api/nvd/search')
  })

  it('API_MITRE_URL starts with API_BASE_URL', () => {
    expect(API_MITRE_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_MITRE_URL).toBe('/api/mitre')
  })

  it('API_MITRE_SEARCH_URL starts with API_BASE_URL', () => {
    expect(API_MITRE_SEARCH_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_MITRE_SEARCH_URL).toBe('/api/mitre/search')
  })

  it('API_VIRUSTOTAL_URL starts with API_BASE_URL', () => {
    expect(API_VIRUSTOTAL_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_VIRUSTOTAL_URL).toBe('/api/virustotal')
  })

  it('API_VIRUSTOTAL_SCAN_URL starts with API_BASE_URL', () => {
    expect(API_VIRUSTOTAL_SCAN_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_VIRUSTOTAL_SCAN_URL).toBe('/api/virustotal/scan')
  })

  it('API_ABUSEIPDB_URL starts with API_BASE_URL', () => {
    expect(API_ABUSEIPDB_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_ABUSEIPDB_URL).toBe('/api/abuseipdb')
  })

  it('API_ABUSEIPDB_CHECK_URL starts with API_BASE_URL', () => {
    expect(API_ABUSEIPDB_CHECK_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_ABUSEIPDB_CHECK_URL).toBe('/api/abuseipdb/check')
  })

  it('API_OTX_URL starts with API_BASE_URL', () => {
    expect(API_OTX_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_OTX_URL).toBe('/api/otx')
  })

  it('API_OTX_SEARCH_URL starts with API_BASE_URL', () => {
    expect(API_OTX_SEARCH_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_OTX_SEARCH_URL).toBe('/api/otx/search')
  })

  it('DIGITAL_TWIN_RESOURCE is the digital-twin route', () => {
    expect(DIGITAL_TWIN_RESOURCE).toBe('digital-twin')
  })

  it('API_DIGITAL_TWIN_URL starts with API_BASE_URL', () => {
    expect(API_DIGITAL_TWIN_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_DIGITAL_TWIN_URL).toBe('/api/digital-twin')
  })

  it('API_DIGITAL_TWIN_RESET_URL starts with API_BASE_URL', () => {
    expect(API_DIGITAL_TWIN_RESET_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_DIGITAL_TWIN_RESET_URL).toBe('/api/digital-twin/reset')
  })

  it('API_DIGITAL_TWIN_DEPLOY_URL starts with API_BASE_URL', () => {
    expect(API_DIGITAL_TWIN_DEPLOY_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_DIGITAL_TWIN_DEPLOY_URL).toBe('/api/digital-twin/deploy')
  })

  it('API_DIGITAL_TWIN_STOP_URL starts with API_BASE_URL', () => {
    expect(API_DIGITAL_TWIN_STOP_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_DIGITAL_TWIN_STOP_URL).toBe('/api/digital-twin/stop')
  })

  it('API_DIGITAL_TWIN_STATUS_URL starts with API_BASE_URL', () => {
    expect(API_DIGITAL_TWIN_STATUS_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_DIGITAL_TWIN_STATUS_URL).toBe('/api/digital-twin/status')
  })

  it('API_DIGITAL_TWIN_VALIDATE_URL starts with API_BASE_URL', () => {
    expect(API_DIGITAL_TWIN_VALIDATE_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_DIGITAL_TWIN_VALIDATE_URL).toBe('/api/digital-twin/validate')
  })

  it('API_DT_EXEC_URL starts with API_BASE_URL', () => {
    expect(API_DT_EXEC_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_DT_EXEC_URL).toBe('/api/dt-exec')
  })

  it('API_DT_EXEC_RUN_URL starts with API_BASE_URL', () => {
    expect(API_DT_EXEC_RUN_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_DT_EXEC_RUN_URL).toBe('/api/dt-exec/run')
  })

  it('API_DT_LOGS_URL starts with API_BASE_URL', () => {
    expect(API_DT_LOGS_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_DT_LOGS_URL).toBe('/api/dt-logs')
  })

  it('API_DT_LOGS_FETCH_URL starts with API_BASE_URL', () => {
    expect(API_DT_LOGS_FETCH_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_DT_LOGS_FETCH_URL).toBe('/api/dt-logs/fetch')
  })

  it('API_DT_PYTHON_URL starts with API_BASE_URL', () => {
    expect(API_DT_PYTHON_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_DT_PYTHON_URL).toBe('/api/dt-python')
  })

  it('API_DT_PYTHON_RUN_URL starts with API_BASE_URL', () => {
    expect(API_DT_PYTHON_RUN_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_DT_PYTHON_RUN_URL).toBe('/api/dt-python/run')
  })

  it('PYTHON_RESOURCE is the python route', () => {
    expect(PYTHON_RESOURCE).toBe('python')
  })

  it('API_DT_PYTHON_START_URL starts with API_BASE_URL', () => {
    expect(API_DT_PYTHON_START_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_DT_PYTHON_START_URL).toBe('/api/dt-python/start')
  })

  it('API_DT_PYTHON_STOP_URL starts with API_BASE_URL', () => {
    expect(API_DT_PYTHON_STOP_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_DT_PYTHON_STOP_URL).toBe('/api/dt-python/stop')
  })

  it('AGENTS_RESOURCE is the agents route', () => {
    expect(AGENTS_RESOURCE).toBe('agents')
  })

  it('API_AGENTS_INFO_STEP_URL starts with API_BASE_URL', () => {
    expect(API_AGENTS_INFO_STEP_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_AGENTS_INFO_STEP_URL).toBe('/api/agents/information/step')
  })

  it('API_AGENTS_INFO_TOOL_URL starts with API_BASE_URL', () => {
    expect(API_AGENTS_INFO_TOOL_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_AGENTS_INFO_TOOL_URL).toBe('/api/agents/information/tool')
  })

  it('API_AGENTS_INFO_PROMPT_URL starts with API_BASE_URL', () => {
    expect(API_AGENTS_INFO_PROMPT_URL.startsWith(API_BASE_URL)).toBe(true)
    expect(API_AGENTS_INFO_PROMPT_URL).toBe('/api/agents/information/prompt')
  })
})
