import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.audit
from app.database import Base
from app.models import AuditEvent


def test_audit_events_reject_orm_updates_and_deletes() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        record = AuditEvent(
            actor_username="analyst",
            actor_role="analyst",
            action="plan.frozen",
            entity_type="measurement_plan",
            entity_id="plan-1",
            initiative_id="initiative-1",
            plan_id="plan-1",
            details={"version": 1},
        )
        session.add(record)
        session.commit()

        record.action = "plan.unfrozen"
        with pytest.raises(ValueError, match="append-only"):
            session.commit()
        session.rollback()

        with pytest.raises(ValueError, match="append-only"):
            session.delete(record)
            session.commit()
        session.rollback()

    engine.dispose()