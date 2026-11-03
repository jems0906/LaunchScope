# Measurement Tree

**Business question:** Did offering the fictional game-discovery module change qualified game-session behavior among eligible households?

```text
Offer module to eligible household
└── Primary: household had >=1 qualified game session in days 1-28
    ├── Diagnostic: module exposure / assigned households
    ├── Diagnostic: module interaction / assigned households
    ├── Diagnostic: repeat engagement / observed households
    ├── Diagnostic: observed primary outcomes / assigned households
    ├── Guardrail: playback-quality failure / eligible playback sessions
    └── Guardrail: stability event / assigned households
```

| Measure | Role | Definition and denominator |
| --- | --- | --- |
| Qualified game session | Primary outcome | Household indicator for at least one documented qualifying session in the fixed 28-day window, divided by assigned households with observed outcomes; unknown outcomes remain missing, not zero |
| Exposure | Diagnostic | Assigned households with a recorded module exposure divided by all assigned households |
| Module interaction | Diagnostic | Assigned households with at least one documented module interaction divided by all assigned households; post-assignment behavior is not an analysis eligibility rule |
| Repeat engagement | Diagnostic | Observed households with at least two qualified sessions divided by households with observed outcomes |
| Outcome completeness | Diagnostic | Households with observed outcome divided by all assigned households, reported by arm |
| Playback-quality failure | Guardrail | Count of prespecified playback failure events divided by all eligible playback sessions; zero-play households are retained in the assignment population and contribute zero eligible sessions |
| Stability event | Guardrail | Households with a prespecified stability event divided by all assigned households |

The session and playback-failure event rules are fictional and must be fixed before analysis; neither is a Netflix definition. The primary estimand is the intention-to-treat difference in household outcome rates, treatment minus control. Playback-quality uncertainty is clustered at household to preserve dependence among sessions from the same household.