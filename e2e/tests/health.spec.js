import { test, expect } from '@playwright/test'

test.describe('API health checks', () => {
  test('GET /api/health returns ok', async ({ request }) => {
    const response = await request.get('/api/health')
    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(body.status).toBe('ok')
    expect(body.app).toBe('CCS Incident Response Planner')
  })

  test('GET /api/example returns 3 fields', async ({ request }) => {
    const response = await request.get('/api/example')
    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(Object.keys(body)).toHaveLength(3)
    expect(body).toHaveProperty('system_description')
    expect(body).toHaveProperty('security_alerts')
    expect(body).toHaveProperty('operator_feedback')
  })

  test('POST /api/plan with valid input returns plan', async ({ request }) => {
    const response = await request.post('/api/plan', {
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
      data: { wrong_key: 'value' }
    })
    expect(response.status()).toBe(400)
    const body = await response.json()
    expect(body.error).toBe('incident_description is required')
  })
})
