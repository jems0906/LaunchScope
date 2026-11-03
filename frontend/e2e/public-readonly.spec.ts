import { expect, test } from '@playwright/test'

test.beforeEach(async ({ request }) => {
  await expect.poll(async () => (await request.get('/api/health')).status()).toBe(200)
})

test('public demo is readable but workspace data and writes are protected', async ({ page, request }) => {
  const sessionResponse = await request.get('/api/auth/session')
  expect(sessionResponse.status()).toBe(200)
  expect(await sessionResponse.json()).toEqual({ authenticated: false })
  expect([401, 503]).toContain((await request.get('/api/workspace')).status())
  expect([401, 503]).toContain((await request.post('/api/initiatives', { data: {} })).status())

  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Did this initiative succeed?' })).toBeVisible()
  await expect(page.getByRole('button', { name: /Analyst sign in/ })).toBeVisible()
  await expect(page.getByText('Read only')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Workspace' })).toHaveCount(0)
  await expect(page.locator('.plot-target .trace.bars')).toHaveCount(1)
})