import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_session
from app.main import app
from app.api.auth import verify_password
from app.auth_admin import hash_password
from app.settings import settings

client = TestClient(app)


def sign_in(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    client.headers.update({"X-CSRF-Token": response.json()["csrf_token"]})
    return response.json()


@pytest.fixture
def authorized_client(monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_session():
        session = test_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_session
    monkeypatch.setattr(settings, "session_secret", "test-session-secret-with-sufficient-length")
    monkeypatch.setattr(settings, "analyst_username", "test-analyst")
    monkeypatch.setattr(settings, "analyst_password_hash", hash_password("analyst-test-password"))
    monkeypatch.setattr(settings, "reviewer_username", "test-reviewer")
    monkeypatch.setattr(settings, "reviewer_password_hash", hash_password("reviewer-test-password"))
    try:
        test_client = TestClient(app)
        sign_in(test_client, "test-analyst", "analyst-test-password")
        yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def create_frozen_plan(
    client: TestClient, subgroup_question: str = "none"
) -> tuple[str, str]:
    initiative = client.post(
        "/api/initiatives",
        json={
            "title": "Fictional game discovery",
            "business_question": "Did the module offer increase qualified game sessions?",
            "proposed_decision": "Continue, redesign, or stop the offer",
            "alternatives": ["Existing discovery", "Redesign and retest"],
            "stakeholder_role": "Content & Games Product Lead",
            "eligible_population": "Households eligible before assignment",
            "timing": "One fixed 28-day window",
            "wrong_decision_consequences": "A false positive could worsen household experience.",
        },
    )
    assert initiative.status_code == 201
    initiative_id = initiative.json()["id"]
    plan = client.post(
        f"/api/initiatives/{initiative_id}/plans",
        json={
            "question": "Did offering the module alter qualified household sessions?",
            "estimand": "Household intention-to-treat rate difference",
            "population": "All households eligible before assignment",
            "eligibility_fixed_before_assignment": True,
            "randomization_unit": "household",
            "allocation_treatment": 0.5,
            "observation_window_days": 28,
            "primary_outcome": "Assigned-household rate with one qualified session",
            "practical_threshold": 0.01,
            "subgroup_question": subgroup_question,
            "diagnostics": ["Exposure / assigned households", "Interaction / assigned households"],
            "guardrails": ["Playback failure / eligible sessions"],
            "baseline_rate": 0.10,
            "target_effect": 0.01,
            "alpha": 0.05,
            "desired_power": 0.80,
            "attrition": 0.05,
            "missingness_rule": "Unknown outcomes stay missing; report completeness by arm.",
            "spillover_assumption": "Assume no material interference across households.",
            "fixed_horizon_no_early_stop": True,
        },
    )
    assert plan.status_code == 201
    plan_id = plan.json()["id"]
    frozen = client.post(f"/api/plans/{plan_id}/freeze")
    assert frozen.status_code == 200
    return initiative_id, plan_id


def test_health_endpoint() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_auth_session_endpoint_reports_public_read_only_state() -> None:
    response = client.get("/api/auth/session")

    assert response.status_code == 200
    assert response.json() == {"authenticated": False}


def test_analyst_login_issues_http_only_cookie_and_session_csrf(authorized_client: TestClient) -> None:
    session = authorized_client.get("/api/auth/session")

    assert session.status_code == 200
    assert session.json()["authenticated"] is True
    assert session.json()["username"] == "test-analyst"
    assert session.json()["role"] == "analyst"
    assert session.json()["csrf_token"] == authorized_client.headers["X-CSRF-Token"]
    assert authorized_client.cookies.get("launchscope_session")
    login_response = authorized_client.post(
        "/api/auth/login",
        json={"username": "test-analyst", "password": "analyst-test-password"},
    )
    cookie_header = login_response.headers["set-cookie"].lower()
    assert "httponly" in cookie_header
    assert "samesite=strict" in cookie_header


def test_password_verification_rejects_mismatched_password() -> None:
    encoded = hash_password("right-password")

    assert verify_password("right-password", encoded) is True
    assert verify_password("wrong-password", encoded) is False


def test_analyst_write_requires_csrf_and_reviewer_cannot_freeze_plans(authorized_client: TestClient) -> None:
    _, plan_id = create_frozen_plan(authorized_client)

    missing_csrf = authorized_client.post(
        f"/api/plans/{plan_id}/freeze",
        headers={"X-CSRF-Token": ""},
    )
    assert missing_csrf.status_code == 403

    reviewer_session = sign_in(authorized_client, "test-reviewer", "reviewer-test-password")
    forbidden_freeze = authorized_client.post(
        f"/api/plans/{plan_id}/freeze",
        headers={"X-CSRF-Token": reviewer_session["csrf_token"]},
    )
    assert forbidden_freeze.status_code == 403


def test_logout_clears_session_cookie(authorized_client: TestClient) -> None:
    csrf_token = authorized_client.headers["X-CSRF-Token"]
    invalid_logout = authorized_client.post("/api/auth/logout", headers={"X-CSRF-Token": "wrong"})
    assert invalid_logout.status_code == 403
    response = authorized_client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_token})

    assert response.status_code == 204
    assert authorized_client.get("/api/auth/session").json() == {"authenticated": False}


def test_tampered_signed_session_is_rejected(authorized_client: TestClient) -> None:
    _, plan_id = create_frozen_plan(authorized_client)
    token = authorized_client.cookies.get("launchscope_session")
    assert token
    authorized_client.cookies.set("launchscope_session", f"{token[:-1]}x")

    assert authorized_client.get("/api/auth/session").json() == {"authenticated": False}
    assert authorized_client.post(f"/api/plans/{plan_id}/freeze").status_code == 401


def test_sensitivity_endpoint_exposes_shortfall() -> None:
    response = client.get(
        "/api/sensitivity",
        params={"baseline_rate": 0.1, "target_effect": 0.01, "available_households": 500},
    )

    assert response.status_code == 200
    assert response.json()["detectable_effect"] > response.json()["target_effect"]
    assert response.json()["detectable_effect_achievable"] is True


def test_demo_scenario_is_fixed_and_reproducible() -> None:
    first = client.get("/api/demo/scenarios/tradeoff")
    second = client.get("/api/demo/scenarios/tradeoff")

    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["dataset_manifest"]["synthetic"] is True
    assert first.json()["scenario_config_version"] == "game-discovery-scenarios-v4"
    assert first.json()["plan_reference"] == {
        "plan_id": "demo-game-discovery-v1",
        "version": 1,
        "status": "frozen",
    }
    assert first.json()["result"]["guardrails"]["playback_quality"]["exceeds_harm_margin"] is True


def test_unknown_demo_scenario_is_rejected() -> None:
    assert client.get("/api/demo/scenarios/arbitrary").status_code == 404


def test_public_client_cannot_create_initiative(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "session_secret", "")
    response = client.post("/api/initiatives", json={})

    assert response.status_code == 503


def test_public_client_cannot_read_analyst_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "session_secret", "")

    assert client.get("/api/workspace").status_code == 503


def test_frozen_plan_lifecycle_records_design_scenario_and_reviewed_memo(authorized_client: TestClient) -> None:
    _, plan_id = create_frozen_plan(authorized_client, subgroup_question="prior_game_engagement")

    audit_response = authorized_client.get("/api/workspace")
    audit_events = audit_response.json()["audit_events"]
    assert [event["action"] for event in reversed(audit_events)] == [
        "initiative.created",
        "plan.created",
        "plan.frozen",
    ]
    assert all(event["actor_username"] == "test-analyst" for event in audit_events)

    assert authorized_client.post(f"/api/plans/{plan_id}/freeze").status_code == 409
    design = authorized_client.post(
        f"/api/plans/{plan_id}/design-runs",
        json={"available_households": 10000, "seed": 73},
    )
    assert design.status_code == 201
    assert design.json()["results"]["baseline_rate"] == 0.10
    assert design.json()["results"]["target_effect"] == 0.01
    design_audit = authorized_client.get("/api/workspace").json()["audit_events"]
    assert any(event["action"] == "design_run.created" and event["entity_id"] == design.json()["id"] for event in design_audit)

    simulation = authorized_client.post(
        f"/api/plans/{plan_id}/simulation-runs",
        json={"scenario": "tradeoff", "seed": 73, "households_per_arm": 100},
    )
    assert simulation.status_code == 201
    assert simulation.json()["plan_reference"] == {"plan_id": plan_id, "version": 1, "status": "frozen"}
    assert simulation.json()["dataset_manifest"]["synthetic"] is True
    assert simulation.json()["dataset_manifest"]["scenario_config_version"] == "game-discovery-scenarios-v4"
    subgroup = simulation.json()["result"]["subgroup_analysis"]
    assert subgroup["question"] == "prior_game_engagement"
    assert set(subgroup["groups"]) == {"no_prior_game_engagement", "prior_game_engagement"}
    assert "interval_low" in subgroup["interaction"]
    assert "interval_high" in subgroup["interaction"]
    simulation_audit = authorized_client.get("/api/workspace").json()["audit_events"]
    assert any(event["action"] == "simulation_run.generated" and event["entity_id"] == simulation.json()["id"] for event in simulation_audit)
    assert any(event["action"] == "analysis_result.created" and event["entity_id"] == simulation.json()["analysis_result_id"] for event in simulation_audit)

    _, other_plan_id = create_frozen_plan(authorized_client)
    other_simulation = authorized_client.post(
        f"/api/plans/{other_plan_id}/simulation-runs",
        json={"scenario": "null", "seed": 74, "households_per_arm": 100},
    )
    cross_plan_memo = authorized_client.post(
        f"/api/plans/{plan_id}/memos",
        json={
            "analysis_result_id": other_simulation.json()["analysis_result_id"],
            "recommendation": "inconclusive",
            "rationale": "This analysis belongs to a different frozen plan and cannot support this memo.",
            "limitations": ["Cross-plan evidence"],
            "evidence_references": [other_simulation.json()["id"]],
        },
    )
    assert cross_plan_memo.status_code == 409

    memo = authorized_client.post(
        f"/api/plans/{plan_id}/memos",
        json={
            "analysis_result_id": simulation.json()["analysis_result_id"],
            "recommendation": "redesign",
            "rationale": "The primary estimate and a guardrail tradeoff require stakeholder review.",
            "limitations": ["Synthetic scenario", "Fixed 28-day window"],
            "evidence_references": [simulation.json()["id"]],
        },
    )
    assert memo.status_code == 201
    assert memo.json()["review_state"] == "draft"
    memo_audit = authorized_client.get("/api/workspace").json()["audit_events"]
    assert any(event["action"] == "decision_memo.drafted" and event["entity_id"] == memo.json()["id"] for event in memo_audit)

    analyst_workspace = authorized_client.get("/api/workspace")
    assert analyst_workspace.status_code == 200
    assert analyst_workspace.json()["user"]["role"] == "analyst"
    assert any(plan["id"] == plan_id and plan["status"] == "frozen" for plan in analyst_workspace.json()["plans"])
    assert any(run["id"] == simulation.json()["id"] for run in analyst_workspace.json()["simulation_runs"])
    assert any(item["id"] == memo.json()["id"] and item["results"] for item in analyst_workspace.json()["memos"])

    analyst_csrf = authorized_client.headers["X-CSRF-Token"]
    assert authorized_client.post(
        f"/api/memos/{memo.json()['id']}/review",
        headers={"X-CSRF-Token": analyst_csrf},
    ).status_code == 403
    reviewer_session = sign_in(authorized_client, "test-reviewer", "reviewer-test-password")
    reviewer_workspace = authorized_client.get("/api/workspace")
    assert reviewer_workspace.json()["user"]["role"] == "reviewer"
    assert any(
        item["id"] == memo.json()["id"] and item["review_state"] == "draft"
        for item in reviewer_workspace.json()["memos"]
    )
    memo_details = authorized_client.get(f"/api/memos/{memo.json()['id']}")
    assert memo_details.status_code == 200
    assert memo_details.json()["recommendation"] == "redesign"
    assert memo_details.json()["results"]["primary"]["estimate"] == simulation.json()["result"]["primary"]["estimate"]
    reviewed = authorized_client.post(
        f"/api/memos/{memo.json()['id']}/review",
        headers={"X-CSRF-Token": reviewer_session["csrf_token"]},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["review_state"] == "reviewed"
    reviewed_audit = authorized_client.get("/api/workspace").json()["audit_events"]
    review_event = next(event for event in reviewed_audit if event["action"] == "decision_memo.reviewed")
    assert review_event["entity_id"] == memo.json()["id"]
    assert review_event["actor_username"] == "test-reviewer"
    assert review_event["actor_role"] == "reviewer"
    assert authorized_client.post(
        f"/api/memos/{memo.json()['id']}/review",
        headers={"X-CSRF-Token": reviewer_session["csrf_token"]},
    ).status_code == 409


def test_plan_cannot_create_evaluation_data_before_freeze(authorized_client: TestClient) -> None:
    initiative_id, plan_id = create_frozen_plan(authorized_client)
    draft = authorized_client.post(
        f"/api/initiatives/{initiative_id}/plans",
        json={
            "question": "Did offering the module alter qualified household sessions?",
            "estimand": "Household intention-to-treat rate difference",
            "population": "All households eligible before assignment",
            "eligibility_fixed_before_assignment": True,
            "randomization_unit": "household",
            "primary_outcome": "Assigned-household rate with one qualified session",
            "diagnostics": ["Exposure / assigned households", "Interaction / assigned households"],
            "guardrails": ["Playback failure / eligible sessions"],
            "missingness_rule": "Unknown outcomes stay missing; report completeness by arm.",
            "spillover_assumption": "Assume no material interference across households.",
        },
    )
    assert draft.status_code == 201
    draft_id = draft.json()["id"]
    assert draft.json()["version"] == 2
    assert authorized_client.post(
        f"/api/plans/{draft_id}/simulation-runs",
        json={"scenario": "null", "seed": 5, "households_per_arm": 20},
    ).status_code == 409
    assert authorized_client.get(f"/api/demo/scenarios/tradeoff").status_code == 200