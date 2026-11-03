from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import (
    AnalysisResult,
    AuditEvent,
    DecisionMemo,
    DesignRun,
    Initiative,
    MeasurementPlan,
    SimulationRun,
)
from app.security import AuthenticatedAccess

router = APIRouter(prefix="/api", tags=["workspace"])


@router.get("/workspace")
def get_workspace(
    user: AuthenticatedAccess,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    initiatives = session.scalars(select(Initiative).order_by(Initiative.created_at.desc())).all()
    plans = session.scalars(select(MeasurementPlan).order_by(MeasurementPlan.created_at.desc())).all()
    design_runs = session.scalars(select(DesignRun).order_by(DesignRun.created_at.desc())).all()
    simulation_runs = session.scalars(select(SimulationRun).order_by(SimulationRun.created_at.desc())).all()
    analyses = session.scalars(select(AnalysisResult)).all()
    memos = session.scalars(select(DecisionMemo).order_by(DecisionMemo.created_at.desc())).all()
    audit_events = session.scalars(
        select(AuditEvent).order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(200)
    ).all()

    initiatives_by_id = {initiative.id: initiative for initiative in initiatives}
    analyses_by_id = {analysis.id: analysis for analysis in analyses}
    analyses_by_simulation = {analysis.simulation_run_id: analysis for analysis in analyses}

    return {
        "user": {"username": user["username"], "role": user["role"]},
        "initiatives": [
            {
                "id": initiative.id,
                "title": initiative.title,
                "business_question": initiative.business_question,
                "proposed_decision": initiative.proposed_decision,
                "stakeholder_role": initiative.stakeholder_role,
                "eligible_population": initiative.eligible_population,
                "wrong_decision_consequences": initiative.wrong_decision_consequences,
                "created_at": initiative.created_at,
            }
            for initiative in initiatives
        ],
        "plans": [
            {
                "id": plan.id,
                "initiative_id": plan.initiative_id,
                "initiative_title": initiatives_by_id[plan.initiative_id].title,
                "version": plan.version,
                "status": plan.status,
                "created_at": plan.created_at,
                "frozen_at": plan.frozen_at,
                "specification": plan.specification,
            }
            for plan in plans
        ],
        "design_runs": [
            {
                "id": run.id,
                "plan_id": run.plan_id,
                "algorithm_version": run.algorithm_version,
                "seed": run.seed,
                "inputs": run.inputs,
                "results": run.results,
                "created_at": run.created_at,
            }
            for run in design_runs
        ],
        "simulation_runs": [
            {
                "id": run.id,
                "plan_id": run.plan_id,
                "scenario": run.scenario,
                "generator_version": run.generator_version,
                "seed": run.seed,
                "dataset_manifest": run.dataset_manifest,
                "analysis_result_id": analyses_by_simulation[run.id].id,
                "results": analyses_by_simulation[run.id].results,
                "created_at": run.created_at,
            }
            for run in simulation_runs
            if run.id in analyses_by_simulation
        ],
        "memos": [
            {
                "id": memo.id,
                "plan_id": memo.plan_id,
                "analysis_result_id": memo.analysis_result_id,
                "recommendation": memo.recommendation,
                "rationale": memo.rationale,
                "limitations": memo.limitations,
                "evidence_references": memo.evidence_references,
                "review_state": memo.review_state,
                "created_at": memo.created_at,
                "reviewed_at": memo.reviewed_at,
                "results": analyses_by_id[memo.analysis_result_id].results
                if memo.analysis_result_id in analyses_by_id
                else None,
            }
            for memo in memos
        ],
        "audit_events": [
            {
                "id": audit_event.id,
                "actor_username": audit_event.actor_username,
                "actor_role": audit_event.actor_role,
                "action": audit_event.action,
                "entity_type": audit_event.entity_type,
                "entity_id": audit_event.entity_id,
                "initiative_id": audit_event.initiative_id,
                "plan_id": audit_event.plan_id,
                "details": audit_event.details,
                "created_at": audit_event.created_at,
            }
            for audit_event in audit_events
        ],
    }