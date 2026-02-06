import { describe, it, expect } from 'vitest'
import {
  LOGIN_RESOURCE,
  ABOUT_RESOURCE,
  RESPONSE_PLANNER_RESOURCE,
  NOT_FOUND_RESOURCE,
  APP_TITLE,
  API_BASE_URL,
  API_HEALTH_URL,
  API_PLAN_URL
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

  it('APP_TITLE is the application name', () => {
    expect(APP_TITLE).toBe('CCS Incident Response Planner')
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
})
