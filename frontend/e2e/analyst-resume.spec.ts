import { expect, test } from '@playwright/test'
import { signInAs } from './support'

test.beforeEach(async ({ request }) => {
  await expect.poll(async () => (await request.get('/api/health')).status()).toBe(200)
})

test('analyst creates a frozen evaluation and resumes it after reload', async ({ page }) => {
  const suffix = crypto.randomUUID().slice(0, 8)
  const title = `LaunchScope browser study ${suffix}`
  await page.goto('/')
  await signInAs(page, 'analyst')

  await page.getByLabel('Initiative title').fill(title)
  await page.getByRole('button', { name: 'Save decision intake' }).click()
  await expect(page.getByText(/Initiative recorded/)).toBeVisible()
  await page.getByRole('button', { name: 'Save plan version' }).click()
  await expect(page.getByText('Plan v1 saved as a draft.')).toBeVisible()
  await page.getByRole('button', { name: 'Freeze plan v1' }).click()
  await expect(page.getByText('Plan v1 is frozen. Evaluation runs are now enabled.')).toBeVisible()
  await page.getByRole('button', { name: 'Calculate sensitivity', exact: true }).click()
  await expect(page.getByText(/Sensitivity result recorded/)).toBeVisible()
  await page.getByRole('button', { name: 'Generate & analyze scenario' }).click()
  await expect(page.getByText(/Synthetic tradeoff evaluation/)).toBeVisible()

  await page.getByLabel('Rationale').fill('The primary movement and guardrail tradeoff require redesign and another fixed-horizon evaluation.')
  await page.getByRole('button', { name: 'Save memo draft' }).click()
  await expect(page.getByText(/saved as a draft/)).toBeVisible()
  await expect(page.locator('.audit-trail')).toContainText('decision memo drafted')
  await page.reload()
  await expect(page.getByLabel('Resume plan version')).toBeVisible()

  const savedPlan = page.getByLabel('Resume plan version')
  await expect(savedPlan).toContainText(`${title} · v1 · frozen`)
  await savedPlan.selectOption({ label: `${title} · v1 · frozen` })
  await expect(page.getByText(`Resumed frozen plan v1 for ${title}.`)).toBeVisible()
  await expect(page.locator('.workspace-step').nth(2).getByText(/primary difference/)).toBeVisible()
  await expect(page.locator('.audit-trail')).toContainText('simulation run generated')
})