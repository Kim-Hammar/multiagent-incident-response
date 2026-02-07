import { test, expect } from '@playwright/test'

test.describe('Navigation', () => {
  test('root redirects to /login when not authenticated', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveURL(/\/login/)
  })

  test('navbar links are visible', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('nav a', { hasText: 'Response planner' })).toBeVisible()
    await expect(page.locator('nav a', { hasText: 'About' })).toBeVisible()
    await expect(page.locator('nav a', { hasText: 'Login' })).toBeVisible()
  })

  test('navigate to About page', async ({ page }) => {
    await page.goto('/')
    await page.locator('nav a', { hasText: 'About' }).click()
    await expect(page).toHaveURL(/\/about/)
    await expect(page.locator('h2')).toHaveText('About')
  })

  test('navigate to Login page', async ({ page }) => {
    await page.goto('/')
    await page.locator('nav a', { hasText: 'Login' }).click()
    await expect(page).toHaveURL(/\/login/)
    await expect(page.locator('h2')).toHaveText('Login')
  })

  test('direct navigation to /login serves the SPA', async ({ page }) => {
    await page.goto('/login')
    await expect(page).toHaveURL(/\/login/)
    await expect(page.locator('h2')).toHaveText('Login')
  })

  test('direct navigation to /about serves the SPA', async ({ page }) => {
    await page.goto('/about')
    await expect(page).toHaveURL(/\/about/)
    await expect(page.locator('h2')).toHaveText('About')
  })

  test('direct navigation to unknown route shows Not Found page', async ({ page }) => {
    await page.goto('/this-does-not-exist')
    await expect(page.locator('h1')).toHaveText('404')
  })

  test('footer is visible with Creative Commons text', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('footer')).toBeVisible()
    await expect(page.locator('footer')).toContainText('Creative Commons')
  })
})
