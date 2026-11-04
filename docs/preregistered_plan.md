# Preregistered Plan

## Version 1: Game discovery offer

- **Question:** Among households eligible before assignment, what is the effect of being offered the module on the probability of at least one qualified game session within 28 days?
- **Estimand:** Household-level intention-to-treat difference in proportions (treatment minus control).
- **Primary outcome:** Binary indicator of one or more documented qualified sessions in days 1 through 28. Fix the fictional session definition and event-quality rules before inspecting outcomes.
- **Assignment:** Household, 1:1 allocation, randomized before exposure. Analyze households as assigned, including non-clickers and non-launchers.
- **Diagnostics:** Exposure, module interaction, repeat engagement, and outcome completeness, each reported with explicit denominators.
- **Guardrails:** Playback-quality failures per eligible playback session and stability events per assigned household. Playback-quality uncertainty is clustered at household. Prespecified harm margin: +0.5 percentage points for each measure; nonsignificance is not evidence that harm is absent.
- **Error control:** One primary outcome, two-sided alpha 0.05, no interim efficacy looks. Guardrail intervals are reported as safety evidence, not as proof of no harm.
- **Practical threshold:** +1 percentage point on the primary rate, a stakeholder judgment threshold rather than a universal success score.
- **Missingness:** Unknown is not zero. Report completeness by arm. Flag a completeness difference of at least 1 percentage point and provide sensitivity analysis before using the result for a decision.
- **Spillovers:** Assume no material interference across households. Shared accounts, household cross-contamination, or external campaigns can violate this assumption and must be investigated.
- **Subgroups:** Version 1 makes no confirmatory subgroup claim. A new frozen plan version may prespecify no subgroup or one exploratory baseline question: prior qualified game engagement before assignment. Report the two subgroup ITT effects and intervals plus the additive risk-difference interaction interval and p-value. This interaction is not multiplicity-adjusted with the primary test and does not replace the primary decision criterion. Interpret the interaction directly; do not infer heterogeneity because one subgroup is significant and another is not. Do not select subgroups using post-assignment behavior.
- **Repeated looks:** Fixed 28-day horizon. Do not repeatedly monitor an ordinary fixed-sample test to stop early for a favorable result.
- **Interpretation:** Causal interpretation depends on valid household randomization, adherence to assignment, stable outcome capture, and limited interference. This estimates the effect of offering the module, not gaming value, satisfaction, retention, financial value, or creative quality.

If randomization is unavailable, this is not an A/B test. A separately documented observational design, assumptions, and sensitivity analysis are required. If the population, outcome, or assumptions cannot answer the stakeholder's question, record “this design cannot answer the question” and redesign or decline the study.