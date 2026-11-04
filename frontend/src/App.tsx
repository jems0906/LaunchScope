import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  Beaker,
  BookOpenCheck,
  ChartNoAxesCombined,
  Check,
  ChevronRight,
  CircleHelp,
  ClipboardList,
  FlaskConical,
  Gauge,
  LockKeyhole,
  LogIn,
  LogOut,
  ShieldAlert,
  Target,
} from 'lucide-react'
import { getAuthSession, getScenario, getSensitivity, login, logout } from './api'
import AnalystWorkspace from './AnalystWorkspace'
import type { AuthSession, ScenarioResult, Sensitivity } from './types'

const sections = [
  { id: 'overview', label: 'Overview', icon: ChartNoAxesCombined },
  { id: 'intake', label: 'Decision intake', icon: ClipboardList },
  { id: 'question', label: 'Question & estimand', icon: CircleHelp },
  { id: 'tree', label: 'Measurement tree', icon: Activity },
  { id: 'design', label: 'Design planner', icon: Beaker },
  { id: 'sensitivity', label: 'Sensitivity', icon: Gauge },
  { id: 'scenarios', label: 'Scenarios', icon: FlaskConical },
  { id: 'memo', label: 'Decision memo', icon: BookOpenCheck },
]

const scenarios = [
  { id: 'helpful', label: 'Helpful signal', note: 'Primary outcome moves; guardrails stay within configured margins.' },
  { id: 'null', label: 'Null result', note: 'No configured primary outcome or playback-quality difference.' },
  { id: 'harmful', label: 'Harmful result', note: 'Primary outcome declines and quality events rise.' },
  { id: 'tradeoff', label: 'Tradeoff', note: 'Primary outcome rises while playback quality worsens.' },
]

function pct(value: number | null | undefined, digits = 1) {
  return value == null ? 'Unknown' : `${(value * 100).toFixed(digits)}%`
}

function points(value: number | null | undefined) {
  if (value == null) return '—'
  const sign = value > 0 ? '+' : ''
  return `${sign}${(value * 100).toFixed(2)} pp`
}

function App() {
  const [activeSection, setActiveSection] = useState('overview')
  const [scenarioId, setScenarioId] = useState('tradeoff')
  const [scenario, setScenario] = useState<ScenarioResult | null>(null)
  const [scenarioError, setScenarioError] = useState('')
  const [loadingScenario, setLoadingScenario] = useState(true)
  const [baseline, setBaseline] = useState(10)
  const [target, setTarget] = useState(1)
  const [sample, setSample] = useState(10000)
  const [sensitivity, setSensitivity] = useState<Sensitivity | null>(null)
  const [sensitivityError, setSensitivityError] = useState('')
  const [loadingSensitivity, setLoadingSensitivity] = useState(false)
  const [authSession, setAuthSession] = useState<AuthSession | null>(null)
  const [csrfToken, setCsrfToken] = useState('')
  const [loginOpen, setLoginOpen] = useState(false)
  const [loginUsername, setLoginUsername] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [authError, setAuthError] = useState('')
  const plotTarget = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getAuthSession()
      .then((session) => {
        setAuthSession(session)
        setCsrfToken(session.csrf_token ?? '')
      })
      .catch(() => setAuthSession({ authenticated: false }))
  }, [])

  useEffect(() => {
    let active = true
    setLoadingScenario(true)
    setScenarioError('')
    getScenario(scenarioId)
      .then((value) => { if (active) setScenario(value) })
      .catch(() => { if (active) setScenarioError('The scenario service is unavailable. Start the API and try again.') })
      .finally(() => { if (active) setLoadingScenario(false) })
    return () => { active = false }
  }, [scenarioId])

  useEffect(() => {
    runSensitivity()
  }, [])

  async function runSensitivity() {
    setLoadingSensitivity(true)
    setSensitivityError('')
    try {
      const result = await getSensitivity({
        baseline_rate: baseline / 100,
        target_effect: target / 100,
        available_households: sample,
        allocation_treatment: 0.5,
        alpha: 0.05,
        power: 0.8,
        attrition: 0.05,
      })
      setSensitivity(result)
    } catch {
      setSensitivityError('Sensitivity calculation unavailable. Check that the API is running.')
    } finally {
      setLoadingSensitivity(false)
    }
  }

  function navigate(id: string) {
    setActiveSection(id)
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  async function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAuthError('')
    try {
      const session = await login(loginUsername, loginPassword)
      setAuthSession(session)
      setCsrfToken(session.csrf_token ?? '')
      setLoginPassword('')
      setLoginOpen(false)
      requestAnimationFrame(() => navigate('analyst-workspace'))
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : 'Sign-in failed.')
    }
  }

  async function signOut() {
    try {
      if (csrfToken) await logout(csrfToken)
    } catch {
      // Clear the local view even if the cookie has expired.
    }
    setAuthSession({ authenticated: false })
    setCsrfToken('')
  }

  const analysis = scenario?.result
  const primary = analysis?.primary
  const effect = primary?.estimate ?? 0
  const isPositive = effect >= 0

  useEffect(() => {
    const target = plotTarget.current
    if (!target || !analysis) return
    let cancelled = false
    let plotly: typeof import('plotly.js-basic-dist-min').default | undefined
    void import('plotly.js-basic-dist-min').then(({ default: Plotly }) => {
      if (cancelled) return
      plotly = Plotly
      return Plotly.newPlot(
        target,
        [{
          type: 'bar',
          orientation: 'h',
          y: ['Treatment', 'Control'],
          x: [analysis.arms.treatment.outcome_rate * 100, analysis.arms.control.outcome_rate * 100],
          marker: { color: ['#c95738', '#8eaa9b'], line: { width: 0 } },
          text: [pct(analysis.arms.treatment.outcome_rate), pct(analysis.arms.control.outcome_rate)],
          textposition: 'outside',
          cliponaxis: false,
          hovertemplate: '%{y}: %{x:.2f}%<extra></extra>',
        }],
        {
          autosize: true,
          height: 128,
          margin: { l: 78, r: 45, t: 4, b: 28 },
          paper_bgcolor: 'transparent',
          plot_bgcolor: 'transparent',
          font: { family: 'DM Sans, sans-serif', size: 11, color: '#66716a' },
          xaxis: { range: [0, Math.max(15, analysis.arms.treatment.outcome_rate * 100 * 1.3)], ticksuffix: '%', gridcolor: '#e5e9e1', zeroline: false, fixedrange: true },
          yaxis: { fixedrange: true, automargin: true },
          showlegend: false,
          bargap: 0.45,
        },
        { displayModeBar: false, responsive: true },
      )
    })
    return () => {
      cancelled = true
      plotly?.purge(target)
    }
  }, [analysis])

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#overview" onClick={(event) => { event.preventDefault(); navigate('overview') }}>
          <span className="brand-mark"><Target size={19} strokeWidth={2.2} /></span>
          <span>LaunchScope</span>
          <span className="brand-divider" />
          <span className="brand-product">Measurement Design Lab</span>
        </a>
        <div className="topbar-right">
          <span className="synthetic-label"><span className="status-dot" /> Synthetic study</span>
          {authSession?.authenticated && authSession.username && authSession.role && csrfToken ? (
            <>
              <span className="role-badge"><span className="status-dot" /> {authSession.role} · {authSession.username}</span>
              <button className="header-action" onClick={() => navigate('analyst-workspace')} title="Open analyst workspace"><ClipboardList size={15} /> Workspace</button>
              <button className="icon-action" onClick={signOut} title="Sign out"><LogOut size={15} /></button>
            </>
          ) : (
            <>
              <span className="read-only"><ShieldAlert size={14} /> Read only</span>
              <button className="header-action" onClick={() => { setLoginOpen(true); setAuthError('') }}><LogIn size={15} /> Analyst sign in</button>
            </>
          )}
        </div>
      </header>

      <aside className="sidebar">
        <div className="side-caption">WORKSPACE</div>
        <div className="initiative-mini">
          <div className="initiative-icon">G</div>
          <div><strong>Game discovery</strong><span>Initiative · v1 frozen</span></div>
        </div>
        <div className="side-caption section-caption">STUDY WORKFLOW</div>
        <nav className="side-nav" aria-label="Study workflow">
          {sections.map(({ id, label, icon: Icon }, index) => (
            <button
              className={`nav-item ${activeSection === id ? 'active' : ''}`}
              key={id}
              onClick={() => navigate(id)}
              title={label}
            >
              <span className="nav-icon"><Icon size={16} /></span>
              <span>{label}</span>
              {index < 4 && <Check className="nav-check" size={13} />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="frozen-box"><span className="lock-mark"><Check size={12} /></span><div><strong>Plan frozen</strong><span>Version 1 · 28-day horizon</span></div></div>
          <p>Blueprint for fictional initiatives and synthetic data. Not Netflix methodology or outcomes.</p>
        </div>
      </aside>

      <main className="main-content">
        {authSession?.authenticated && authSession.username && authSession.role && csrfToken && (
          <AnalystWorkspace
            session={{ ...authSession, username: authSession.username, role: authSession.role }}
            csrfToken={csrfToken}
          />
        )}
        <section id="overview" className="page-section overview-section">
          <div className="breadcrumb"><span>Content & Games</span><ChevronRight size={13} /><span>Measurement design</span><ChevronRight size={13} /><strong>Game discovery offer</strong></div>
          <div className="hero-row">
            <div>
              <div className="eyebrow"><span className="eyebrow-line" /> DECISION STUDY <span className="version-tag">PLAN V1</span></div>
              <h1>Did this initiative<br /><em>succeed?</em></h1>
              <p className="hero-copy">A fictional game-discovery module, evaluated through one prespecified outcome, a household-level experiment, and explicit decision boundaries.</p>
            </div>
            <div className="study-stamp"><span className="stamp-icon"><FlaskConical size={18} /></span><div><strong>Educational blueprint</strong><span>Fictional initiative · synthetic results</span></div></div>
          </div>

          <div className="stat-strip">
            <div className="stat-cell"><span className="stat-label">PRIMARY ESTIMAND</span><strong>Intention to treat</strong><small>Effect of offering the module</small></div>
            <div className="stat-cell"><span className="stat-label">ASSIGNMENT UNIT</span><strong>Household</strong><small>1:1 randomized allocation</small></div>
            <div className="stat-cell"><span className="stat-label">OBSERVATION WINDOW</span><strong>28 days</strong><small>Fixed horizon · no early stop</small></div>
            <div className="stat-cell"><span className="stat-label">DECISION OWNER</span><strong>Product Lead</strong><small>Stakeholder judgment retained</small></div>
          </div>

          <div className="section-heading results-heading">
            <div><span className="eyebrow">01 / EVIDENCE SNAPSHOT</span><h2>One primary result. Guardrails stay visible.</h2></div>
            <button className="text-action" onClick={() => navigate('scenarios')}>Explore scenarios <ChevronRight size={15} /></button>
          </div>

          {scenarioError ? <div className="error-banner">{scenarioError}</div> : null}
          <div className="evidence-grid">
            <div className="primary-evidence">
              <div className="evidence-topline"><span className="pill-label"><span className="pill-dot" /> PRIMARY OUTCOME</span><span className="synthetic-note">SYNTHETIC RESULT</span></div>
              <div className="metric-title">Qualified game session <span>per assigned household</span></div>
              <div className="effect-line">
                <strong className={isPositive ? 'positive' : 'negative'}>{loadingScenario ? '…' : points(primary?.estimate)}</strong>
                <span className={`effect-direction ${isPositive ? 'up' : 'down'}`}>{isPositive ? <ArrowUpRight size={15} /> : <ArrowDownRight size={15} />}{scenario?.label ?? 'Loading'}</span>
              </div>
              <div className="interval-line"><span>95% interval</span><strong>{loadingScenario ? '…' : `${points(primary?.interval_low)} to ${points(primary?.interval_high)}`}</strong><span className="interval-p">p = {primary?.p_value.toFixed(3) ?? '—'}</span></div>
              <div className="plot-wrap">
                {analysis ? <div className="plot-target" ref={plotTarget} /> : <div className="plot-placeholder">Loading assigned-household rates…</div>}
              </div>
              <div className="threshold-note"><span className="threshold-mark" /> Practical threshold <strong>+1.00 pp</strong><span className="threshold-separator" />{primary?.practically_positive ? 'Interval clears threshold' : 'Interval does not establish threshold'} </div>
            </div>

            <div className="guardrail-column">
              <div className="guardrail-head"><span className="eyebrow">PRESPECIFIED GUARDRAILS</span><span className="guardrail-count">02</span></div>
              <div className={`guardrail-row ${analysis?.guardrails.playback_quality.exceeds_harm_margin ? 'harm' : ''}`}>
                <div className="guardrail-name"><span className="guardrail-icon"><Activity size={15} /></span><div><strong>Playback quality</strong><span>Failures / eligible playback sessions</span></div></div>
                <strong className="guardrail-value">{loadingScenario ? '…' : points(analysis?.guardrails.playback_quality.difference)}</strong>
                <div className="guardrail-sub">95% interval {points(analysis?.guardrails.playback_quality.interval_low)} to {points(analysis?.guardrails.playback_quality.interval_high)} · harm margin +0.50 pp</div>
                <div className="guardrail-denominator">Control {analysis?.guardrails.playback_quality.control_failures ?? '—'} / {analysis?.guardrails.playback_quality.control_eligible_playback_sessions ?? '—'} ({analysis?.guardrails.playback_quality.control_households_with_eligible_playback ?? '—'} households) · Treatment {analysis?.guardrails.playback_quality.treatment_failures ?? '—'} / {analysis?.guardrails.playback_quality.treatment_eligible_playback_sessions ?? '—'} ({analysis?.guardrails.playback_quality.treatment_households_with_eligible_playback ?? '—'} households)</div>
                <span className={`guardrail-status ${analysis?.guardrails.playback_quality.exceeds_harm_margin ? 'status-harm' : ''}`}>{analysis?.guardrails.playback_quality.exceeds_harm_margin ? 'MARGIN EXCEEDED' : 'WITHIN MARGIN'}</span>
              </div>
              <div className={`guardrail-row ${analysis?.guardrails.stability.exceeds_harm_margin ? 'harm' : ''}`}>
                <div className="guardrail-name"><span className="guardrail-icon"><Gauge size={15} /></span><div><strong>Stability</strong><span>Events / assigned households</span></div></div>
                <strong className="guardrail-value">{loadingScenario ? '…' : points(analysis?.guardrails.stability.difference)}</strong>
                <div className="guardrail-sub">95% interval {points(analysis?.guardrails.stability.interval_low)} to {points(analysis?.guardrails.stability.interval_high)} · harm margin +0.50 pp</div>
                <span className={`guardrail-status ${analysis?.guardrails.stability.exceeds_harm_margin ? 'status-harm' : ''}`}>{analysis?.guardrails.stability.exceeds_harm_margin ? 'MARGIN EXCEEDED' : 'WITHIN MARGIN'}</span>
              </div>
              <div className="guardrail-caveat"><ShieldAlert size={16} /><span>A nonsignificant guardrail test is <strong>not</strong> evidence that harm is absent.</span></div>
              <p className="guardrail-footnote">Intervals preserve within-household dependence; households with zero eligible playback sessions remain visible in the assigned population but contribute no playback denominator.</p>
            </div>
          </div>
          <div className="scenario-selector-line"><span>Currently viewing</span><strong>{scenario?.label ?? 'Scenario'}</strong><span className="scenario-separator">/</span><span>{scenario?.description}</span><button onClick={() => navigate('scenarios')}>Change scenario <ChevronRight size={14} /></button></div>
        </section>

        <section id="intake" className="page-section detail-section">
          <div className="section-heading"><div><span className="eyebrow">02 / DECISION INTAKE</span><h2>Start with the decision, not a metric.</h2></div><span className="section-index">01—08</span></div>
          <div className="intake-layout">
            <div className="intake-question"><span className="field-label">PROPOSED DECISION</span><p>Should the stakeholder continue, revise, or stop offering the module after the fixed evaluation window?</p><span className="role-tag">ACCOUNTABLE ROLE <strong>Content & Games Product Lead</strong></span></div>
            <div className="intake-fields">
              <div><span className="field-label">ALTERNATIVES</span><p>Existing discovery only · limited redesign and retest · no rollout</p></div>
              <div><span className="field-label">ELIGIBLE POPULATION</span><p>Households meeting eligibility rules recorded before assignment</p></div>
              <div><span className="field-label">TIMING</span><p>28 days after assignment · one fixed horizon · no early efficacy stop</p></div>
              <div className="consequence-fields"><div><span className="field-label">COST OF A FALSE POSITIVE</span><p>Continue an offer that may worsen household experience or playback quality.</p></div><div><span className="field-label">COST OF A FALSE NEGATIVE</span><p>Delay or abandon a useful discovery experience.</p></div></div>
            </div>
          </div>
        </section>

        <section id="question" className="page-section detail-section">
          <div className="section-heading"><div><span className="eyebrow">03 / QUESTION → ESTIMAND</span><h2>Four questions. One this study answers.</h2></div><span className="section-index">02—08</span></div>
          <div className="estimand-grid">
            <div className="estimand-card selected"><span className="estimand-num">01</span><span className="estimand-type">INCREMENTAL BEHAVIOR</span><h3>Did the offer change qualified sessions?</h3><p>Probability an eligible assigned household has ≥1 qualified game session in days 1–28.</p><span className="answered-tag"><Check size={12} /> ANSWERED BY THIS DESIGN</span></div>
            <div className="estimand-card"><span className="estimand-num">02</span><span className="estimand-type">REACH</span><h3>Did eligible households see it?</h3><p>Exposure rate by assigned arm. Diagnostic only; exposure is post-assignment.</p><span className="not-primary">DIAGNOSTIC</span></div>
            <div className="estimand-card"><span className="estimand-num">03</span><span className="estimand-type">ENGAGEMENT</span><h3>Did households interact or return?</h3><p>Module interaction and repeat engagement, with assignment-based denominators.</p><span className="not-primary">DIAGNOSTIC</span></div>
            <div className="estimand-card boundary-card"><span className="estimand-num">04</span><span className="estimand-type">LONGER-HORIZON VALUE</span><h3>Did satisfaction or retention improve?</h3><p>A 28-day session outcome cannot establish satisfaction, retention, or financial value.</p><span className="boundary-tag">OUTSIDE THIS DESIGN</span></div>
          </div>
          <div className="causal-boundary"><span className="boundary-symbol">!</span><p><strong>Interpretation boundary</strong> The estimand is the effect of <em>offering</em> the module. Never condition the main comparison on clicking it or launching a game; those are post-assignment behaviors. Demo plan V1 has no confirmatory subgroup claim; analysts can prespecify one baseline prior-engagement question in a new version.</p></div>
        </section>

        <section id="tree" className="page-section detail-section">
          <div className="section-heading"><div><span className="eyebrow">04 / MEASUREMENT TREE</span><h2>Business question, operationalized.</h2></div><span className="section-index">03—08</span></div>
          <div className="tree-layout">
            <div className="tree-root"><span className="tree-overline">BUSINESS QUESTION</span><strong>Did offering the game-discovery module change qualified game-session behavior?</strong><span className="tree-root-foot"><Target size={14} /> Household assignment · intention to treat</span></div>
            <div className="tree-branches">
              <div className="tree-outcome primary-node"><span className="node-type">PRIMARY OUTCOME</span><strong>≥1 qualified game session</strong><small>Household rate · 28-day window</small><span className="node-denom">Observed households; unknown ≠ zero</span></div>
              <div className="tree-diagnostics"><span className="node-type">SECONDARY DIAGNOSTICS</span><div><span>Exposure</span><small>/ assigned households</small></div><div><span>Module interaction</span><small>/ assigned households</small></div><div><span>Repeat engagement</span><small>/ observed households</small></div><div><span>Outcome completeness</span><small>/ assigned households</small></div></div>
              <div className="tree-guardrails"><span className="node-type">GUARDRAILS</span><div><span>Playback-quality failure</span><small>Failures / eligible playback sessions</small></div><div><span>Stability event</span><small>/ assigned households</small></div></div>
            </div>
          </div>
          <div className="definition-note"><span>!</span><p>Session qualification and playback-failure events are fictional documented rules fixed before analysis, not Netflix definitions. Playback-quality rates use failures divided by eligible playback sessions; uncertainty is clustered at the randomized household.</p></div>
        </section>

        <section id="design" className="page-section detail-section">
          <div className="section-heading"><div><span className="eyebrow">05 / DESIGN PLANNER</span><h2>Assignment determines the analysis unit.</h2></div><span className="section-index">04—08</span></div>
          <div className="design-table">
            <div className="design-row"><span>Randomization unit</span><strong>Household</strong><small>Aggregate or resample at household level; preserve within-household dependence.</small></div>
            <div className="design-row"><span>Allocation</span><strong>1:1</strong><small>Equal randomized assignment to module offer and existing discovery.</small></div>
            <div className="design-row"><span>Eligibility</span><strong>Before assignment</strong><small>All eligible households remain in their assigned arm, including nonparticipants.</small></div>
            <div className="design-row"><span>Observation</span><strong>Fixed 28-day window</strong><small>No repeated efficacy looks or early favorable stop.</small></div>
            <div className="design-row"><span>Missingness</span><strong>Unknown stays unknown</strong><small>Report outcome completeness by arm; assess sensitivity if capture differs.</small></div>
            <div className="design-row"><span>Spillovers</span><strong>Assume limited interference</strong><small>Shared accounts and cross-household exposure can invalidate the contrast.</small></div>
          </div>
          <div className="design-warning"><ShieldAlert size={17} /><div><strong>Randomization unavailable?</strong><span>Do not label an observational comparison an A/B test. Document another design and its assumptions, or record that this design cannot answer the question.</span></div></div>
        </section>

        <section id="sensitivity" className="page-section detail-section">
          <div className="section-heading"><div><span className="eyebrow">06 / SENSITIVITY PLANNER</span><h2>What could this sample reliably detect?</h2></div><span className="section-index">05—08</span></div>
          <div className="sensitivity-layout">
            <div className="planner-inputs">
              <div className="planner-intro"><span className="planner-icon"><Gauge size={17} /></span><div><strong>Planning assumptions</strong><span>Household-level, two-sided two-proportion approximation</span></div></div>
              <div className="input-grid">
                <label>Baseline household rate <div className="number-input"><input type="number" min="1" max="99" value={baseline} onChange={(event) => setBaseline(Number(event.target.value))} /><span>%</span></div></label>
                <label>Target effect <div className="number-input"><input type="number" min="0.1" max="40" step="0.1" value={target} onChange={(event) => setTarget(Number(event.target.value))} /><span>pp</span></div></label>
                <label>Available households <div className="number-input wide-input"><input type="number" min="4" max="1000000" step="500" value={sample} onChange={(event) => setSample(Number(event.target.value))} /><span>total</span></div></label>
              </div>
              <div className="assumption-pills"><span>1:1 allocation</span><span>α = 0.05</span><span>80% power</span><span>5% attrition</span></div>
              <button className="calculate-button" onClick={runSensitivity} disabled={loadingSensitivity}>{loadingSensitivity ? 'Calculating…' : 'Recalculate sensitivity'} <ChevronRight size={15} /></button>
              {sensitivityError && <p className="inline-error">{sensitivityError}</p>}
            </div>
            <div className="sensitivity-result">
              <span className="result-kicker">REQUIRED TO DETECT {target.toFixed(1)} PP</span>
              <div className="required-number">{sensitivity ? sensitivity.required_total.toLocaleString() : '—'} <span>households</span></div>
              <div className="arm-split"><span><i className="split-control" /> Control <strong>{sensitivity?.required_control.toLocaleString() ?? '—'}</strong></span><span><i className="split-treatment" /> Treatment <strong>{sensitivity?.required_treatment.toLocaleString() ?? '—'}</strong></span></div>
              <div className="effective-split">Effective after attrition <strong>{sensitivity?.effective_control.toLocaleString() ?? '—'} control</strong><span>·</span><strong>{sensitivity?.effective_treatment.toLocaleString() ?? '—'} treatment</strong></div>
              <div className={`detectability ${sensitivity && sample < sensitivity.required_total ? 'underpowered' : ''}`}>
                <div><span className="detectability-label">WITH {sample.toLocaleString()} AVAILABLE</span><strong>{sensitivity ? sensitivity.detectable_effect_achievable ? `${(sensitivity.detectable_effect * 100).toFixed(2)} pp` : 'Not attainable' : '—'}</strong></div>
                <span className="detectability-copy">{sensitivity?.detectable_effect_achievable ? 'Smallest positive effect this sample can detect with 80% power' : 'No possible positive rate increase reaches 80% power at this sample size'}</span>
              </div>
              {sensitivity && (!sensitivity.detectable_effect_achievable || sample < sensitivity.required_total) && <div className="shortfall"><ShieldAlert size={15} /> Available sample cannot reliably detect the +{target.toFixed(1)} pp threshold.</div>}
              <div className="algorithm-note">Algorithm <code>{sensitivity?.algorithm_version ?? 'loading'}</code></div>
            </div>
          </div>
          <p className="planner-footnote">Illustrative inputs only. Normal approximation; household is the independent unit. Does not account for clustering above household, covariate adjustment, or multiple primary outcomes. Verified against an independent reference and seeded null simulation.</p>
        </section>

        <section id="scenarios" className="page-section detail-section scenario-section">
          <div className="section-heading"><div><span className="eyebrow">07 / SCENARIO SIMULATOR</span><h2>Same frozen plan. Different possible evidence.</h2></div><span className="section-index">06—08</span></div>
          <div className="scenario-layout">
            <div className="scenario-list" role="group" aria-label="Fixed synthetic scenario">
              {scenarios.map((item, index) => (
                <button key={item.id} className={`scenario-option ${scenarioId === item.id ? 'selected' : ''}`} onClick={() => setScenarioId(item.id)}>
                  <span className="scenario-number">0{index + 1}</span><span className="scenario-option-copy"><strong>{item.label}</strong><small>{item.note}</small></span><span className="scenario-radio" />
                </button>
              ))}
              <div className="scenario-manifest"><span className="manifest-status"><Check size={12} /> FIXED SCENARIO</span><span>Seed {scenario?.seed ?? '—'} · {scenario?.dataset_manifest.households_per_arm.toLocaleString() ?? '—'} households / arm</span><code>{scenario?.dataset_manifest.sha256.slice(0, 20) ?? '—'}…</code></div>
            </div>
            <div className="scenario-output">
              <div className="scenario-output-head"><div><span className="field-label">SELECTED EVALUATION DATASET</span><h3>{scenario?.label ?? 'Loading scenario'}</h3></div><span className="scenario-freeze"><Check size={12} /> PLAN V1 FROZEN</span></div>
              <p>{scenario?.description ?? 'Generating fixed, seeded household observations.'}</p>
              <div className="scenario-evidence-row"><div><span>Control rate</span><strong>{pct(analysis?.arms.control.outcome_rate)}</strong><small>{analysis?.arms.control.qualified_sessions ?? '—'} / {analysis?.arms.control.observed ?? '—'} observed</small></div><div><span>Treatment rate</span><strong>{pct(analysis?.arms.treatment.outcome_rate)}</strong><small>{analysis?.arms.treatment.qualified_sessions ?? '—'} / {analysis?.arms.treatment.observed ?? '—'} observed</small></div><div className={isPositive ? 'positive-cell' : 'negative-cell'}><span>ITT difference</span><strong>{points(primary?.estimate)}</strong><small>95% {points(primary?.interval_low)} to {points(primary?.interval_high)}</small></div></div>
              <div className="diagnostic-row"><div><span>Outcome completeness</span><strong>Control {pct(analysis ? 1 - analysis.arms.control.missing / analysis.arms.control.assigned : null)} <i /> Treatment {pct(analysis ? 1 - analysis.arms.treatment.missing / analysis.arms.treatment.assigned : null)}</strong></div><div><span>Treatment exposure</span><strong>{pct(analysis?.diagnostics.exposure_rate_treatment)}</strong></div><div><span>Module interaction</span><strong>{pct(analysis?.diagnostics.module_interaction_rate_treatment)}</strong></div></div>
              <div className="scenario-warning-list">{analysis?.warnings.map((warning) => <div key={warning}><ShieldAlert size={14} />{warning}</div>)}</div>
              <div className="scenario-provenance"><span>Generator {scenario?.generator_version ?? '—'}</span><span>Analysis {scenario?.analysis_version ?? '—'}</span><span>Plan ref {scenario?.plan_reference.plan_id ?? '—'}</span><span>SHA-256 {scenario?.dataset_manifest.sha256.slice(0, 12) ?? '—'}</span></div>
            </div>
          </div>
          <div className="simulator-note"><FlaskConical size={16} /><span>These bounded scenarios are synthetic teaching examples, not evidence about real users or outcomes. Re-running a scenario with the same plan, generator, and seed reproduces the same data and analysis.</span></div>
        </section>

        <section id="memo" className="page-section detail-section memo-section">
          <div className="section-heading"><div><span className="eyebrow">08 / DECISION MEMO</span><h2>Evidence informs the call. It does not make it.</h2></div><span className="section-index">07—08</span></div>
          <div className="memo-header"><div><span className="memo-doc-icon"><BookOpenCheck size={18} /></span><div><strong>Executive decision memo</strong><span>Evidence summary · {scenario?.label ?? 'Selected scenario'} · Plan v1</span></div></div><span className="memo-state">DRAFT TEMPLATE</span></div>
          <div className="memo-grid">
            <div className="memo-main">
              <div className="memo-item"><span className="field-label">QUESTION & DESIGN</span><p>Among households eligible before assignment, what is the effect of offering the module, versus existing discovery, on at least one qualified game session in 28 days? Household randomization; intention-to-treat.</p></div>
              <div className="memo-item"><span className="field-label">EVIDENCE</span><p>Primary difference: <strong>{points(primary?.estimate)}</strong> (95% interval {points(primary?.interval_low)} to {points(primary?.interval_high)}; p = {primary?.p_value.toFixed(3) ?? '—'}). Practical threshold: +1.00 pp. Playback-quality difference: <strong>{points(analysis?.guardrails.playback_quality.difference)}</strong> (household-clustered interval; control {analysis?.guardrails.playback_quality.control_failures ?? '—'}/{analysis?.guardrails.playback_quality.control_eligible_playback_sessions ?? '—'} failures/sessions, treatment {analysis?.guardrails.playback_quality.treatment_failures ?? '—'}/{analysis?.guardrails.playback_quality.treatment_eligible_playback_sessions ?? '—'}); stability: <strong>{points(analysis?.guardrails.stability.difference)}</strong>.</p></div>
              <div className="memo-item"><span className="field-label">MISSINGNESS SENSITIVITY</span><p>Extreme missing-outcome bounds for the primary difference: <strong>{points(analysis?.diagnostics.missing_outcome_sensitivity.lower)} to {points(analysis?.diagnostics.missing_outcome_sensitivity.upper)}</strong>. They assign unknown outcomes in opposite directions between arms and are not an imputation model.</p></div>
              <div className="memo-item"><span className="field-label">INTERPRETATION LIMIT</span><p>Effect of offering the module on a fictional qualified-session outcome only. This does not establish satisfaction, retention, financial value, or creative quality. Unknown outcomes remain distinct from zero.</p></div>
              <div className="memo-item"><span className="field-label">RECOMMENDATION</span><div className="recommendation-options"><span>Continue</span><span>Redesign</span><span>More evidence</span><span>Stop</span><span>Inconclusive</span><span className="cannot-answer">Cannot answer</span></div><small>Recommendation remains stakeholder judgment; the demo does not make an automatic release decision.</small></div>
            </div>
            <aside className="memo-side"><span className="field-label">EVIDENCE REFERENCES</span><ul><li>Frozen plan v1</li><li>{scenario?.scenario ?? 'scenario'} · seed {scenario?.seed ?? '—'}</li><li>Dataset {scenario?.dataset_manifest.sha256.slice(0, 12) ?? '—'}</li><li>ITT analysis · {scenario?.analysis_version ?? '—'}</li></ul><div className="memo-side-line" /><span className="field-label">REVIEW STATUS</span><strong className="review-status"><span /> Not reviewed</strong><p>Public demo is read-only. Protected workflows require authorized API access; reviewed memos cannot be published by public users.</p></aside>
          </div>
        </section>

        <footer className="page-footer"><div className="footer-brand"><span className="brand-mark"><Target size={15} /></span> LaunchScope <span>·</span> Content & Games Measurement Design Lab</div><div>Fictional initiative · Synthetic data · Educational blueprint only</div></footer>
      </main>
      {loginOpen && (
        <div className="login-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setLoginOpen(false) }}>
          <section className="login-dialog" role="dialog" aria-modal="true" aria-labelledby="login-title">
            <div className="login-heading"><span className="stamp-icon"><LockKeyhole size={17} /></span><div><h2 id="login-title">Analyst sign in</h2><p>Use your configured analyst or reviewer account.</p></div></div>
            <form className="workspace-form" onSubmit={submitLogin}>
              <label>Username<input autoComplete="username" value={loginUsername} onChange={(event) => setLoginUsername(event.target.value)} required /></label>
              <label>Password<input type="password" autoComplete="current-password" value={loginPassword} onChange={(event) => setLoginPassword(event.target.value)} required /></label>
              {authError && <p className="inline-error" role="alert">{authError}</p>}
              <div className="login-actions"><button className="calculate-button" type="submit"><LogIn size={14} /> Sign in</button><button className="text-action" type="button" onClick={() => setLoginOpen(false)}>Cancel</button></div>
            </form>
          </section>
        </div>
      )}
    </div>
  )
}

export default App