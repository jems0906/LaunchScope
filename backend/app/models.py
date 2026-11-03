from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base


def new_id() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Initiative(Base):
    __tablename__ = "initiatives"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    business_question: Mapped[str] = mapped_column(String(1000), nullable=False)
    proposed_decision: Mapped[str] = mapped_column(String(500), nullable=False)
    alternatives: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    stakeholder_role: Mapped[str] = mapped_column(String(160), nullable=False)
    eligible_population: Mapped[str] = mapped_column(String(1000), nullable=False)
    timing: Mapped[str] = mapped_column(String(500), nullable=False)
    wrong_decision_consequences: Mapped[str] = mapped_column(String(2000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class MeasurementPlan(Base):
    __tablename__ = "measurement_plans"
    __table_args__ = (UniqueConstraint("initiative_id", "version", name="uq_plan_initiative_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    initiative_id: Mapped[str] = mapped_column(ForeignKey("initiatives.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    specification: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DesignRun(Base):
    __tablename__ = "design_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    plan_id: Mapped[str] = mapped_column(ForeignKey("measurement_plans.id"), nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(100), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    inputs: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    results: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    plan_id: Mapped[str] = mapped_column(ForeignKey("measurement_plans.id"), nullable=False)
    scenario: Mapped[str] = mapped_column(String(32), nullable=False)
    generator_version: Mapped[str] = mapped_column(String(100), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    dataset_manifest: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    simulation_run_id: Mapped[str] = mapped_column(ForeignKey("simulation_runs.id"), unique=True, nullable=False)
    analysis_version: Mapped[str] = mapped_column(String(100), nullable=False)
    results: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class DecisionMemo(Base):
    __tablename__ = "decision_memos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    plan_id: Mapped[str] = mapped_column(ForeignKey("measurement_plans.id"), nullable=False)
    analysis_result_id: Mapped[str] = mapped_column(ForeignKey("analysis_results.id"), nullable=False)
    recommendation: Mapped[str] = mapped_column(String(64), nullable=False)
    rationale: Mapped[str] = mapped_column(String(4000), nullable=False)
    limitations: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    evidence_references: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    review_state: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))