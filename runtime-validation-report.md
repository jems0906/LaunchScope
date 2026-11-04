# Runtime Validation Report

**Generated:** 2026-11-04
**Target:** `D:\LaunchScope`
**Release commit:** `c01fd6f`

## Summary

| Tier | Status | Evidence |
| --- | --- | --- |
| Backend integration | PASS | `python -m pytest -q` from `backend`: 37 passed, including Monte Carlo null calibration for subgroup interaction. |
| Frontend build | PASS | `npm run build` from `frontend`; TypeScript and Vite production build succeeded. Vite retains its existing Plotly chunk-size warning (about 378 kB gzip). |
| Browser E2E | PASS | Playwright Chromium: 3 passed; analyst prespecifies and resumes a subgroup plan, reviewer sees interaction evidence, and public writes/workspace remain protected. |
| Container build | PASS | API and Nginx frontend images built locally and in hosted CI. |
| Migration | PASS | Hosted PostgreSQL migration step completed through Alembic `head`. |
| Railway startup | PASS | Both services report `SUCCESS`; frontend and `/api/health` return 200. Scenario endpoint returns config v4 / analysis v3. Anonymous `/api/workspace` returns the expected 503 while auth accounts are unset. |
| Hosted GitHub Actions | PASS | [Run 41922645538](https://github.com/jems0906/LaunchScope/actions/runs/41922645538) on `c01fd6f`; backend, frontend, containers, and browser-e2e jobs succeeded. |

**Overall:** PASS

## Scientific Validation

- The subgroup scenario is generated as a binary pre-assignment household attribute: prior qualified game engagement.
- Subgroup effects use assigned-household ITT denominators and report assignment counts, observed counts, missing outcomes, rates, and intervals.
- Heterogeneity is assessed with the additive risk-difference interaction and its Wald interval/p-value; separate subgroup p-values are not treated as evidence of a difference.
- A seeded 250-trial null simulation bounds interaction type-I error and 95% interval coverage with Wilson uncertainty intervals.
- Subgroup selection is stored in the frozen plan version. Existing V1 remains unchanged and has no confirmatory subgroup claim.
- The subgroup interaction is exploratory and not multiplicity-adjusted with the primary test; it does not replace the primary decision criterion.

## Deployment Validation

- Railway service region: US West; frontend is the only service with a public domain. API and PostgreSQL have no public domains.
- The Nginx entrypoint waits for the private API before starting. Nginx resolves the upstream using the container's runtime DNS resolver with a 10-second cache.
- A local isolated Docker test moved the `api` alias from `172.30.254.10` to `172.30.254.20`; without restarting Nginx, the proxy switched from the old API response to the replacement API response after DNS refresh.
- Railway health checks use `/api/health` on both services. The public domain returned 200, the proxied health endpoint returned `{"status":"ok","service":"launchscope-api"}`, and the synthetic tradeoff endpoint returned scenario config `game-discovery-scenarios-v4` and analysis `itt-newcombe-household-clustered-subgroups-v3`.
- The public demo is read-only: analyst/reviewer credentials are unset, and anonymous workspace access remains blocked.
- A workspace-wide $60 soft usage alert is configured; no hard limit is set. This alert applies to all workspace projects, not only LaunchScope.

## Browser Journeys

- Public visitor sees the synthetic scenario and cannot read workspace data or create initiatives.
- Analyst creates and freezes a plan with the prior-engagement subgroup prespecified, calculates sensitivity, generates a scenario, drafts a memo, reloads, and resumes the frozen version with its subgroup selection intact.
- Reviewer inspects the linked primary and playback results, sees the subgroup ITT effects and interaction interval, and marks the memo reviewed.

## Known Scope

- Only one optional baseline subgroup is supported: prior qualified game engagement. This is intentionally bounded, not a general subgroup-discovery platform.
- The interaction is exploratory and unadjusted against the primary test; do not make confirmatory subgroup claims from it.
- The project remains a single shared workspace, not a multi-tenant service. The public deployment has no analyst/reviewer accounts configured.
- Results are synthetic and do not establish satisfaction, retention, financial value, or creative quality.
