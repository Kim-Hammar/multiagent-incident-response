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

  test('four textareas are visible', async ({ page }) => {
    await expect(page.locator('#systemDescription')).toBeVisible()
    await expect(page.locator('#securityAlerts')).toBeVisible()
    await expect(page.locator('#operatorFeedback')).toBeVisible()
    await expect(page.locator('#specification')).toBeVisible()
  })

  test('textareas are initially empty', async ({ page }) => {
    await expect(page.locator('#systemDescription')).toHaveValue('')
    await expect(page.locator('#securityAlerts')).toHaveValue('')
    await expect(page.locator('#operatorFeedback')).toHaveValue('')
    await expect(page.locator('#specification')).toHaveValue('')
  })

  test('user can type into textareas', async ({ page }) => {
    await page.locator('#systemDescription').fill('Test system')
    await page.locator('#securityAlerts').fill('Test alert')
    await page.locator('#operatorFeedback').fill('Test feedback')
    await page.locator('#specification').fill('Test spec')
    await expect(page.locator('#systemDescription')).toHaveValue('Test system')
    await expect(page.locator('#securityAlerts')).toHaveValue('Test alert')
    await expect(page.locator('#operatorFeedback')).toHaveValue('Test feedback')
    await expect(page.locator('#specification')).toHaveValue('Test spec')
  })

  test('Generate plan button is visible', async ({ page }) => {
    await expect(page.locator('button', { hasText: 'Generate plan' })).toBeVisible()
  })

  test('Load example button is visible', async ({ page }) => {
    await expect(page.locator('button', { hasText: 'Load example' })).toBeVisible()
  })

  test('Load example populates all four fields', async ({ page }) => {
    const select = page.locator('select').filter({ hasText: 'Select an incident' })
    await select.waitFor({ state: 'visible', timeout: 5000 })
    // Wait for the dropdown to have options loaded from API
    await expect(select.locator('option')).not.toHaveCount(1, { timeout: 5000 })
    await select.selectOption({ label: 'Incident 1' })
    await page.locator('button', { hasText: 'Load example' }).click()
    await expect(page.locator('#systemDescription')).not.toHaveValue('', { timeout: 5000 })
    await expect(page.locator('#securityAlerts')).not.toHaveValue('')
    await expect(page.locator('#operatorFeedback')).not.toHaveValue('')
    await expect(page.locator('#specification')).not.toHaveValue('')
  })

  test('Fetch example populates fields from API', async ({ page }) => {
    const select = page.locator('select').filter({ hasText: 'Select an incident' })
    await select.waitFor({ state: 'visible', timeout: 5000 })
    await expect(select.locator('option')).not.toHaveCount(1, { timeout: 5000 })
    await select.selectOption({ label: 'Incident 1' })
    await page.locator('button', { hasText: 'Load example' }).click()
    await expect(page.locator('#systemDescription')).not.toHaveValue('', { timeout: 5000 })
    const sysDesc = await page.locator('#systemDescription').inputValue()
    expect(sysDesc).toContain('SaaS company')
  })
})
