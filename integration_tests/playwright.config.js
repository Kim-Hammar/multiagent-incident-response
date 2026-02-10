import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  timeout: 30000,
  retries: 0,
  workers: 1,
  use: {
    baseURL: 'http://localhost:8888',
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'on-first-retry'
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
      testIgnore: /digital-twin\.spec\.js/
    },
    {
      name: 'digital-twin',
      timeout: 300000,
      testMatch: /digital-twin\.spec\.js/,
      dependencies: ['chromium']
    }
  ]
})
