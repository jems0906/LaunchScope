import { expect, type APIRequestContext, type Page } from '@playwright/test'

export function requiredEnv(name: 'E2E_ANALYST_USERNAME' | 'E2E_ANALYST_PASSWORD' | 'E2E_REVIEWER_USERNAME' | 'E2E_REVIEWER_PASSWORD'): string {
  const value = process.env[name]
  if (!value) throw new Error(`${name} must be set for browser E2E tests`)
  return value
}

export async function signInAs(page: Page, role: 'analyst' | 'reviewer'): Promise<void> {
  const username = requiredEnv(role === 'analyst' ? 'E2E_ANALYST_USERNAME' : 'E2E_REVIEWER_USERNAME')
  const password = requiredEnv(role === 'analyst' ? 'E2E_ANALYST_PASSWORD' : 'E2E_REVIEWER_PASSWORD')
  await page.getByRole('button', { name: /Analyst sign in/ }).click()
  await page.getByRole('dialog').getByLabel('Username').fill(username)
  await page.getByRole('dialog').getByLabel('Password').fill(password)
  await page.getByRole('dialog').getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('banner').getByText(new RegExp(`${role} · ${username}`))).toBeVisible()
}

export async function createDraftMemoThroughApi(request: APIRequestContext, suffix: string): Promise<string> {
  const username = requiredEnv('E2E_ANALYST_USERNAME')
  const password = requiredEnv('E2E_ANALYST_PASSWORD')
  const login = await request.post('/api/auth/login', { data: { username, password } })
  expect(login.status()).toBe(200)
  const sessionResponse = await request.get('/api/auth/session')
  const session = await sessionResponse.json() as { csrf_token: string }
  const headers = { 'X-CSRF-Token': session.csrf_token }

  const initiativeResponse = await request.post('/api/initiatives', {
    headers,
    data: {
      title: `Reviewer queue E2E ${suffix}`,
      business_question: 'Did offering the fictional module alter qualified household sessions?',
      proposed_decision: 'Continue, redesign, collect more evidence, or stop',
      alternatives: ['Existing discovery only', 'Redesign and retest'],
      stakeholder_role: 'Content & Games Product Lead',
      eligible_population: 'Households meeting eligibility rules before assignment',
      timing: 'One fixed 28-day observation window',
      wrong_decision_consequences: 'A false positive could worsen household experience.',
    },
  })
  expect(initiativeResponse.status()).toBe(201)
  const initiative = await initiativeResponse.json() as { id: string }

  const planResponse = await request.post(`/api/initiatives/${initiative.id}/plans`, {
    headers,
    data: {
      question: 'Did offering the module alter qualified household sessions?',
      estimand: 'Household intention-to-treat difference in qualified-session rates',
      population: 'All households eligible before assignment',
      eligibility_fixed_before_assignment: true,
      randomization_unit: 'household',
      allocation_treatment: 0.5,
      observation_window_days: 28,
      primary_outcome: 'Assigned-household rate with one qualified session',
      diagnostics: ['Exposure / assigned households', 'Module interaction / assigned households'],
      guardrails: ['Playback failures / eligible playback sessions'],
      baseline_rate: 0.10,
      target_effect: 0.01,
      alpha: 0.05,
      desired_power: 0.8,
      attrition: 0.05,
      missingness_rule: 'Unknown outcomes remain missing; completeness reported by arm.',
      spillover_assumption: 'Assume no material household interference.',
    },
  })
  expect(planResponse.status()).toBe(201)
  const plan = await planResponse.json() as { id: string }
  const freezeResponse = await request.post(`/api/plans/${plan.id}/freeze`, { headers, data: {} })
  expect(freezeResponse.status()).toBe(200)

  const simulationResponse = await request.post(`/api/plans/${plan.id}/simulation-runs`, {
    headers,
    data: { scenario: 'tradeoff', seed: 87123, households_per_arm: 150 },
  })
  expect(simulationResponse.status()).toBe(201)
  const simulation = await simulationResponse.json() as { id: string; analysis_result_id: string }
  const memoResponse = await request.post(`/api/plans/${plan.id}/memos`, {
    headers,
    data: {
      analysis_result_id: simulation.analysis_result_id,
      recommendation: 'redesign',
      rationale: 'The primary movement and playback harm require redesign and another evaluation.',
      limitations: ['Synthetic scenario', 'Fixed observation window'],
      evidence_references: [simulation.id, simulation.analysis_result_id],
    },
  })
  expect(memoResponse.status()).toBe(201)
  return (await memoResponse.json() as { id: string }).id
}