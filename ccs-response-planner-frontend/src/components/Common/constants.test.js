import { describe, it, expect } from 'vitest'
import {
  HOME_RESOURCE,
  NOT_FOUND_RESOURCE,
  APP_TITLE,
  API_BASE_URL,
  API_HEALTH_URL,
  API_PLAN_URL
} from './constants'

describe('constants', () => {
  it('HOME_RESOURCE is a non-empty string', () => {
    expect(typeof HOME_RESOURCE).toBe('string')
    expect(HOME_RESOURCE).toBe('home-page')
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
