import { test, expect } from '@playwright/test'

test.describe('Login page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.locator('nav a', { hasText: 'Login' }).click()
    await expect(page).toHaveURL(/\/login/)
  })

  test('username and password fields are visible', async ({ page }) => {
    await expect(page.locator('#username')).toBeVisible()
    await expect(page.locator('#password')).toBeVisible()
  })

  test('Sign in button is visible', async ({ page }) => {
    await expect(page.locator('button', { hasText: 'Sign in' })).toBeVisible()
  })

  test('password field has type password', async ({ page }) => {
    await expect(page.locator('#password')).toHaveAttribute('type', 'password')
  })

  test('successful login redirects to response planner', async ({ page }) => {
    await page.locator('#username').fill('admin')
    await page.locator('#password').fill(process.env.ADMIN_PASSWORD || 'admin')
    await page.locator('button', { hasText: 'Sign in' }).click()
    await expect(page).toHaveURL(/\/response-planner/, { timeout: 5000 })
    await expect(page.locator('h2')).toHaveText('Response planner')
  })
})
