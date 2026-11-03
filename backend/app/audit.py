from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models import AuditEvent, now_utc


def record_audit_event(
    session: Session,
    actor: dict[str, str],
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    initiative_id: str | None = None,
    plan_id: str | None = None,
    details: dict[str, object] | None = None,
) -> None:
    session.add(
        AuditEvent(
            actor_username=actor["username"],
            actor_role=actor["role"],
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            initiative_id=initiative_id,
            plan_id=plan_id,
            details=details or {},
            created_at=now_utc(),
        )
    )


@event.listens_for(AuditEvent, "before_update")
def reject_audit_event_update(mapper, connection, target) -> None:
    raise ValueError("Audit events are append-only")


@event.listens_for(AuditEvent, "before_delete")
def reject_audit_event_delete(mapper, connection, target) -> None:
    raise ValueError("Audit events are append-only")