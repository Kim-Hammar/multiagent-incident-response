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
  DIGITAL_TWIN_RESOURCE,
  API_DIGITAL_TWIN_URL,
  API_DIGITAL_TWIN_RESET_URL,
  API_DIGITAL_TWIN_DEPLOY_URL,
  API_DIGITAL_TWIN_STOP_URL,
  API_DIGITAL_TWIN_STATUS_URL,
  API_DIGITAL_TWIN_VALIDATE_URL
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
})
