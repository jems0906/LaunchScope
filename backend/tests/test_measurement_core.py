from __future__ import annotations

import math

import numpy as np
from scipy.stats import norm
from statsmodels.stats.proportion import proportion_confint

from measurement_core import analyze_dataset, generate_scenario, plan_sensitivity


def _clustered_playback_trial_rows(
    rng: np.random.Generator,
    *,
    households_per_arm: int,
    control_rate: float,
    treatment_rate: float,
) -> list[dict[str, int | str | bool | None]]:
    rows = []
    for arm, average_rate in (("control", control_rate), ("treatment", treatment_rate)):
        eligible_sessions = rng.poisson(5, households_per_arm)
        household_rates = rng.beta(average_rate * 49, (1 - average_rate) * 49, households_per_arm)
        failures = rng.binomial(eligible_sessions, household_rates)
        outcomes = rng.binomial(1, 0.10, households_per_arm)
        for index in range(households_per_arm):
            rows.append(
                {
                    "household_id": f"{arm}-{index}",
                    "assignment": arm,
                    "observed": True,
                    "qualified_session": int(outcomes[index]),
                    "exposed": 0,
                    "module_interaction": 0,
                    "repeat_engagement": 0,
                    "eligible_playback_sessions": int(eligible_sessions[index]),
                    "playback_failures": int(failures[index]),
                    "stability_event": 0,
                }
            )
    return rows


def test_sample_size_matches_independent_normal_reference() -> None:
    baseline = 0.10
    target = 0.01
    alpha = 0.05
    desired_power = 0.80
    effect_h = 2 * math.asin(math.sqrt(baseline + target)) - 2 * math.asin(math.sqrt(baseline))
    expected_per_arm = 2 * (norm.ppf(1 - alpha / 2) + norm.ppf(desired_power)) ** 2 / effect_h**2

    plan = plan_sensitivity(
        baseline_rate=baseline,
        target_effect=target,
        alpha=alpha,
        power=desired_power,
        attrition=0,
    )

    assert abs(plan.required_control - expected_per_arm) / expected_per_arm < 0.02
    assert plan.required_control == plan.required_treatment
    assert plan.required_total == plan.required_control + plan.required_treatment


def test_planner_reports_sample_shortfall_as_larger_detectable_effect() -> None:
    underpowered = plan_sensitivity(
        baseline_rate=0.10,
        target_effect=0.01,
        available_households=500,
    )
    powered = plan_sensitivity(
        baseline_rate=0.10,
        target_effect=0.01,
        available_households=underpowered.required_total * 2,
    )

    assert underpowered.detectable_effect > 0.01
    assert powered.detectable_effect < underpowered.detectable_effect
    assert underpowered.detectable_effect_achievable is True


def test_attrition_reduces_effective_sample_for_detectable_effect() -> None:
    no_attrition = plan_sensitivity(
        baseline_rate=0.10,
        target_effect=0.01,
        available_households=10000,
        attrition=0,
    )
    with_attrition = plan_sensitivity(
        baseline_rate=0.10,
        target_effect=0.01,
        available_households=10000,
        attrition=0.10,
    )

    assert with_attrition.required_total > no_attrition.required_total
    assert with_attrition.detectable_effect > no_attrition.detectable_effect


def test_planner_reports_when_no_effect_can_reach_requested_power() -> None:
    plan = plan_sensitivity(
        baseline_rate=0.10,
        target_effect=0.01,
        available_households=4,
    )

    assert plan.detectable_effect_achievable is False
    assert plan.detectable_treatment_rate == 1.0


def test_scenario_generation_is_reproducible_and_has_fixed_bounds() -> None:
    first = generate_scenario("tradeoff", seed=1729, households_per_arm=200)
    second = generate_scenario("tradeoff", seed=1729, households_per_arm=200)

    assert first == second
    assert len(first) == 400
    assert {row["assignment"] for row in first} == {"control", "treatment"}


def test_itt_keeps_nonparticipants_in_assignment_denominator() -> None:
    rows = generate_scenario("helpful", seed=41, households_per_arm=300)
    result = analyze_dataset(rows)

    assert result["arms"]["treatment"]["assigned"] == 300
    assert result["diagnostics"]["module_interaction_rate_treatment"] < 1
    assert result["primary"]["interval_low"] < result["primary"]["estimate"]
    assert result["primary"]["estimate"] < result["primary"]["interval_high"]
    bounds = result["diagnostics"]["missing_outcome_sensitivity"]
    assert bounds["lower"] <= result["primary"]["estimate"] <= bounds["upper"]


def test_differential_missingness_is_warned_and_bounds_are_reported() -> None:
    rows = [
        {
            "assignment": arm,
            "observed": observed,
            "qualified_session": outcome,
            "exposed": 0,
            "module_interaction": 0,
            "repeat_engagement": outcome if observed else None,
            "eligible_playback_sessions": 10,
            "playback_failures": 0,
            "stability_event": 0,
        }
        for arm, count, missing_count in (("control", 100, 0), ("treatment", 100, 15))
        for index in range(count)
        for observed, outcome in [
            (index >= missing_count, int(index < 10) if index >= missing_count else None)
        ]
    ]

    result = analyze_dataset(rows)

    assert abs(result["diagnostics"]["completeness_difference_treatment_minus_control"]) >= 0.01
    assert any("missingness differs" in warning for warning in result["warnings"])
    assert result["diagnostics"]["missing_outcome_sensitivity"]["lower"] < result["diagnostics"]["missing_outcome_sensitivity"]["upper"]


def test_known_helpful_and_harmful_effects_keep_the_configured_direction() -> None:
    helpful = analyze_dataset(generate_scenario("helpful", seed=1729, households_per_arm=5000))
    harmful = analyze_dataset(generate_scenario("harmful", seed=1729, households_per_arm=5000))

    assert helpful["primary"]["estimate"] > 0
    assert harmful["primary"]["estimate"] < 0


def test_tradeoff_guardrail_warning_survives_a_favorable_primary_signal() -> None:
    result = analyze_dataset(generate_scenario("tradeoff", seed=2027, households_per_arm=5000))

    assert result["primary"]["estimate"] > 0
    assert result["guardrails"]["playback_quality"]["difference"] > 0.005
    assert any("guardrail point estimate" in warning for warning in result["warnings"])


def test_playback_quality_uses_eligible_sessions_and_keeps_zero_play_households() -> None:
    rows = []
    for arm, failures in (("control", [0, 0, 1, 1]), ("treatment", [0, 1, 2, 2])):
        for index, event_count in enumerate(failures):
            eligible_sessions = 0 if index == 0 else 10
            rows.append(
                {
                    "household_id": f"{arm}-{index}",
                    "assignment": arm,
                    "observed": True,
                    "qualified_session": int(index == 1),
                    "exposed": 0,
                    "module_interaction": 0,
                    "repeat_engagement": 0,
                    "eligible_playback_sessions": eligible_sessions,
                    "playback_failures": event_count,
                    "stability_event": 0,
                }
            )

    result = analyze_dataset(rows)
    control = result["arms"]["control"]
    playback = result["guardrails"]["playback_quality"]

    assert control["assigned"] == 4
    assert control["households_with_eligible_playback"] == 3
    assert control["eligible_playback_sessions"] == 30
    assert control["playback_failures"] == 2
    assert control["playback_failure_rate"] == 2 / 30
    assert playback["difference"] == (5 / 30) - (2 / 30)
    assert playback["control_eligible_playback_sessions"] == 30
    assert playback["treatment_eligible_playback_sessions"] == 30


def test_playback_interval_preserves_perfect_within_household_dependence() -> None:
    rows = []
    for arm in ("control", "treatment"):
        for index in range(80):
            failures = 50 if index % 2 == 0 else 0
            rows.append(
                {
                    "household_id": f"{arm}-{index}",
                    "assignment": arm,
                    "observed": True,
                    "qualified_session": int(index % 2 == 0),
                    "exposed": 0,
                    "module_interaction": 0,
                    "repeat_engagement": 0,
                    "eligible_playback_sessions": 50,
                    "playback_failures": failures,
                    "stability_event": 0,
                }
            )

    interval = analyze_dataset(rows)["guardrails"]["playback_quality"]

    assert interval["difference"] == 0
    assert interval["interval_high"] - interval["interval_low"] > 0.15
    assert interval["interval_low"] < 0 < interval["interval_high"]


def test_clustered_playback_null_frequency_and_interval_coverage() -> None:
    rng = np.random.default_rng(20261105)
    trial_count = 400
    false_positives = 0
    covered = 0

    for _ in range(trial_count):
        rows = _clustered_playback_trial_rows(
            rng,
            households_per_arm=250,
            control_rate=0.03,
            treatment_rate=0.03,
        )
        interval = analyze_dataset(rows)["guardrails"]["playback_quality"]
        false_positives += interval["interval_low"] > 0 or interval["interval_high"] < 0
        covered += interval["interval_low"] <= 0 <= interval["interval_high"]

    false_positive_bounds = proportion_confint(false_positives, trial_count, method="wilson")
    coverage_bounds = proportion_confint(covered, trial_count, method="wilson")

    assert false_positive_bounds[0] <= 0.05 <= false_positive_bounds[1]
    assert false_positive_bounds[1] < 0.10
    assert coverage_bounds[0] <= 0.95 <= coverage_bounds[1]
    assert coverage_bounds[0] > 0.90


def test_clustered_playback_interval_detects_known_harm() -> None:
    rows = _clustered_playback_trial_rows(
        np.random.default_rng(7351),
        households_per_arm=600,
        control_rate=0.03,
        treatment_rate=0.045,
    )

    interval = analyze_dataset(rows)["guardrails"]["playback_quality"]

    assert interval["difference"] > interval["harm_margin"]
    assert interval["interval_low"] > 0


def test_null_monte_carlo_false_positive_frequency_is_bounded() -> None:
    rng = np.random.default_rng(20261103)
    trial_count = 300
    household_count = 500
    false_positives = 0

    for _ in range(trial_count):
        control_outcomes = rng.binomial(1, 0.10, household_count)
        treatment_outcomes = rng.binomial(1, 0.10, household_count)
        rows = [
            {
                "assignment": arm,
                "observed": True,
                "qualified_session": int(outcome),
                "exposed": 0,
                "module_interaction": 0,
                "repeat_engagement": 0,
                "eligible_playback_sessions": 10,
                "playback_failures": 0,
                "stability_event": 0,
            }
            for arm, outcomes in (("control", control_outcomes), ("treatment", treatment_outcomes))
            for outcome in outcomes
        ]
        false_positives += analyze_dataset(rows)["primary"]["p_value"] < 0.05

    assert false_positives / trial_count < 0.09


def test_null_monte_carlo_interval_coverage_is_bounded() -> None:
    rng = np.random.default_rng(20261104)
    trial_count = 300
    household_count = 500
    covered = 0

    for _ in range(trial_count):
        control_outcomes = rng.binomial(1, 0.10, household_count)
        treatment_outcomes = rng.binomial(1, 0.10, household_count)
        rows = [
            {
                "assignment": arm,
                "observed": True,
                "qualified_session": int(outcome),
                "exposed": 0,
                "module_interaction": 0,
                "repeat_engagement": 0,
                "eligible_playback_sessions": 10,
                "playback_failures": 0,
                "stability_event": 0,
            }
            for arm, outcomes in (("control", control_outcomes), ("treatment", treatment_outcomes))
            for outcome in outcomes
        ]
        interval = analyze_dataset(rows)["primary"]
        covered += interval["interval_low"] <= 0 <= interval["interval_high"]

    assert 0.90 <= covered / trial_count <= 0.99