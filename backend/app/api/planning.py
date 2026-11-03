from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import record_audit_event
from app.database import get_session
from app.models import DesignRun, Initiative, MeasurementPlan
from app.schemas import DesignRunInput, InitiativeCreate, PlanSpecification
from app.security import AnalystAccess
from measurement_core import PLAN_ALGORITHM_VERSION, plan_sensitivity

router = APIRouter(prefix="/api", tags=["planning"])


@router.post("/initiatives", status_code=201)
def create_initiative(
    payload: InitiativeCreate,
    actor: AnalystAccess,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    initiative = Initiative(**payload.model_dump())
    session.add(initiative)
    session.flush()
    record_audit_event(
        session,
        actor,
        action="initiative.created",
        entity_type="initiative",
        entity_id=initiative.id,
        initiative_id=initiative.id,
        details={"title": initiative.title},
    )
    session.commit()
    session.refresh(initiative)
    return {"id": initiative.id, "title": initiative.title, "created_at": initiative.created_at}


@router.post("/initiatives/{initiative_id}/plans", status_code=201)
def create_plan(
    initiative_id: str,
    payload: PlanSpecification,
    actor: AnalystAccess,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    initiative = session.get(Initiative, initiative_id)
    if initiative is None:
        raise HTTPException(status_code=404, detail="Initiative not found")
    latest = session.scalar(
        select(func.max(MeasurementPlan.version)).where(MeasurementPlan.initiative_id == initiative_id)
    )
    plan = MeasurementPlan(
        initiative_id=initiative_id,
        version=(latest or 0) + 1,
        status="draft",
        specification=payload.model_dump(),
    )
    session.add(plan)
    session.flush()
    record_audit_event(
        session,
        actor,
        action="plan.created",
        entity_type="measurement_plan",
        entity_id=plan.id,
        initiative_id=initiative_id,
        plan_id=plan.id,
        details={"version": plan.version, "status": plan.status},
    )
    session.commit()
    session.refresh(plan)
    return {"id": plan.id, "initiative_id": initiative_id, "version": plan.version, "status": plan.status}


@router.post("/plans/{plan_id}/freeze")
def freeze_plan(
    plan_id: str,
    actor: AnalystAccess,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    plan = session.get(MeasurementPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.status != "draft":
        raise HTTPException(status_code=409, detail="Only a draft plan can be frozen; create a new version instead")
    from app.models import now_utc

    plan.status = "frozen"
    plan.frozen_at = now_utc()
    record_audit_event(
        session,
        actor,
        action="plan.frozen",
        entity_type="measurement_plan",
        entity_id=plan.id,
        initiative_id=plan.initiative_id,
        plan_id=plan.id,
        details={"version": plan.version, "frozen_at": plan.frozen_at.isoformat()},
    )
    session.commit()
    return {"id": plan.id, "version": plan.version, "status": plan.status, "frozen_at": plan.frozen_at}


@router.post("/plans/{plan_id}/design-runs", status_code=201)
def create_design_run(
    plan_id: str,
    payload: DesignRunInput,
    actor: AnalystAccess,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    plan = session.get(MeasurementPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.status != "frozen":
        raise HTTPException(status_code=409, detail="Freeze the plan before calculating sensitivity")
    specification = plan.specification
    planning_inputs = {
        "baseline_rate": specification["baseline_rate"],
        "target_effect": specification["target_effect"],
        "allocation_treatment": specification["allocation_treatment"],
        "alpha": specification["alpha"],
        "power": specification["desired_power"],
        "attrition": specification["attrition"],
        "available_households": payload.available_households,
    }
    results = plan_sensitivity(**planning_inputs).as_dict()
    design_run = DesignRun(
        plan_id=plan_id,
        algorithm_version=PLAN_ALGORITHM_VERSION,
        seed=payload.seed,
        inputs={**planning_inputs, "seed": payload.seed},
        results=results,
    )
    session.add(design_run)
    session.flush()
    record_audit_event(
        session,
        actor,
        action="design_run.created",
        entity_type="design_run",
        entity_id=design_run.id,
        initiative_id=plan.initiative_id,
        plan_id=plan.id,
        details={
            "algorithm_version": PLAN_ALGORITHM_VERSION,
            "seed": payload.seed,
            "available_households": payload.available_households,
        },
    )
    session.commit()
    session.refresh(design_run)
    return {"id": design_run.id, "plan_id": plan_id, "results": results}