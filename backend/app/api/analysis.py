from fastapi import APIRouter, HTTPException, Query

from measurement_core import plan_sensitivity

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/sensitivity")
def sensitivity(
    baseline_rate: float = Query(default=0.10, gt=0, lt=1),
    target_effect: float = Query(default=0.01, gt=0, lt=0.5),
    allocation_treatment: float = Query(default=0.5, gt=0, lt=1),
    alpha: float = Query(default=0.05, gt=0, lt=1),
    power: float = Query(default=0.80, gt=0, lt=1),
    attrition: float = Query(default=0.05, ge=0, lt=1),
    available_households: int = Query(default=10000, ge=4, le=1_000_000),
) -> dict[str, float | int | str | bool]:
    try:
        return plan_sensitivity(
            baseline_rate=baseline_rate,
            target_effect=target_effect,
            allocation_treatment=allocation_treatment,
            alpha=alpha,
            power=power,
            attrition=attrition,
            available_households=available_households,
        ).as_dict()
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error