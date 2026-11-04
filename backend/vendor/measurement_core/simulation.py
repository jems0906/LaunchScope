"""Seeded synthetic household data generation and intention-to-treat analysis."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import numpy as np
from scipy.stats import norm, t
from statsmodels.stats.proportion import confint_proportions_2indep

GENERATOR_VERSION = "seeded-household-playback-sessions-v4"
ScenarioName = Literal["helpful", "null", "harmful", "tradeoff"]
SubgroupQuestion = Literal["none", "prior_game_engagement"]
_CONFIG_PATH = Path(
    os.environ.get(
        "LAUNCHSCOPE_SCENARIO_CONFIG",
        Path(__file__).parents[3] / "configs" / "scenarios" / "game_discovery.json",
    )
)
SCENARIO_CONFIG = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
SCENARIO_CONFIG_VERSION = str(SCENARIO_CONFIG["version"])
SCENARIOS: dict[ScenarioName, dict[str, float | str]] = {
    item["id"]: item for item in SCENARIO_CONFIG["scenarios"]
}
BASELINE_RATE = float(SCENARIO_CONFIG["baseline_rate"])
CONTROL_PLAYBACK_FAILURE_RATE = float(SCENARIO_CONFIG["control_playback_failure_rate"])
CONTROL_STABILITY_EVENT_RATE = float(SCENARIO_CONFIG["control_stability_event_rate"])
CONTROL_MISSINGNESS_RATE = float(SCENARIO_CONFIG["control_missingness_rate"])
TREATMENT_MISSINGNESS_RATE = float(SCENARIO_CONFIG["treatment_missingness_rate"])
PLAYBACK_HARM_MARGIN = float(SCENARIO_CONFIG["playback_harm_margin"])
STABILITY_HARM_MARGIN = float(SCENARIO_CONFIG["stability_harm_margin"])


@dataclass(frozen=True)
class ArmSummary:
    assigned: int
    observed: int
    missing: int
    qualified_sessions: int
    outcome_rate: float | None
    households_with_eligible_playback: int
    eligible_playback_sessions: int
    playback_failures: int
    playback_failure_rate: float | None
    stability_events: int
    stability_event_rate: float


def generate_scenario(
    scenario: ScenarioName, *, seed: int, households_per_arm: int = 2000
) -> list[dict[str, int | str | bool | None]]:
    """Generate bounded synthetic household-level results for a fixed scenario."""
    if scenario not in SCENARIOS:
        raise ValueError(f"Unsupported fixed scenario: {scenario}")
    if not 20 <= households_per_arm <= 10_000:
        raise ValueError("households_per_arm must be between 20 and 10000")
    rng = np.random.default_rng(seed)
    treatment_rate = float(SCENARIOS[scenario]["treatment_rate"])
    scenario_config = SCENARIOS[scenario]
    playback_rate = float(scenario_config["playback_failure_rate"])
    playback_sessions_mean = float(SCENARIO_CONFIG["eligible_playback_sessions_mean"])
    playback_risk_concentration = float(SCENARIO_CONFIG["playback_risk_concentration"])
    prior_engagement_rate = float(SCENARIO_CONFIG["prior_game_engagement_rate"])
    rows: list[dict[str, int | str | bool | None]] = []
    for arm, outcome_rate, quality_rate in (
        ("control", BASELINE_RATE, CONTROL_PLAYBACK_FAILURE_RATE),
        ("treatment", treatment_rate, playback_rate),
    ):
        outcomes = rng.binomial(1, outcome_rate, households_per_arm)
        prior_game_engagement = rng.binomial(1, prior_engagement_rate, households_per_arm)
        eligible_playback_sessions = rng.poisson(playback_sessions_mean, households_per_arm)
        household_failure_rates = rng.beta(
            quality_rate * playback_risk_concentration,
            (1 - quality_rate) * playback_risk_concentration,
            households_per_arm,
        )
        playback_failures = rng.binomial(eligible_playback_sessions, household_failure_rates)
        stability_rate = (
            CONTROL_STABILITY_EVENT_RATE
            if arm == "control"
            else float(scenario_config["stability_event_rate"])
        )
        stability = rng.binomial(1, stability_rate, households_per_arm)
        missing_rate = CONTROL_MISSINGNESS_RATE if arm == "control" else TREATMENT_MISSINGNESS_RATE
        missing = rng.binomial(1, missing_rate, households_per_arm)
        for index in range(households_per_arm):
            observed = not bool(missing[index])
            rows.append(
                {
                    "household_id": f"{arm}-{index:05d}",
                    "assignment": arm,
                    "observed": observed,
                    "qualified_session": int(outcomes[index]) if observed else None,
                    "prior_game_engagement": int(prior_game_engagement[index]),
                    "exposed": int(rng.random() < (0.80 if arm == "treatment" else 0.10)),
                    "module_interaction": int(rng.random() < (0.30 if arm == "treatment" else 0.03)),
                    "repeat_engagement": int(outcomes[index] and rng.random() < 0.35) if observed else None,
                    "eligible_playback_sessions": int(eligible_playback_sessions[index]),
                    "playback_failures": int(playback_failures[index]),
                    "stability_event": int(stability[index]),
                }
            )
    return rows


def _arm_summary(rows: list[dict[str, int | str | bool | None]]) -> ArmSummary:
    observed_rows = [row for row in rows if row["observed"]]
    assigned = len(rows)
    outcome_count = sum(int(row["qualified_session"] or 0) for row in observed_rows)
    return ArmSummary(
        assigned=assigned,
        observed=len(observed_rows),
        missing=assigned - len(observed_rows),
        qualified_sessions=outcome_count,
        outcome_rate=outcome_count / len(observed_rows) if observed_rows else None,
        households_with_eligible_playback=sum(
            int(row["eligible_playback_sessions"] > 0) for row in rows
        ),
        eligible_playback_sessions=sum(int(row["eligible_playback_sessions"]) for row in rows),
        playback_failures=sum(int(row["playback_failures"]) for row in rows),
        playback_failure_rate=(
            sum(int(row["playback_failures"]) for row in rows)
            / sum(int(row["eligible_playback_sessions"]) for row in rows)
            if sum(int(row["eligible_playback_sessions"]) for row in rows)
            else None
        ),
        stability_events=sum(int(row["stability_event"]) for row in rows),
        stability_event_rate=sum(int(row["stability_event"]) for row in rows) / assigned,
    )


def _rate_difference_interval(
    treatment: ArmSummary, control: ArmSummary, alpha: float
) -> tuple[float, float, float]:
    estimate = float(treatment.outcome_rate) - float(control.outcome_rate)
    low, high = confint_proportions_2indep(
        treatment.qualified_sessions,
        treatment.observed,
        control.qualified_sessions,
        control.observed,
        method="newcomb",
        alpha=alpha,
    )
    return estimate, float(low), float(high)


def _guardrail_difference(
    treatment_events: int,
    treatment_n: int,
    control_events: int,
    control_n: int,
    alpha: float,
) -> dict[str, float | bool]:
    difference = treatment_events / treatment_n - control_events / control_n
    low, high = confint_proportions_2indep(
        treatment_events,
        treatment_n,
        control_events,
        control_n,
        method="newcomb",
        alpha=alpha,
    )
    return {
        "difference": difference,
        "interval_low": float(low),
        "interval_high": float(high),
        "exceeds_harm_margin": difference > PLAYBACK_HARM_MARGIN,
        "interval_excludes_no_harm": float(low) > 0,
    }


def _clustered_playback_difference(
    treatment_rows: list[dict[str, int | str | bool | None]],
    control_rows: list[dict[str, int | str | bool | None]],
    alpha: float,
) -> dict[str, float | int | bool | str]:
    def arm_rate(
        rows: list[dict[str, int | str | bool | None]],
    ) -> tuple[float, float, int, int, int]:
        sessions = np.asarray([int(row["eligible_playback_sessions"]) for row in rows])
        failures = np.asarray([int(row["playback_failures"]) for row in rows])
        if np.any(sessions < 0) or np.any(failures < 0) or np.any(failures > sessions):
            raise ValueError("Playback failures must be counts within eligible playback sessions")
        denominator = int(sessions.sum())
        if denominator == 0:
            raise ValueError("Each arm must have eligible playback sessions")
        eligible_households = int(np.count_nonzero(sessions))
        if eligible_households < 2:
            raise ValueError("Each arm needs at least two households with eligible playback sessions")
        rate = float(failures.sum() / denominator)
        residuals = failures - rate * sessions
        variance = len(rows) / (len(rows) - 1) * float(residuals @ residuals) / denominator**2
        return rate, variance, int(failures.sum()), denominator, eligible_households

    treatment_rate, treatment_variance, treatment_failures, treatment_sessions, treatment_households = arm_rate(treatment_rows)
    control_rate, control_variance, control_failures, control_sessions, control_households = arm_rate(control_rows)
    estimate = treatment_rate - control_rate
    standard_error = float(np.sqrt(treatment_variance + control_variance))
    degrees_of_freedom = min(len(treatment_rows), len(control_rows)) - 1
    critical_value = float(t.ppf(1 - alpha / 2, degrees_of_freedom))
    interval_low = max(-1.0, estimate - critical_value * standard_error)
    interval_high = min(1.0, estimate + critical_value * standard_error)
    return {
        "difference": estimate,
        "interval_low": interval_low,
        "interval_high": interval_high,
        "interval_excludes_no_harm": interval_low > 0,
        "exceeds_harm_margin": estimate > PLAYBACK_HARM_MARGIN,
        "harm_margin": PLAYBACK_HARM_MARGIN,
        "control_failures": control_failures,
        "control_eligible_playback_sessions": control_sessions,
        "control_households_with_eligible_playback": control_households,
        "treatment_failures": treatment_failures,
        "treatment_eligible_playback_sessions": treatment_sessions,
        "treatment_households_with_eligible_playback": treatment_households,
        "uncertainty_method": "household-clustered sandwich with finite-sample correction",
    }


def _rate_variance_sqrt(treatment: ArmSummary, control: ArmSummary) -> float:
    treatment_rate = float(treatment.outcome_rate)
    control_rate = float(control.outcome_rate)
    return float(
        np.sqrt(
            treatment_rate * (1 - treatment_rate) / treatment.observed
            + control_rate * (1 - control_rate) / control.observed
        )
    )


def _subgroup_analysis(
    rows: list[dict[str, int | str | bool | None]], *, alpha: float
) -> dict[str, object]:
    if any(row.get("prior_game_engagement") not in (0, 1) for row in rows):
        raise ValueError("Prior game engagement subgroup requires a binary pre-assignment value per household")

    groups: dict[str, dict[str, object]] = {}
    group_effects: dict[str, tuple[float, float, float, int, int]] = {}
    for group_name, group_value in (
        ("no_prior_game_engagement", 0),
        ("prior_game_engagement", 1),
    ):
        group_rows = [row for row in rows if row["prior_game_engagement"] == group_value]
        control = _arm_summary([row for row in group_rows if row["assignment"] == "control"])
        treatment = _arm_summary([row for row in group_rows if row["assignment"] == "treatment"])
        if control.observed < 2 or treatment.observed < 2:
            return {
                "question": "prior_game_engagement",
                "label": "Prior qualified game engagement before assignment",
                "groups": groups,
                "interaction": None,
                "unavailable_reason": "Each subgroup needs at least two observed households in both assignment arms.",
                "warnings": ["Subgroup interaction was not estimable because at least one subgroup arm was too small."],
            }

        estimate, interval_low, interval_high = _rate_difference_interval(treatment, control, alpha)
        standard_error = _rate_variance_sqrt(treatment, control)
        p_value = float(2 * norm.sf(abs(estimate / standard_error))) if standard_error else 1.0
        group_effects[group_name] = (
            estimate,
            float(treatment.outcome_rate),
            float(control.outcome_rate),
            treatment.observed,
            control.observed,
        )
        groups[group_name] = {
            "control": {
                "assigned": control.assigned,
                "observed": control.observed,
                "missing": control.missing,
                "qualified_sessions": control.qualified_sessions,
                "outcome_rate": control.outcome_rate,
            },
            "treatment": {
                "assigned": treatment.assigned,
                "observed": treatment.observed,
                "missing": treatment.missing,
                "qualified_sessions": treatment.qualified_sessions,
                "outcome_rate": treatment.outcome_rate,
            },
            "effect": {
                "estimate": estimate,
                "interval_low": interval_low,
                "interval_high": interval_high,
                "p_value": p_value,
            },
        }

    no_prior_effect, no_prior_treatment_rate, no_prior_control_rate, no_prior_treatment_n, no_prior_control_n = group_effects[
        "no_prior_game_engagement"
    ]
    prior_effect, prior_treatment_rate, prior_control_rate, prior_treatment_n, prior_control_n = group_effects[
        "prior_game_engagement"
    ]
    interaction = prior_effect - no_prior_effect
    interaction_variance = sum(
        rate * (1 - rate) / count
        for rate, count in (
            (no_prior_treatment_rate, no_prior_treatment_n),
            (no_prior_control_rate, no_prior_control_n),
            (prior_treatment_rate, prior_treatment_n),
            (prior_control_rate, prior_control_n),
        )
    )
    interaction_standard_error = float(np.sqrt(interaction_variance))
    critical_value = float(norm.ppf(1 - alpha / 2))
    return {
        "question": "prior_game_engagement",
        "label": "Prior qualified game engagement before assignment",
        "groups": groups,
        "interaction": {
            "estimate": interaction,
            "interval_low": interaction - critical_value * interaction_standard_error,
            "interval_high": interaction + critical_value * interaction_standard_error,
            "p_value": float(2 * norm.sf(abs(interaction / interaction_standard_error)))
            if interaction_standard_error
            else 1.0,
            "contrast": "Prior-engagement treatment effect minus no-prior-engagement treatment effect",
            "uncertainty_method": "household-level additive risk-difference interaction with Wald interval",
        },
        "warnings": [
            "Use the interaction interval to assess heterogeneity; separate subgroup p-values do not establish a subgroup difference."
        ],
    }


def analyze_dataset(
    rows: list[dict[str, int | str | bool | None]],
    *,
    alpha: float = 0.05,
    subgroup_question: SubgroupQuestion = "none",
) -> dict[str, object]:
    """Analyze all assigned households; never condition ITT on post-assignment behavior."""
    if not 0 < alpha < 1:
        raise ValueError("alpha must be strictly between 0 and 1")
    if subgroup_question not in ("none", "prior_game_engagement"):
        raise ValueError(f"Unsupported prespecified subgroup question: {subgroup_question}")
    control_rows = [row for row in rows if row["assignment"] == "control"]
    treatment_rows = [row for row in rows if row["assignment"] == "treatment"]
    if not control_rows or not treatment_rows:
        raise ValueError("Both randomized assignment arms must be present")
    control = _arm_summary(control_rows)
    treatment = _arm_summary(treatment_rows)
    if not control.observed or not treatment.observed:
        raise ValueError("Each arm must have at least one observed outcome")
    estimate, interval_low, interval_high = _rate_difference_interval(treatment, control, alpha)
    se = _rate_variance_sqrt(treatment, control)
    p_value = float(2 * norm.sf(abs(estimate / se))) if se else 1.0
    playback = _clustered_playback_difference(treatment_rows, control_rows, alpha)
    stability = _guardrail_difference(
        treatment.stability_events,
        treatment.assigned,
        control.stability_events,
        control.assigned,
        alpha,
    )
    completeness_difference = treatment.missing / treatment.assigned - control.missing / control.assigned
    missingness_bounds = {
        "lower": treatment.qualified_sessions / treatment.assigned
        - (control.qualified_sessions + control.missing) / control.assigned,
        "upper": (treatment.qualified_sessions + treatment.missing) / treatment.assigned
        - control.qualified_sessions / control.assigned,
        "interpretation": "Extreme bounds for the ITT rate difference if all missing treatment outcomes are failures or successes and missing control outcomes take the opposite value.",
    }
    warnings = [
        "Nonsignificant guardrail results do not establish that harm is absent.",
        "This intention-to-treat estimate is the effect of offering the module, not the value of gaming or creative quality.",
    ]
    if abs(completeness_difference) >= 0.01:
        warnings.append("Outcome missingness differs by at least 1 percentage point between assignment arms; use sensitivity analysis.")
    if playback["exceeds_harm_margin"] or stability["exceeds_harm_margin"]:
        warnings.append("At least one guardrail point estimate exceeds its prespecified harm margin; do not let the primary result conceal it.")
    subgroup = _subgroup_analysis(rows, alpha=alpha) if subgroup_question == "prior_game_engagement" else None
    if subgroup and subgroup.get("warnings"):
        warnings.extend(subgroup["warnings"])
    return {
        "estimand": "Intention-to-treat difference in qualified-session household rates (treatment minus control).",
        "primary": {
            "estimate": estimate,
            "interval_low": interval_low,
            "interval_high": interval_high,
            "p_value": p_value,
            "practical_threshold": 0.01,
            "practically_positive": interval_low > 0.01,
        },
        "arms": {"control": asdict(control), "treatment": asdict(treatment)},
        "guardrails": {
            "playback_quality": playback,
            "stability": {**stability, "harm_margin": STABILITY_HARM_MARGIN},
        },
        "subgroup_analysis": subgroup,
        "diagnostics": {
            "completeness_difference_treatment_minus_control": completeness_difference,
            "missing_outcome_sensitivity": missingness_bounds,
            "exposure_rate_treatment": sum(int(row["exposed"]) for row in treatment_rows) / len(treatment_rows),
            "module_interaction_rate_treatment": sum(int(row["module_interaction"]) for row in treatment_rows) / len(treatment_rows),
            "repeat_engagement_rate_treatment_observed": sum(int(row["repeat_engagement"] or 0) for row in treatment_rows if row["observed"]) / treatment.observed,
        },
        "warnings": warnings,
        "analysis_version": "itt-newcombe-household-clustered-v2",
    }