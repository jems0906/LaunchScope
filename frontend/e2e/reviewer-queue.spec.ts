import { expect, test } from '@playwright/test'
import { createDraftMemoThroughApi, signInAs, waitForApi } from './support'

test.beforeEach(async ({ request }) => {
  await waitForApi(request)
})

test('reviewer inspects linked estimates and approves a queued memo', async ({ browser, request }) => {
  const memoId = await createDraftMemoThroughApi(request, crypto.randomUUID().slice(0, 8))
  const context = await browser.newContext()
  const page = await context.newPage()
  await page.goto('/')
  await signInAs(page, 'reviewer')

  const queuedMemo = page.locator('.queue-item').filter({ hasText: memoId })
  await expect(queuedMemo).toBeVisible()
  await queuedMemo.click()
  await expect(page.getByText('Primary ITT', { exact: true })).toBeVisible()
  await expect(page.getByText('Playback guardrail', { exact: true })).toBeVisible()
  await expect(page.getByText(/Interaction \(prior minus no prior\)/)).toBeVisible()
  await expect(page.getByText(/Synthetic scenario/)).toBeVisible()

  await page.getByRole('button', { name: 'Mark reviewed' }).click()
  await expect(page.locator('.reviewed-tag')).toHaveText('reviewed')
  await expect(page.locator('.audit-trail')).toContainText('decision memo reviewed')
  await expect(queuedMemo).toHaveCount(0)
  await context.close()
})