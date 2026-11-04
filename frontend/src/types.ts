export type ArmSummary = {
  assigned: number
  observed: number
  missing: number
  qualified_sessions: number
  outcome_rate: number
  households_with_eligible_playback: number
  eligible_playback_sessions: number
  playback_failures: number
  playback_failure_rate: number | null
  stability_event_rate: number
}

export type Difference = {
  estimate: number
  interval_low: number
  interval_high: number
  p_value: number
  practical_threshold: number
  practically_positive: boolean
}

export type Guardrail = {
  difference: number
  interval_low: number
  interval_high: number
  harm_margin: number
  exceeds_harm_margin: boolean
  interval_excludes_no_harm: boolean
  control_failures?: number
  control_eligible_playback_sessions?: number
  control_households_with_eligible_playback?: number
  treatment_failures?: number
  treatment_eligible_playback_sessions?: number
  treatment_households_with_eligible_playback?: number
  uncertainty_method?: string
}

export type SubgroupQuestion = 'none' | 'prior_game_engagement'
export type SubgroupEffect = {
  estimate: number
  interval_low: number
  interval_high: number
  p_value: number
}
export type SubgroupArm = {
  assigned: number
  observed: number
  missing: number
  qualified_sessions: number
  outcome_rate: number | null
}
export type SubgroupGroup = {
  control: SubgroupArm
  treatment: SubgroupArm
  effect: SubgroupEffect | null
}
export type SubgroupAnalysis = {
  question: 'prior_game_engagement'
  label: string
  groups: Partial<Record<'no_prior_game_engagement' | 'prior_game_engagement', SubgroupGroup>>
  interaction: {
    estimate: number
    interval_low: number
    interval_high: number
    p_value: number
    contrast: string
    uncertainty_method: string
  } | null
  unavailable_reason?: string
  warnings: string[]
}

export type Analysis = {
  primary: Difference
  arms: { control: ArmSummary; treatment: ArmSummary }
  guardrails: { playback_quality: Guardrail; stability: Guardrail }
  subgroup_analysis?: SubgroupAnalysis | null
  diagnostics: {
    completeness_difference_treatment_minus_control: number
    missing_outcome_sensitivity: {
      lower: number
      upper: number
      interpretation: string
    }
    exposure_rate_treatment: number
    module_interaction_rate_treatment: number
    repeat_engagement_rate_treatment_observed: number
  }
  warnings: string[]
}

export type ScenarioResult = {
  scenario: string
  label: string
  description: string
  generator_version: string
  scenario_config_version: string
  analysis_version: string
  plan_reference: { plan_id: string; version: number; status: string }
  seed: number
  dataset_manifest: { synthetic: boolean; households_per_arm: number; row_count: number; sha256: string }
  result: Analysis
}

export type Sensitivity = {
  baseline_rate: number
  target_effect: number
  allocation_treatment: number
  alpha: number
  power: number
  attrition: number
  required_control: number
  required_treatment: number
  required_total: number
  effective_control: number
  effective_treatment: number
  effective_total: number
  detectable_effect: number
  detectable_treatment_rate: number
  detectable_effect_achievable: boolean
  algorithm_version: string
}

export type AuthSession = {
  authenticated: boolean
  username?: string
  role?: 'analyst' | 'reviewer'
  csrf_token?: string
}

export type InitiativeRecord = { id: string; title: string }
export type PlanRecord = { id: string; initiative_id: string; version: number; status: 'draft' | 'frozen' }
export type DesignRecord = { id: string; plan_id: string; results: Sensitivity }
export type SimulationRecord = {
  id: string
  analysis_result_id: string
  result: Analysis
  dataset_manifest: ScenarioResult['dataset_manifest']
  scenario: string
  seed: number
}
export type MemoRecord = { id: string; plan_id: string; review_state: 'draft' | 'reviewed' }
export type MemoReviewDetails = {
  id: string
  plan_id: string
  recommendation: string
  rationale: string
  limitations: string[]
  evidence_references: string[]
  review_state: 'draft' | 'reviewed'
  results: Analysis | null
}

export type WorkspaceInitiative = {
  id: string
  title: string
  business_question: string
  proposed_decision: string
  stakeholder_role: string
  eligible_population: string
  wrong_decision_consequences: string
  created_at: string
}

export type WorkspacePlan = {
  id: string
  initiative_id: string
  initiative_title: string
  version: number
  status: 'draft' | 'frozen'
  created_at: string
  frozen_at: string | null
  specification: Record<string, unknown>
}

export type WorkspaceDesignRun = {
  id: string
  plan_id: string
  results: Sensitivity
  created_at: string
}

export type WorkspaceSimulationRun = {
  id: string
  plan_id: string
  scenario: string
  seed: number
  analysis_result_id: string
  results: Analysis
  dataset_manifest: ScenarioResult['dataset_manifest']
  created_at: string
}

export type WorkspaceMemo = MemoReviewDetails & {
  created_at: string
  reviewed_at: string | null
}

export type WorkspaceAuditEvent = {
  id: number
  actor_username: string
  actor_role: 'analyst' | 'reviewer'
  action: string
  entity_type: string
  entity_id: string
  initiative_id: string | null
  plan_id: string | null
  details: Record<string, unknown>
  created_at: string
}

export type WorkspaceSnapshot = {
  user: { username: string; role: 'analyst' | 'reviewer' }
  initiatives: WorkspaceInitiative[]
  plans: WorkspacePlan[]
  design_runs: WorkspaceDesignRun[]
  simulation_runs: WorkspaceSimulationRun[]
  memos: WorkspaceMemo[]
  audit_events: WorkspaceAuditEvent[]
}