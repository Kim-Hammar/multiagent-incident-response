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
  API_LLM_URL
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
})
