import type {
  AuthSession,
  DesignRecord,
  InitiativeRecord,
  MemoRecord,
  MemoReviewDetails,
  PlanRecord,
  ScenarioResult,
  Sensitivity,
  SimulationRecord,
  WorkspaceSnapshot,
} from './types'

const apiBase = import.meta.env.VITE_API_URL ?? ''

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    credentials: 'same-origin',
    headers: { ...(init?.headers ?? {}) },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null
    throw new Error(body?.detail ?? `Request failed (${response.status})`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

async function getJson<T>(path: string): Promise<T> {
  return requestJson<T>(path)
}

async function postJson<T>(path: string, payload: unknown, csrfToken?: string): Promise<T> {
  return requestJson<T>(path, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
    },
    body: JSON.stringify(payload),
  })
}

export function getScenario(id: string): Promise<ScenarioResult> {
  return getJson(`/api/demo/scenarios/${id}`)
}

export function getSensitivity(values: {
  baseline_rate: number
  target_effect: number
  available_households: number
  allocation_treatment: number
  alpha: number
  power: number
  attrition: number
}): Promise<Sensitivity> {
  const query = new URLSearchParams(Object.entries(values).map(([key, value]) => [key, String(value)]))
  return getJson(`/api/sensitivity?${query}`)
}

export function getAuthSession(): Promise<AuthSession> {
  return getJson('/api/auth/session')
}

export function login(username: string, password: string): Promise<AuthSession> {
  return postJson('/api/auth/login', { username, password })
}

export function logout(csrfToken: string): Promise<void> {
  return postJson('/api/auth/logout', {}, csrfToken)
}

export function createInitiative(csrfToken: string, payload: unknown): Promise<InitiativeRecord> {
  return postJson('/api/initiatives', payload, csrfToken)
}

export function createPlan(csrfToken: string, initiativeId: string, payload: unknown): Promise<PlanRecord> {
  return postJson(`/api/initiatives/${initiativeId}/plans`, payload, csrfToken)
}

export function freezePlan(csrfToken: string, planId: string): Promise<PlanRecord> {
  return postJson(`/api/plans/${planId}/freeze`, {}, csrfToken)
}

export function createDesignRun(
  csrfToken: string,
  planId: string,
  payload: { available_households: number; seed: number },
): Promise<DesignRecord> {
  return postJson(`/api/plans/${planId}/design-runs`, payload, csrfToken)
}

export function createSimulationRun(
  csrfToken: string,
  planId: string,
  payload: { scenario: string; seed: number; households_per_arm: number },
): Promise<SimulationRecord> {
  return postJson(`/api/plans/${planId}/simulation-runs`, payload, csrfToken)
}

export function createMemo(
  csrfToken: string,
  planId: string,
  payload: {
    analysis_result_id: string
    recommendation: string
    rationale: string
    limitations: string[]
    evidence_references: string[]
  },
): Promise<MemoRecord> {
  return postJson(`/api/plans/${planId}/memos`, payload, csrfToken)
}

export function reviewMemo(csrfToken: string, memoId: string): Promise<MemoRecord> {
  return postJson(`/api/memos/${memoId}/review`, {}, csrfToken)
}

export function getMemo(memoId: string): Promise<MemoReviewDetails> {
  return getJson(`/api/memos/${memoId}`)
}

export function getWorkspace(): Promise<WorkspaceSnapshot> {
  return getJson('/api/workspace')
}