# LaunchScope: Content & Games Measurement Design Lab

LaunchScope turns the fictional stakeholder question “Did this initiative succeed?” into a documented decision, estimand, measurement contract, study design, sensitivity assessment, fixed synthetic evaluation, and decision memo.

This is an educational portfolio blueprint using one fictional initiative: offering a game-discovery module to eligible households. It does not represent Netflix methodology, internal systems, or actual business outcomes. All scenario data are synthetic.

## Run locally

Docker Compose starts PostgreSQL, applies Alembic migrations before starting FastAPI, and serves the React application:

```bash
docker compose up --build
```

Open the application at [http://localhost:4173](http://localhost:4173). The API health check is at [http://localhost:4173/api/health](http://localhost:4173/api/health), with interactive API documentation at [http://localhost:4173/docs](http://localhost:4173/docs). The API and database remain on the internal Compose network.

For a public, read-only Railway deployment, follow [the Railway deployment guide](docs/railway-deployment.md). It keeps the API and PostgreSQL private and leaves analyst/reviewer credentials unset.

The public UI is read-only until local analyst/reviewer accounts are configured. After sign-in, analysts can capture intake, save and freeze versioned plans, run sensitivity and fixed synthetic evaluations, draft memos, and resume saved initiatives and plan versions after reload. Reviewers get a pending-memo queue and can inspect linked estimates before signing off. This single-project lab shares its persisted records across configured accounts; it is not a multi-tenant service. The API uses expiring signed HttpOnly cookies, distinct analyst and reviewer roles, and CSRF tokens for writes. No auth secret is bundled into the frontend. The demo accepts no arbitrary user code, uploaded datasets, or proprietary data.

Successful workflow writes append actor-attributed audit events for initiatives, plan versions and freezes, design runs, simulations, analyses, memo drafts, and reviewer sign-off. The authenticated workspace displays the latest activity. ORM guards and PostgreSQL triggers reject updates and deletes to audit events; they are intended for application-level traceability, not protection from database administrators.

For local analyst access, copy `.env.example` to `.env`. Generate a signing secret with `python -c "import secrets; print(secrets.token_urlsafe(48))"` and set `SESSION_SECRET`. From `backend`, run `python -m app.auth_admin --role analyst --username analyst`; the CLI prompts for a password without echoing it and prints `ANALYST_USERNAME` and a salted `ANALYST_PASSWORD_HASH` to add to `.env`. Repeat with `--role reviewer` for independent memo review. Then restart with `docker compose up --build`. Leave account values blank to preserve the public read-only mode. Sessions expire after eight hours; logout clears the browser cookie. For any TLS-terminated deployment, set `SESSION_COOKIE_SECURE=true`; the local Compose setup uses HTTP and defaults it to false.

For a split development setup, configure the same environment variables, run the API from `backend` with `PYTHONPATH=.;vendor` and `PORT=8000`, then run `npm ci` and `npm run dev` from `frontend`. Vite proxies `/api` requests to `http://localhost:8000`.

## Measurement contract

- **Treatment:** Availability of a fictional game-discovery module.
- **Control:** Existing fictional discovery experience.
- **Population:** Households meeting eligibility rules before assignment.
- **Assignment:** Household, randomized 1:1.
- **Primary outcome:** Proportion of assigned households with at least one qualified game session during a fixed 28-day window.
- **Estimand:** Intention-to-treat difference in household outcome rates, treatment minus control.
- **Diagnostics:** Exposure, module interaction, repeat engagement, and observation completeness, with explicit denominators.
- **Guardrails:** Playback-quality failure and stability events, each with a prespecified +0.5 percentage-point educational harm margin.
- **Practical threshold:** +1 percentage point on the primary outcome, kept separate from statistical evidence and stakeholder judgment.

The fictional qualified-session and playback-failure event definitions must be fixed before analysis; neither is a Netflix definition. Playback-quality rate is failures divided by eligible playback sessions, with uncertainty clustered at household. Zero-play households remain in the assignment population but contribute no eligible sessions. Nonsignificant guardrail evidence does not establish that harm is absent.

Do not condition the main analysis on clicking the module or launching a game. These are post-assignment behaviors. Unknown outcomes remain distinct from observed zero; the analysis reports completeness by arm and extreme missing-outcome bounds. Fixed-horizon tests are not repeatedly monitored for early favorable stopping.

## Scientific and decision boundaries

The shared [`measurement_core`](backend/vendor/measurement_core/__init__.py) contains planning, seeded household generation, analysis, and version identifiers. The sensitivity planner uses `statsmodels`' two-proportion normal approximation and reports both required enrollment and detectable effect for the entered available sample. Playback failures use a beta-binomial household-risk model, and the guardrail interval uses household-clustered uncertainty. Scenario configuration is bounded and versioned in [`game_discovery.json`](configs/scenarios/game_discovery.json); web requests cannot provide code or arbitrary scenario parameters.

Plan versions are immutable once frozen. Design runs inherit assumptions from the frozen plan. Evaluation data cannot be generated before freeze. Every stored simulation records its plan reference, scenario, seed, generator version, and SHA-256 dataset manifest; analyses and memos reference the frozen plan. Reviewer access is separate from write access.

New plan versions may prespecify one baseline subgroup question: prior qualified game engagement before assignment. When selected, the analysis reports each subgroup's ITT difference and interval, observed and assigned denominators, and the additive risk-difference interaction interval. The demo's original frozen version has no confirmatory subgroup analysis. Do not infer heterogeneity from separate subgroup significance tests.

If randomization is unavailable, do not call an observational comparison an A/B test. Document a different design and assumptions, or select “this design cannot answer the question.” The estimate concerns the effect of offering the module on the specified behavior; it does not establish satisfaction, retention, financial value, or creative quality. There is no universal success score and no automatic release decision.

## Project map

```text
backend/                 FastAPI, SQLAlchemy, Alembic, shared measurement_core, tests
frontend/                React, Vite, Plotly, public demo plus authenticated analyst/reviewer workflow
configs/scenarios/       Fixed, versioned fictional scenario configuration
docs/                    Decision brief, measurement tree, preregistration, sensitivity,
                         stakeholder tradeoffs, executive memo template
docker-compose.yml       PostgreSQL + API + frontend
.github/workflows/ci.yml Backend tests, PostgreSQL migrations, frontend build, container builds, browser E2E
```

## Verification

The required test gates are defined in CI; they are not claims of Netflix validation. They include an independent sample-size reference, seeded reproducibility, household-level ITT denominators, known helpful/harmful effects, null false-positive frequency and interval coverage with Monte Carlo uncertainty bounds for both the primary outcome and clustered playback guardrail, tradeoff guardrail visibility, missing-outcome sensitivity, protected writes, frozen-plan/memo lifecycle and audit attribution checks, and append-only enforcement.

Run the backend checks from `backend`:

```bash
$env:PYTHONPATH='.;vendor'
python -m pytest -q
```

Run the frontend production check from `frontend`:

```bash
npm ci
npm run build
```

Run browser E2E tests against a running Compose stack from `frontend`:

```bash
npm ci
npx playwright install chromium
$env:E2E_BASE_URL = "http://localhost:4173"
$env:E2E_ANALYST_USERNAME = "analyst"
$env:E2E_ANALYST_PASSWORD = "<configured analyst password>"
$env:E2E_REVIEWER_USERNAME = "reviewer"
$env:E2E_REVIEWER_PASSWORD = "<configured reviewer password>"
npm run test:e2e
```

The E2E suite covers public read-only restrictions, analyst create/freeze/evaluate/memo and reload/resume, reviewer queue inspection/approval, and visibility of the audit activity feed. CI uses disposable credentials and tears down its Compose volume after each run.