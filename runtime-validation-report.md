# Runtime Validation Report

**Generated:** 2026-11-03
**Target:** `D:\LaunchScope`

## Summary

| Tier | Status | Exit Code | Evidence |
| --- | --- | ---: | --- |
| Startup | PASS | 0 | `docker compose up -d --force-recreate`; API health returned 200; Compose services remained up |
| Migration | PASS | 0 | PostgreSQL reports `0002_seed_demo_plan`; canonical demo plan remains frozen |
| Backend integration | PASS | 0 | `python -m pytest -q` from `backend`: 29 passed |
| Frontend build | PASS | 0 | `npm run build` from `frontend`: TypeScript and Vite production build succeeded |
| Browser E2E | PASS | 0 | `npx playwright test` from `frontend`: 3 passed in 5.8 seconds |
| Container build | PASS | 0 | `docker compose build` built API and frontend images |

**Overall:** PASS

## Environment

- Docker daemon: available
- Node.js: v22.14.0
- Playwright: installed; Chromium browser available
- Infrastructure tier: Docker Compose with PostgreSQL 16, FastAPI, and Nginx-served React SPA
- Browser tier: Playwright Chromium

## Browser Journeys

- Public visitor receives unauthenticated session state, can view the synthetic scenario/chart, and cannot read the workspace or create initiatives.
- Analyst signs in, records decision intake, creates and freezes plan v1, records sensitivity and a tradeoff evaluation, drafts a memo, reloads, and resumes the saved plan.
- Reviewer signs in separately, opens a queued memo, inspects its linked primary and playback estimates, and marks it reviewed; the pending queue updates.

## Test Data and Cleanup

Browser tests use unique initiative titles and disposable CI credentials. The local E2E test initiatives, plans, runs, analyses, and memos were removed after validation. The seeded public demo initiative and frozen plan remain. Temporary local credentials were cleared and the running stack was restored to read-only mode.

## Known Gaps

The GitHub Actions browser job is configured but has not yet run on GitHub-hosted CI; the same Playwright suite passed locally against Docker Compose. This is a single shared workspace, not a multi-tenant system. The Vite build reports the separately loaded Plotly bundle as larger than 500 kB (about 378 kB gzip).
