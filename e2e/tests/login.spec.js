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
})
