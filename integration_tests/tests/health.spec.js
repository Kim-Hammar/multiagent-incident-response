import { test, expect } from '@playwright/test'

async function getAuthToken(request) {
  const loginRes = await request.post('/api/login', {
    data: { username: 'admin', password: process.env.ADMIN_PASSWORD || 'admin' }
  })
  expect(loginRes.status()).toBe(200)
  const body = await loginRes.json()
  return body.token
}

/**
 * Send an authenticated request, retrying once with a fresh token if
 * a concurrent login from another worker invalidated the first token.
 */
async function authedRequest(request, method, url, options = {}) {
  const token = await getAuthToken(request)
  const res = await request[method](url, {
    ...options,
    headers: { ...options.headers, Authorization: `Bearer ${token}` }
  })
  if (res.status() === 401) {
    const retryToken = await getAuthToken(request)
    return request[method](url, {
      ...options,
      headers: { ...options.headers, Authorization: `Bearer ${retryToken}` }
    })
  }
  return res
}

test.describe('API health checks', () => {
  test('GET /api/health returns ok', async ({ request }) => {
    const response = await request.get('/api/health')
    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(body.status).toBe('ok')
    expect(body.app).toBe('Incident Response Planner')
  })

  test('GET /api/example returns 11 fields', async ({ request }) => {
    const response = await authedRequest(request, 'get', '/api/example')
    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(Object.keys(body)).toHaveLength(11)
    expect(body).toHaveProperty('system_description')
    expect(body).toHaveProperty('security_alerts')
    expect(body).toHaveProperty('operator_feedback')
    expect(body).toHaveProperty('specification')
    expect(body).toHaveProperty('specification_commands')
    expect(body).toHaveProperty('incident_report')
    expect(body).toHaveProperty('response_plan')
    expect(body).toHaveProperty('system_description_images')
    expect(body).toHaveProperty('host_to_analyze')
    expect(body).toHaveProperty('attack_path')
    expect(body).toHaveProperty('action_to_validate')
  })

  test('POST /api/plan with valid input returns plan', async ({ request }) => {
    const response = await authedRequest(request, 'post', '/api/plan', {
      data: { incident_description: 'Server compromised' }
    })
    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(body.incident_description).toBe('Server compromised')
    expect(body.severity).toBeTruthy()
    expect(body.steps.length).toBeGreaterThan(0)
  })

  test('POST /api/plan without description returns 400', async ({ request }) => {
    const response = await authedRequest(request, 'post', '/api/plan', {
      data: { wrong_key: 'value' }
    })
    expect(response.status()).toBe(400)
    const body = await response.json()
    expect(body.error).toBe('incident_description is required')
  })
})
