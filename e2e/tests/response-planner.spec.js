import { test, expect } from '@playwright/test'

test.describe('Response Planner page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveURL(/\/response-planner/)
  })

  test('three textareas are visible', async ({ page }) => {
    await expect(page.locator('#systemDescription')).toBeVisible()
    await expect(page.locator('#securityAlerts')).toBeVisible()
    await expect(page.locator('#operatorFeedback')).toBeVisible()
  })

  test('textareas are initially empty', async ({ page }) => {
    await expect(page.locator('#systemDescription')).toHaveValue('')
    await expect(page.locator('#securityAlerts')).toHaveValue('')
    await expect(page.locator('#operatorFeedback')).toHaveValue('')
  })

  test('user can type into textareas', async ({ page }) => {
    await page.locator('#systemDescription').fill('Test system')
    await page.locator('#securityAlerts').fill('Test alert')
    await page.locator('#operatorFeedback').fill('Test feedback')
    await expect(page.locator('#systemDescription')).toHaveValue('Test system')
    await expect(page.locator('#securityAlerts')).toHaveValue('Test alert')
    await expect(page.locator('#operatorFeedback')).toHaveValue('Test feedback')
  })

  test('Generate plan button is visible', async ({ page }) => {
    await expect(page.locator('button', { hasText: 'Generate plan' })).toBeVisible()
  })

  test('Fetch example incident button is visible', async ({ page }) => {
    await expect(page.locator('button', { hasText: 'Fetch example' })).toBeVisible()
  })

  test('Fetch example populates all three fields', async ({ page }) => {
    await page.locator('button', { hasText: 'Fetch example' }).click()
    await expect(page.locator('#systemDescription')).not.toHaveValue('')
    await expect(page.locator('#securityAlerts')).not.toHaveValue('')
    await expect(page.locator('#operatorFeedback')).not.toHaveValue('')
  })

  test('Fetch example populates fields from API', async ({ page }) => {
    await page.locator('button', { hasText: 'Fetch example' }).click()
    await expect(page.locator('#systemDescription')).not.toHaveValue('', { timeout: 5000 })
    const sysDesc = await page.locator('#systemDescription').inputValue()
    expect(sysDesc).toContain('web server')
  })
})
