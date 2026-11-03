import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Check, ChevronRight, ClipboardCheck, FlaskConical, Gauge, LockKeyhole, Play, Save, ShieldCheck } from 'lucide-react'
import {
  createDesignRun,
  createInitiative,
  createMemo,
  createPlan,
  createSimulationRun,
  freezePlan,
  getMemo,
  getWorkspace,
  reviewMemo,
} from './api'
import type { Analysis, AuthSession, MemoRecord, MemoReviewDetails, Sensitivity, WorkspaceSnapshot } from './types'

type Props = {
  session: AuthSession & { username: string; role: 'analyst' | 'reviewer' }
  csrfToken: string
}

const scenarioOptions = [
  { id: 'helpful', label: 'Helpful signal' },
  { id: 'null', label: 'Null result' },
  { id: 'harmful', label: 'Harmful result' },
  { id: 'tradeoff', label: 'Tradeoff' },
]

export default function AnalystWorkspace({ session, csrfToken }: Props) {
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [initiativeId, setInitiativeId] = useState('')
  const [initiativeTitle, setInitiativeTitle] = useState('Game discovery module offer')
  const [businessQuestion, setBusinessQuestion] = useState('Did offering the game-discovery module change qualified game-session behavior?')
  const [eligiblePopulation, setEligiblePopulation] = useState('Households meeting eligibility rules recorded before assignment')
  const [wrongDecisionConsequences, setWrongDecisionConsequences] = useState('A false positive could worsen household experience or playback quality; a false negative could delay a useful discovery experience.')
  const [planId, setPlanId] = useState('')
  const [planVersion, setPlanVersion] = useState<number | null>(null)
  const [planStatus, setPlanStatus] = useState<'draft' | 'frozen' | ''>('')
  const [baselineRate, setBaselineRate] = useState(10)
  const [targetEffect, setTargetEffect] = useState(1)
  const [availableHouseholds, setAvailableHouseholds] = useState(10000)
  const [sensitivity, setSensitivity] = useState<Sensitivity | null>(null)
  const [scenario, setScenario] = useState('tradeoff')
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [analysisResultId, setAnalysisResultId] = useState('')
  const [simulationRunId, setSimulationRunId] = useState('')
  const [recommendation, setRecommendation] = useState('inconclusive')
  const [rationale, setRationale] = useState('')
  const [memo, setMemo] = useState<MemoRecord | null>(null)
  const [memoId, setMemoId] = useState('')
  const [reviewDetails, setReviewDetails] = useState<MemoReviewDetails | null>(null)
  const [workspace, setWorkspace] = useState<WorkspaceSnapshot | null>(null)

  async function refreshWorkspace() {
    try {
      setWorkspace(await getWorkspace())
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Could not load saved work.')
    }
  }

  useEffect(() => {
    void refreshWorkspace()
  }, [])

  async function runAction(action: () => Promise<void>) {
    setBusy(true)
    setMessage('')
    try {
      await action()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'The request could not be completed.')
    } finally {
      setBusy(false)
    }
  }

  async function submitInitiative(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await runAction(async () => {
      const result = await createInitiative(csrfToken, {
        title: initiativeTitle,
        business_question: businessQuestion,
        proposed_decision: 'Continue, redesign, collect more evidence, or stop',
        alternatives: ['Existing discovery only', 'Redesign and retest', 'No rollout'],
        stakeholder_role: 'Content & Games Product Lead',
        eligible_population: eligiblePopulation,
        timing: 'One fixed 28-day observation window after household assignment',
        wrong_decision_consequences: wrongDecisionConsequences,
      })
      setInitiativeId(result.id)
      setMessage(`Initiative recorded: ${result.id}`)
      await refreshWorkspace()
    })
  }

  async function submitPlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!initiativeId) return
    await runAction(async () => {
      const target = targetEffect / 100
      const result = await createPlan(csrfToken, initiativeId, {
        question: businessQuestion,
        estimand: 'Household intention-to-treat difference in qualified-session rates, treatment minus control',
        population: eligiblePopulation,
        eligibility_fixed_before_assignment: true,
        randomization_unit: 'household',
        allocation_treatment: 0.5,
        observation_window_days: 28,
        primary_outcome: 'Proportion of assigned households with at least one qualified game session in days 1-28',
        practical_threshold: target,
        diagnostics: ['Exposure / assigned households', 'Module interaction / assigned households', 'Repeat engagement / observed households', 'Outcome completeness / assigned households'],
        guardrails: ['Playback failures / eligible playback sessions', 'Stability events / assigned households'],
        baseline_rate: baselineRate / 100,
        target_effect: target,
        alpha: 0.05,
        desired_power: 0.8,
        attrition: 0.05,
        missingness_rule: 'Unknown outcomes stay missing; report completeness by assignment arm and assess extreme bounds.',
        spillover_assumption: 'Assume no material interference across households; investigate shared accounts and contamination.',
        fixed_horizon_no_early_stop: true,
      })
      setPlanId(result.id)
      setPlanVersion(result.version)
      setPlanStatus(result.status)
      setMessage(`Plan v${result.version} saved as a draft.`)
      await refreshWorkspace()
    })
  }

  async function freezeCurrentPlan() {
    await runAction(async () => {
      const result = await freezePlan(csrfToken, planId)
      setPlanStatus('frozen')
      setMessage(`Plan v${result.version} is frozen. Evaluation runs are now enabled.`)
      await refreshWorkspace()
    })
  }

  async function runDesign() {
    await runAction(async () => {
      const result = await createDesignRun(csrfToken, planId, {
        available_households: availableHouseholds,
        seed: 20261103,
      })
      setSensitivity(result.results)
      setMessage('Sensitivity result recorded against the frozen plan.')
      await refreshWorkspace()
    })
  }

  async function runScenario() {
    await runAction(async () => {
      const result = await createSimulationRun(csrfToken, planId, {
        scenario,
        seed: 20261103,
        households_per_arm: 2500,
      })
      setAnalysis(result.result)
      setAnalysisResultId(result.analysis_result_id)
      setSimulationRunId(result.id)
      setMemo(null)
      setMessage(`Synthetic ${scenario} evaluation and analysis recorded for plan v${planVersion}.`)
      await refreshWorkspace()
    })
  }

  async function submitMemo(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await runAction(async () => {
      const result = await createMemo(csrfToken, planId, {
        analysis_result_id: analysisResultId,
        recommendation,
        rationale,
        limitations: [
          'Synthetic scenario; not evidence about real users or outcomes.',
          'Effect concerns offering the module, not satisfaction, retention, or financial value.',
          'Guardrail nonsignificance does not establish absence of harm.',
        ],
        evidence_references: [simulationRunId, analysisResultId],
      })
      setMemo(result)
      setMemoId(result.id)
      setMessage(`Memo ${result.id} saved as a draft for separate reviewer sign-off.`)
      await refreshWorkspace()
    })
  }

  async function submitReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await runAction(async () => {
      const result = await reviewMemo(csrfToken, memoId)
      setReviewDetails((current) => current ? { ...current, review_state: result.review_state } : current)
      setMessage(`Memo ${result.id} marked reviewed.`)
      await refreshWorkspace()
    })
  }

  async function loadMemo(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await openMemo(memoId.trim())
  }

  async function openMemo(id: string) {
    setMemoId(id)
    await runAction(async () => {
      const result = await getMemo(id)
      setReviewDetails(result)
      setMessage(`Loaded memo ${result.id} and its linked analysis.`)
    })
  }

  function resumeInitiative(initiativeIdToResume: string) {
    const initiative = workspace?.initiatives.find((item) => item.id === initiativeIdToResume)
    if (!initiative) return
    setInitiativeId(initiative.id)
    setInitiativeTitle(initiative.title)
    setBusinessQuestion(initiative.business_question)
    setEligiblePopulation(initiative.eligible_population)
    setWrongDecisionConsequences(initiative.wrong_decision_consequences)
    setPlanId('')
    setPlanVersion(null)
    setPlanStatus('')
    setSensitivity(null)
    setAnalysis(null)
    setAnalysisResultId('')
    setSimulationRunId('')
    setMemo(null)
    setMessage(`Resumed initiative ${initiative.title}. Choose or create a plan version.`)
  }

  function resumePlan(planIdToResume: string) {
    const plan = workspace?.plans.find((item) => item.id === planIdToResume)
    if (!plan) return
    const initiative = workspace?.initiatives.find((item) => item.id === plan.initiative_id)
    const specification = plan.specification
    setInitiativeId(plan.initiative_id)
    setInitiativeTitle(plan.initiative_title)
    setBusinessQuestion(String(specification.question ?? ''))
    setEligiblePopulation(String(specification.population ?? ''))
    if (initiative) setWrongDecisionConsequences(initiative.wrong_decision_consequences)
    setPlanId(plan.id)
    setPlanVersion(plan.version)
    setPlanStatus(plan.status)
    if (typeof specification.baseline_rate === 'number') setBaselineRate(specification.baseline_rate * 100)
    if (typeof specification.target_effect === 'number') setTargetEffect(specification.target_effect * 100)
    const design = workspace?.design_runs.find((run) => run.plan_id === plan.id)
    setSensitivity(design?.results ?? null)
    const simulation = workspace?.simulation_runs.find((run) => run.plan_id === plan.id)
    setAnalysis(simulation?.results ?? null)
    setAnalysisResultId(simulation?.analysis_result_id ?? '')
    setSimulationRunId(simulation?.id ?? '')
    setScenario(simulation?.scenario ?? 'tradeoff')
    setMemo(null)
    setMessage(`Resumed frozen plan v${plan.version} for ${plan.initiative_title}.`)
  }

  return (
    <section id="analyst-workspace" className="page-section detail-section analyst-workspace">
      <div className="section-heading">
        <div><span className="eyebrow">ANALYST WORKSPACE / AUTHENTICATED</span><h2>Version, freeze, evaluate, document.</h2></div>
        <span className="role-badge"><ShieldCheck size={13} /> {session.role} · {session.username}</span>
      </div>
      <div className="workspace-intro"><LockKeyhole size={15} /><span>Writes use your signed same-site session. Frozen criteria cannot be edited; create a new plan version to change them.</span></div>
      {message && <div className="workspace-message" role="status">{busy && <span className="loading-dot" />}{message}</div>}
      {workspace && <div className="workspace-history">
        {session.role === 'analyst' ? <>
          <label>Resume initiative<select defaultValue="" onChange={(event) => event.target.value && resumeInitiative(event.target.value)}><option value="">Choose a saved initiative</option>{workspace.initiatives.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
          <label>Resume plan version<select defaultValue="" onChange={(event) => event.target.value && resumePlan(event.target.value)}><option value="">Choose a plan version</option>{workspace.plans.map((item) => <option key={item.id} value={item.id}>{item.initiative_title} · v{item.version} · {item.status}</option>)}</select></label>
          <span className="history-count">{workspace.initiatives.length} initiatives · {workspace.plans.length} plan versions · {workspace.simulation_runs.length} evaluations · {workspace.memos.length} memos</span>
        </> : <>
          <div className="review-queue-head"><strong>Pending review</strong><span>{workspace.memos.filter((item) => item.review_state === 'draft').length}</span></div>
          {workspace.memos.filter((item) => item.review_state === 'draft').map((item) => <button className="queue-item" key={item.id} onClick={() => void openMemo(item.id)}><span><strong>{item.recommendation.replaceAll('_', ' ')}</strong><small>{item.id} · plan {item.plan_id}</small></span><ChevronRight size={14} /></button>)}
          {workspace.memos.every((item) => item.review_state !== 'draft') && <p className="queue-empty">No pending memos.</p>}
        </>}
      </div>}

      {session.role === 'analyst' ? (
        <>
          <div className="workspace-step-grid">
            <section className="workspace-step">
              <div className="workspace-step-head"><span>01</span><div><h3>Decision intake</h3><small>{initiativeId ? `Saved · ${initiativeId}` : 'Capture owner, population, and consequences'}</small></div>{initiativeId && <Check size={16} />}</div>
              <form className="workspace-form" onSubmit={submitInitiative}>
                <label>Initiative title<input value={initiativeTitle} maxLength={160} onChange={(event) => setInitiativeTitle(event.target.value)} required /></label>
                <label>Business question<textarea value={businessQuestion} maxLength={1000} rows={2} onChange={(event) => setBusinessQuestion(event.target.value)} required /></label>
                <label>Eligible population<textarea value={eligiblePopulation} maxLength={1000} rows={2} onChange={(event) => setEligiblePopulation(event.target.value)} required /></label>
                <label>Consequences of a wrong decision<textarea value={wrongDecisionConsequences} maxLength={2000} rows={2} onChange={(event) => setWrongDecisionConsequences(event.target.value)} required /></label>
                <button className="workspace-button" type="submit" disabled={busy || Boolean(initiativeId)}><Save size={14} /> {initiativeId ? 'Intake recorded' : 'Save decision intake'}</button>
              </form>
            </section>

            <section className="workspace-step">
              <div className="workspace-step-head"><span>02</span><div><h3>Measurement contract</h3><small>{planId ? `Plan v${planVersion} · ${planStatus}` : 'Prespecify outcome, assumptions, and horizon'}</small></div>{planStatus === 'frozen' && <LockKeyhole size={15} />}</div>
              <form className="workspace-form" onSubmit={submitPlan}>
                <label>Baseline outcome rate (%)<input type="number" min="0.1" max="99" step="0.1" value={baselineRate} onChange={(event) => setBaselineRate(Number(event.target.value))} /></label>
                <label>Practical threshold (percentage points)<input type="number" min="0.1" max="40" step="0.1" value={targetEffect} onChange={(event) => setTargetEffect(Number(event.target.value))} /></label>
                <p className="workspace-contract">Household randomization · 1:1 allocation · 28-day fixed horizon · ITT primary outcome · eligible-session playback guardrail</p>
                {!planId ? <button className="workspace-button" type="submit" disabled={busy || !initiativeId}><ClipboardCheck size={14} /> Save plan version</button> : (
                  <div className="workspace-actions">
                    {planStatus === 'draft' ? <button className="workspace-button freeze-button" type="button" onClick={freezeCurrentPlan} disabled={busy}><LockKeyhole size={14} /> Freeze plan v{planVersion}</button> : <span className="frozen-inline"><Check size={13} /> Frozen v{planVersion}</span>}
                    <button className="workspace-button secondary-button" type="button" onClick={submitPlanAsNew} disabled={busy || planStatus !== 'frozen'}>Create next version</button>
                  </div>
                )}
              </form>
            </section>

            <section className="workspace-step">
              <div className="workspace-step-head"><span>03</span><div><h3>Sensitivity & evaluation</h3><small>{planStatus === 'frozen' ? 'Runs reference the frozen plan version' : 'Freeze the plan to enable evaluation'}</small></div><FlaskConical size={16} /></div>
              <div className="workspace-form">
                <label>Available households<input type="number" min="4" max="1000000" step="100" value={availableHouseholds} onChange={(event) => setAvailableHouseholds(Number(event.target.value))} /></label>
                <div className="workspace-actions">
                  <button className="workspace-button" type="button" onClick={runDesign} disabled={busy || planStatus !== 'frozen'}><Gauge size={14} /> Calculate sensitivity</button>
                  <span className="workspace-seed">Seed fixed · 20261103</span>
                </div>
                {sensitivity && <div className="workspace-result"><strong>{sensitivity.required_total.toLocaleString()}</strong> required · {sensitivity.effective_total.toLocaleString()} effective · detectable {sensitivity.detectable_effect_achievable ? `${(sensitivity.detectable_effect * 100).toFixed(2)} pp` : 'not attainable'}</div>}
                <label>Fixed synthetic scenario<select value={scenario} onChange={(event) => setScenario(event.target.value)}>{scenarioOptions.map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}</select></label>
                <button className="workspace-button" type="button" onClick={runScenario} disabled={busy || planStatus !== 'frozen'}><Play size={14} /> Generate & analyze scenario</button>
                {analysis && <div className="workspace-result"><strong>{(analysis.primary.estimate * 100).toFixed(2)} pp</strong> primary difference · playback {((analysis.guardrails.playback_quality.difference) * 100).toFixed(2)} pp</div>}
              </div>
            </section>

            <section className="workspace-step">
              <div className="workspace-step-head"><span>04</span><div><h3>Decision memo</h3><small>{memo ? `Draft · ${memo.id}` : 'Attach the analysis and record a human recommendation'}</small></div><ClipboardCheck size={16} /></div>
              <form className="workspace-form" onSubmit={submitMemo}>
                <label>Stakeholder recommendation<select value={recommendation} onChange={(event) => setRecommendation(event.target.value)}><option value="continue">Continue</option><option value="redesign">Redesign</option><option value="collect_more_evidence">Collect more evidence</option><option value="stop">Stop</option><option value="inconclusive">Inconclusive</option><option value="cannot_answer">This design cannot answer the question</option></select></label>
                <label>Rationale<textarea value={rationale} minLength={20} maxLength={4000} rows={3} onChange={(event) => setRationale(event.target.value)} required /></label>
                <button className="workspace-button" type="submit" disabled={busy || !analysisResultId || !rationale.trim()}><Save size={14} /> Save memo draft</button>
                {memo && <p className="workspace-result">Share memo reference <code>{memo.id}</code> with the reviewer. Review is a separate role.</p>}
              </form>
            </section>
          </div>
        </>
      ) : (
        <section className="review-step">
          <div className="workspace-step-head"><span>01</span><div><h3>Reviewer sign-off</h3><small>Review a draft memo using its evidence-linked ID.</small></div><ShieldCheck size={16} /></div>
          <form className="workspace-form review-form" onSubmit={loadMemo}>
            <label>Draft memo ID<input value={memoId} onChange={(event) => setMemoId(event.target.value)} minLength={8} required /></label>
            <button className="workspace-button secondary-button" type="submit" disabled={busy || !memoId.trim()}><ClipboardCheck size={14} /> Load evidence</button>
          </form>
          {reviewDetails && <div className="review-evidence"><div className="review-evidence-head"><strong>Memo {reviewDetails.id}</strong><span className={reviewDetails.review_state === 'reviewed' ? 'reviewed-tag' : 'draft-tag'}>{reviewDetails.review_state}</span></div><p><span>Recommendation</span>{reviewDetails.recommendation.replaceAll('_', ' ')}</p><p><span>Rationale</span>{reviewDetails.rationale}</p><p><span>Primary ITT</span>{reviewDetails.results ? `${(reviewDetails.results.primary.estimate * 100).toFixed(2)} pp · 95% ${(reviewDetails.results.primary.interval_low * 100).toFixed(2)} to ${(reviewDetails.results.primary.interval_high * 100).toFixed(2)} pp` : 'Unavailable'}</p><p><span>Playback guardrail</span>{reviewDetails.results ? `${(reviewDetails.results.guardrails.playback_quality.difference * 100).toFixed(2)} pp · 95% ${(reviewDetails.results.guardrails.playback_quality.interval_low * 100).toFixed(2)} to ${(reviewDetails.results.guardrails.playback_quality.interval_high * 100).toFixed(2)} pp` : 'Unavailable'}</p><p><span>Limitations</span>{reviewDetails.limitations.join(' ')}</p><p><span>Evidence IDs</span>{reviewDetails.evidence_references.join(' · ')}</p><form onSubmit={submitReview}><button className="workspace-button freeze-button" type="submit" disabled={busy || reviewDetails.review_state !== 'draft'}><Check size={14} /> Mark reviewed</button></form></div>}
        </section>
      )}
    </section>
  )

  async function submitPlanAsNew() {
    setPlanId('')
    setPlanStatus('')
    setPlanVersion(null)
    setSensitivity(null)
    setAnalysis(null)
    setAnalysisResultId('')
    setSimulationRunId('')
    setMemo(null)
    setMessage('Previous version remains frozen. Save the next specification as a new version.')
  }
}