import { test, expect } from '@playwright/test'

let authToken

test.beforeAll(async ({ request }) => {
  const loginRes = await request.post('/api/login', {
    data: { username: 'admin', password: process.env.ADMIN_PASSWORD || 'admin' }
  })
  expect(loginRes.status()).toBe(200)
  const body = await loginRes.json()
  authToken = body.token
})

test.describe('API health checks', () => {
  test('GET /api/health returns ok', async ({ request }) => {
    const response = await request.get('/api/health')
    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(body.status).toBe('ok')
    expect(body.app).toBe('CCS Incident Response Planner')
  })

  test('GET /api/example returns 3 fields', async ({ request }) => {
    const response = await request.get('/api/example', {
      headers: { Authorization: `Bearer ${authToken}` }
    })
    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(Object.keys(body)).toHaveLength(3)
    expect(body).toHaveProperty('system_description')
    expect(body).toHaveProperty('security_alerts')
    expect(body).toHaveProperty('operator_feedback')
  })

  test('POST /api/plan with valid input returns plan', async ({ request }) => {
    const response = await request.post('/api/plan', {
      headers: { Authorization: `Bearer ${authToken}` },
      data: { incident_description: 'Server compromised' }
    })
    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(body.incident_description).toBe('Server compromised')
    expect(body.severity).toBeTruthy()
    expect(body.steps.length).toBeGreaterThan(0)
  })

  test('POST /api/plan without description returns 400', async ({ request }) => {
    const response = await request.post('/api/plan', {
      headers: { Authorization: `Bearer ${authToken}` },
      data: { wrong_key: 'value' }
    })
    expect(response.status()).toBe(400)
    const body = await response.json()
    expect(body.error).toBe('incident_description is required')
  })
})
