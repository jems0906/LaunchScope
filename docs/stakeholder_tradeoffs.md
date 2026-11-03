# Stakeholder Tradeoffs

The Content & Games Product Lead may value discovery and repeat use, while playback reliability and household experience constrain the decision. Those interests are not collapsed into a weighted score.

| Evidence pattern | Discussion prompt |
| --- | --- |
| Primary estimate is practically meaningful and guardrails appear acceptable | Is the uncertainty narrow enough, and are operating constraints satisfied? |
| Primary estimate is positive but below the practical threshold | Is the observed change worth the implementation and opportunity cost? |
| Primary estimate is imprecise | Is more sample or a narrower decision question feasible? |
| Primary estimate is favorable and a guardrail exceeds its harm margin | Does the harm require stopping or redesign regardless of primary movement? |
| Outcome completeness differs by arm | Could missing outcomes change the interpretation under plausible assumptions? |
| Randomization, stable capture, or low interference is not credible | This design cannot answer the causal question; choose and document a different design |

The analyst summarizes evidence and limitations. The accountable stakeholder records a recommendation and rationale. Statistical significance alone does not determine the action.

## Review permissions

Analyst and reviewer accounts are configured separately through environment-held salted scrypt hashes. Analysts can create new initiative/plan records, freeze their plan versions, record design and simulation runs, and draft memos. Reviewers can inspect a draft's rationale, limitations, and linked analysis before marking it reviewed; they cannot change plans or create evaluation records. Writes require the signed same-site session and its CSRF token. The public demo remains read-only when these accounts are not configured.

Authenticated users can reload the workspace snapshot and resume saved initiatives, plan versions, runs, and memos. This MVP is a single shared workspace: records are visible to configured analyst/reviewer roles and are not partitioned by account. Do not deploy it as a multi-tenant system without adding ownership/tenant scoping and corresponding authorization tests.