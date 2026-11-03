"""Transparent two-arm binary-outcome planning calculations."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from scipy.optimize import brentq
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize

PLAN_ALGORITHM_VERSION = "two-proportion-normal-approximation-v1"


@dataclass(frozen=True)
class SensitivityPlan:
    baseline_rate: float
    target_effect: float
    allocation_treatment: float
    alpha: float
    power: float
    attrition: float
    required_control: int
    required_treatment: int
    required_total: int
    effective_control: int
    effective_treatment: int
    effective_total: int
    detectable_effect: float
    detectable_treatment_rate: float
    detectable_effect_achievable: bool
    algorithm_version: str = PLAN_ALGORITHM_VERSION

    def as_dict(self) -> dict[str, float | int | str]:
        return asdict(self)


def plan_sensitivity(
    *,
    baseline_rate: float,
    target_effect: float,
    allocation_treatment: float = 0.5,
    alpha: float = 0.05,
    power: float = 0.8,
    attrition: float = 0.0,
    available_households: int | None = None,
) -> SensitivityPlan:
    """Plan an unclustered household-randomized difference in proportions.

    Sample sizes are counts of households, and attrition inflates the enrolled
    counts. The detectable effect is the smallest positive rate increase at
    the supplied available sample size (or the required sample if omitted).
    """
    if not 0 < baseline_rate < 1:
        raise ValueError("baseline_rate must be strictly between 0 and 1")
    if not 0 < target_effect < 1 - baseline_rate:
        raise ValueError("target_effect must be positive and keep the rate below 1")
    if not 0 < allocation_treatment < 1:
        raise ValueError("allocation_treatment must be strictly between 0 and 1")
    if not 0 < alpha < 1 or not 0 < power < 1:
        raise ValueError("alpha and power must be strictly between 0 and 1")
    if not 0 <= attrition < 1:
        raise ValueError("attrition must be in [0, 1)")
    if available_households is not None and available_households < 4:
        raise ValueError("available_households must be at least 4")

    control_to_treatment_ratio = allocation_treatment / (1 - allocation_treatment)
    effect_size = abs(
        proportion_effectsize(baseline_rate + target_effect, baseline_rate)
    )
    power_model = NormalIndPower()
    control_enrolled = math.ceil(
        power_model.solve_power(
            effect_size=effect_size,
            power=power,
            alpha=alpha,
            ratio=control_to_treatment_ratio,
            alternative="two-sided",
        )
    )
    treatment_enrolled = math.ceil(control_enrolled * control_to_treatment_ratio)
    control_required = math.ceil(control_enrolled / (1 - attrition))
    treatment_required = math.ceil(treatment_enrolled / (1 - attrition))

    total_available = available_households or (control_required + treatment_required)
    treatment_enrolled_available = round(total_available * allocation_treatment)
    control_enrolled_available = total_available - treatment_enrolled_available
    treatment_available = max(2, math.floor(treatment_enrolled_available * (1 - attrition)))
    control_available = max(2, math.floor(control_enrolled_available * (1 - attrition)))
    effect_h = power_model.solve_power(
        nobs1=control_available,
        alpha=alpha,
        power=power,
        ratio=treatment_available / control_available,
        alternative="two-sided",
    )
    maximum_effect = proportion_effectsize(1 - 1e-8, baseline_rate)
    detectable_effect_achievable = bool(effect_h < maximum_effect)
    detectable_rate = (
        brentq(
            lambda candidate: proportion_effectsize(candidate, baseline_rate) - effect_h,
            baseline_rate + 1e-8,
            1 - 1e-8,
        )
        if detectable_effect_achievable
        else 1.0
    )
    return SensitivityPlan(
        baseline_rate=baseline_rate,
        target_effect=target_effect,
        allocation_treatment=allocation_treatment,
        alpha=alpha,
        power=power,
        attrition=attrition,
        required_control=control_required,
        required_treatment=treatment_required,
        required_total=control_required + treatment_required,
        effective_control=control_available,
        effective_treatment=treatment_available,
        effective_total=control_available + treatment_available,
        detectable_effect=detectable_rate - baseline_rate,
        detectable_treatment_rate=detectable_rate,
        detectable_effect_achievable=detectable_effect_achievable,
    )