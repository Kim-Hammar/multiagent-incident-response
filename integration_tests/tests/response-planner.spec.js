import { test, expect } from '@playwright/test'

/**
 * Helper: log in via the UI so localStorage gets the token
 * and the response-planner route becomes accessible.
 */
async function loginViaUI(page) {
  await page.goto('/login')
  await page.locator('#username').fill('admin')
  await page.locator('#password').fill(process.env.ADMIN_PASSWORD || 'admin')
  await page.locator('button', { hasText: 'Sign in' }).click()
  await expect(page).toHaveURL(/\/response-planner/, { timeout: 5000 })
}

test.describe('Response Planner page', () => {
  test.beforeEach(async ({ page }) => {
    await loginViaUI(page)
  })

  test('three textareas are visible', async ({ page }) => {
    await expect(page.locator('#rp-system-desc')).toBeVisible()
    await expect(page.locator('#rp-security-alerts')).toBeVisible()
    await expect(page.locator('#rp-operator-feedback')).toBeVisible()
  })

  test('textareas are initially empty', async ({ page }) => {
    await expect(page.locator('#rp-system-desc')).toHaveValue('')
    await expect(page.locator('#rp-security-alerts')).toHaveValue('')
    await expect(page.locator('#rp-operator-feedback')).toHaveValue('')
  })

  test('user can type into textareas', async ({ page }) => {
    await page.locator('#rp-system-desc').fill('Test system')
    await page.locator('#rp-security-alerts').fill('Test alert')
    await page.locator('#rp-operator-feedback').fill('Test feedback')
    await expect(page.locator('#rp-system-desc')).toHaveValue('Test system')
    await expect(page.locator('#rp-security-alerts')).toHaveValue('Test alert')
    await expect(page.locator('#rp-operator-feedback')).toHaveValue('Test feedback')
  })

  test('Run agent button is visible', async ({ page }) => {
    await expect(page.locator('button', { hasText: 'Run agent' })).toBeVisible()
  })

  test('Load example button is visible', async ({ page }) => {
    await expect(page.locator('button', { hasText: 'Load example' })).toBeVisible()
  })

  test('Load example populates all three fields', async ({ page }) => {
    const select = page.locator('select').filter({ hasText: 'Select an incident' })
    await select.waitFor({ state: 'visible', timeout: 5000 })
    // Wait for the dropdown to have options loaded from API
    await expect(select.locator('option')).not.toHaveCount(1, { timeout: 5000 })
    await select.selectOption({ label: 'Incident 1' })
    await page.locator('button', { hasText: 'Load example' }).click()
    await expect(page.locator('#rp-system-desc')).not.toHaveValue('', { timeout: 5000 })
    await expect(page.locator('#rp-security-alerts')).not.toHaveValue('')
    await expect(page.locator('#rp-operator-feedback')).not.toHaveValue('')
  })

  test('Fetch example populates fields from API', async ({ page }) => {
    const select = page.locator('select').filter({ hasText: 'Select an incident' })
    await select.waitFor({ state: 'visible', timeout: 5000 })
    await expect(select.locator('option')).not.toHaveCount(1, { timeout: 5000 })
    await select.selectOption({ label: 'Incident 1' })
    await page.locator('button', { hasText: 'Load example' }).click()
    await expect(page.locator('#rp-system-desc')).not.toHaveValue('', { timeout: 5000 })
    const sysDesc = await page.locator('#rp-system-desc').inputValue()
    expect(sysDesc).toContain('SaaS company')
  })
})
