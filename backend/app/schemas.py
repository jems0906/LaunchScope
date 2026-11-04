from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class InitiativeCreate(BaseModel):
    title: str = Field(min_length=4, max_length=160)
    business_question: str = Field(min_length=10, max_length=1000)
    proposed_decision: str = Field(min_length=5, max_length=500)
    alternatives: list[str] = Field(min_length=2, max_length=6)
    stakeholder_role: str = Field(min_length=3, max_length=160)
    eligible_population: str = Field(min_length=10, max_length=1000)
    timing: str = Field(min_length=5, max_length=500)
    wrong_decision_consequences: str = Field(min_length=10, max_length=2000)


class LoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class PlanSpecification(BaseModel):
    question: str = Field(min_length=10, max_length=1000)
    estimand: str = Field(min_length=10, max_length=500)
    population: str = Field(min_length=10, max_length=1000)
    eligibility_fixed_before_assignment: Literal[True] = True
    randomization_unit: Literal["household"] = "household"
    allocation_treatment: float = Field(default=0.5, gt=0, lt=1)
    observation_window_days: int = Field(default=28, ge=1, le=90)
    primary_outcome: str = Field(min_length=10, max_length=1000)
    practical_threshold: float = Field(default=0.01, gt=0, lt=0.5)
    subgroup_question: Literal["none", "prior_game_engagement"] = "none"
    diagnostics: list[str] = Field(min_length=2, max_length=8)
    guardrails: list[str] = Field(min_length=1, max_length=6)
    baseline_rate: float = Field(default=0.10, gt=0, lt=1)
    target_effect: float = Field(default=0.01, gt=0, lt=0.5)
    alpha: float = Field(default=0.05, gt=0, lt=1)
    desired_power: float = Field(default=0.80, gt=0, lt=1)
    attrition: float = Field(default=0.05, ge=0, lt=1)
    missingness_rule: str = Field(min_length=10, max_length=1000)
    spillover_assumption: str = Field(min_length=10, max_length=1000)
    fixed_horizon_no_early_stop: Literal[True] = True

    @model_validator(mode="after")
    def validate_target_rate(self) -> "PlanSpecification":
        if self.target_effect >= 1 - self.baseline_rate:
            raise ValueError("target_effect must keep the treatment rate below 1")
        return self


class DesignRunInput(BaseModel):
    available_households: int = Field(ge=4, le=1_000_000)
    seed: int = Field(ge=0, le=2_147_483_647)


class SimulationRunInput(BaseModel):
    scenario: Literal["helpful", "null", "harmful", "tradeoff"]
    seed: int = Field(ge=0, le=2_147_483_647)
    households_per_arm: int = Field(default=2500, ge=20, le=10_000)


class MemoCreate(BaseModel):
    analysis_result_id: str
    recommendation: Literal[
        "continue", "redesign", "collect_more_evidence", "stop", "inconclusive", "cannot_answer"
    ]
    rationale: str = Field(min_length=20, max_length=4000)
    limitations: list[str] = Field(min_length=1, max_length=20)
    evidence_references: list[str] = Field(min_length=1, max_length=20)


class FrozenPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    initiative_id: str
    version: int
    status: str