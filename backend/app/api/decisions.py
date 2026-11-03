from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import AnalysisResult, DecisionMemo, MeasurementPlan, SimulationRun, now_utc
from app.schemas import MemoCreate
from app.security import AnalystAccess, AuthenticatedAccess, ReviewerAccess

router = APIRouter(prefix="/api", tags=["decisions"])


@router.get("/memos/{memo_id}")
def get_memo(
    memo_id: str,
    _: AuthenticatedAccess,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    memo = session.get(DecisionMemo, memo_id)
    if memo is None:
        raise HTTPException(status_code=404, detail="Memo not found")
    analysis = session.get(AnalysisResult, memo.analysis_result_id)
    return {
        "id": memo.id,
        "plan_id": memo.plan_id,
        "analysis_result_id": memo.analysis_result_id,
        "recommendation": memo.recommendation,
        "rationale": memo.rationale,
        "limitations": memo.limitations,
        "evidence_references": memo.evidence_references,
        "review_state": memo.review_state,
        "results": analysis.results if analysis else None,
    }


@router.post("/plans/{plan_id}/memos", status_code=201)
def create_memo(
    plan_id: str,
    payload: MemoCreate,
    _: AnalystAccess,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    plan = session.get(MeasurementPlan, plan_id)
    analysis = session.get(AnalysisResult, payload.analysis_result_id)
    if plan is None or plan.status != "frozen":
        raise HTTPException(status_code=404, detail="Frozen plan not found")
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis result not found")
    simulation = session.get(SimulationRun, analysis.simulation_run_id)
    if simulation is None or simulation.plan_id != plan_id:
        raise HTTPException(status_code=409, detail="Memo evidence must come from this frozen plan")
    memo = DecisionMemo(
        plan_id=plan_id,
        analysis_result_id=analysis.id,
        recommendation=payload.recommendation,
        rationale=payload.rationale,
        limitations=payload.limitations,
        evidence_references=payload.evidence_references,
        review_state="draft",
    )
    session.add(memo)
    session.commit()
    session.refresh(memo)
    return {"id": memo.id, "plan_id": plan_id, "review_state": memo.review_state}


@router.post("/memos/{memo_id}/review")
def review_memo(
    memo_id: str,
    _: ReviewerAccess,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    memo = session.get(DecisionMemo, memo_id)
    if memo is None:
        raise HTTPException(status_code=404, detail="Memo not found")
    if memo.review_state != "draft":
        raise HTTPException(status_code=409, detail="Memo has already been reviewed")
    memo.review_state = "reviewed"
    memo.reviewed_at = now_utc()
    session.commit()
    return {"id": memo.id, "review_state": memo.review_state, "reviewed_at": memo.reviewed_at}