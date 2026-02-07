import { test, expect } from '@playwright/test'

test.describe('Navigation', () => {
  test('root redirects to /response-planner', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveURL(/\/response-planner/)
    await expect(page.locator('h2')).toHaveText('Response planner')
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

  test('direct navigation to unknown route returns server 404', async ({ page }) => {
    const response = await page.goto('/this-does-not-exist')
    expect(response.status()).toBe(404)
  })

  test('direct navigation to sub-path falls back to server', async ({ page }) => {
    const response = await page.goto('/nonexistent-page')
    expect(response.status()).toBe(404)
  })

  test('footer is visible with Creative Commons text', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('footer')).toBeVisible()
    await expect(page.locator('footer')).toContainText('Creative Commons')
  })
})
