import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import AnalysisResult, MeasurementPlan, SimulationRun
from app.schemas import SimulationRunInput
from app.security import AnalystAccess
from measurement_core import GENERATOR_VERSION, analyze_dataset, generate_scenario
from measurement_core.simulation import SCENARIO_CONFIG_VERSION, SCENARIOS

router = APIRouter(prefix="/api", tags=["simulations"])
SEED_BY_SCENARIO = {"helpful": 1103, "null": 2207, "harmful": 3301, "tradeoff": 4409}
DEMO_PLAN_ID = "demo-game-discovery-v1"


def scenario_summary(scenario: str, seed: int, households_per_arm: int) -> dict[str, object]:
    rows = generate_scenario(scenario, seed=seed, households_per_arm=households_per_arm)
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    result = analyze_dataset(rows)
    return {
        "scenario": scenario,
        "label": SCENARIOS[scenario]["label"],
        "description": SCENARIOS[scenario]["description"],
        "generator_version": GENERATOR_VERSION,
        "scenario_config_version": SCENARIO_CONFIG_VERSION,
        "analysis_version": result["analysis_version"],
        "plan_reference": {"plan_id": DEMO_PLAN_ID, "version": 1, "status": "frozen"},
        "seed": seed,
        "dataset_manifest": {
            "synthetic": True,
            "scenario_config_version": SCENARIO_CONFIG_VERSION,
            "households_per_arm": households_per_arm,
            "row_count": len(rows),
            "sha256": hashlib.sha256(canonical).hexdigest(),
        },
        "result": result,
    }


@router.get("/demo/scenarios")
def list_scenarios() -> dict[str, object]:
    return {
        "initiative": "Fictional game-discovery module offer",
        "design": {
            "assignment_unit": "household",
            "allocation": "1:1",
            "observation_window_days": 28,
            "estimand": "Intention-to-treat difference in qualified-session household rates",
        },
        "scenarios": [
            {"id": name, "label": config["label"], "description": config["description"]}
            for name, config in SCENARIOS.items()
        ],
    }


@router.get("/demo/scenarios/{scenario}")
def get_demo_scenario(scenario: str) -> dict[str, object]:
    if scenario not in SEED_BY_SCENARIO:
        raise HTTPException(status_code=404, detail="Unknown fixed scenario")
    return scenario_summary(scenario, SEED_BY_SCENARIO[scenario], 2500)


@router.post("/plans/{plan_id}/simulation-runs", status_code=201)
def create_simulation_run(
    plan_id: str,
    payload: SimulationRunInput,
    _: AnalystAccess,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    plan = session.get(MeasurementPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.status != "frozen":
        raise HTTPException(status_code=409, detail="Freeze the plan before generating evaluation data")
    summary = scenario_summary(payload.scenario, payload.seed, payload.households_per_arm)
    summary["plan_reference"] = {"plan_id": plan.id, "version": plan.version, "status": plan.status}
    run = SimulationRun(
        plan_id=plan_id,
        scenario=payload.scenario,
        generator_version=GENERATOR_VERSION,
        seed=payload.seed,
        dataset_manifest=summary["dataset_manifest"],
    )
    session.add(run)
    session.flush()
    analysis = AnalysisResult(
        simulation_run_id=run.id,
        analysis_version=summary["result"]["analysis_version"],
        results=summary["result"],
    )
    session.add(analysis)
    session.commit()
    return {"id": run.id, "analysis_result_id": analysis.id, **summary}