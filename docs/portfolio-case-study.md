# LaunchScope: Portfolio Case Study

**Live demo:** [LaunchScope Measurement Design Lab](https://frontend-production-2b4c.up.railway.app/)  
**Source:** [jems0906/LaunchScope](https://github.com/jems0906/LaunchScope)

## The Problem

“Did this initiative succeed?” is not yet a measurable question. LaunchScope guides an analyst from that ambiguity to a decision, a defined estimand, a study design, an evidence plan, and a human-reviewed memo.

The example is intentionally narrow: offering a fictional game-discovery module to eligible households. The data and event definitions are synthetic and do not represent Netflix methodology, internal systems, or actual outcomes.

## The Measurement Approach

- **Decision:** Continue, redesign, gather more evidence, stop, or record that the design cannot answer the question.
- **Primary estimand:** Household intention-to-treat difference in the probability of at least one qualified game session during a fixed 28-day window.
- **Assignment:** Eligible households are randomized 1:1 before exposure; non-clickers remain in their assigned arm.
- **Diagnostics:** Exposure, interaction, repeat engagement, and outcome completeness retain explicit denominators.
- **Guardrails:** Playback-quality failures per eligible playback session and stability events per assigned household, with prespecified harm margins.
- **Planning:** Analysts enter baseline, target effect, allocation, alpha, power, and attrition assumptions; the UI shows required enrollment and the effect the available sample can detect.
- **Scenarios:** Seeded helpful, null, harmful, and tradeoff datasets make uncertainty and guardrail conflicts visible without creating a universal success score.

New plan versions can prespecify one baseline subgroup, prior qualified game engagement. The analysis reports subgroup ITT estimates and an additive risk-difference interaction interval. This interaction is exploratory and is not multiplicity-adjusted; it does not replace the primary criterion. The original frozen V1 plan has no subgroup claim.

## The Application

Analysts capture decision intake, version and freeze a plan, run sensitivity calculations, generate a fixed synthetic scenario, and draft an evidence-linked memo. Reviewers independently inspect the evidence and record sign-off. Frozen criteria cannot be edited retroactively; new assumptions require a new version.

The public Railway deployment serves the read-only demo. The API and PostgreSQL stay private, and write credentials are not configured in the public environment.

## Implementation and Verification

FastAPI, SQLAlchemy, PostgreSQL, and Alembic provide the API and persisted workflow. The shared `measurement_core` package owns planning, seeded household generation, analysis, and provenance. React, Vite, and Plotly provide the interface; Docker Compose supports local development; GitHub Actions runs backend tests, migrations, frontend builds, container builds, and Playwright journeys.

The current validation run covers 37 backend tests, including independent planning references, seeded reproducibility, known effects, missingness, household-clustered guardrails, and null calibration for subgroup interactions. Three browser journeys cover public read-only access, analyst plan creation/resume, and reviewer inspection/sign-off. See the [runtime validation report](../runtime-validation-report.md) for deployment checks and residual limitations.

## Boundaries

- All results and event definitions are fictional and synthetic.
- The 28-day behavioral effect does not establish satisfaction, retention, financial value, or creative quality.
- The subgroup interaction is exploratory; no general-purpose subgroup discovery or automatic release decision is provided.
- This is a single shared workspace, not a multi-tenant production service.