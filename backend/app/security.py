import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from app.settings import settings


SESSION_COOKIE_NAME = "launchscope_session"
SESSION_LIFETIME_SECONDS = 8 * 60 * 60


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def issue_session(username: str, role: str) -> tuple[str, str]:
    csrf_token = secrets.token_urlsafe(32)
    payload = {
        "username": username,
        "role": role,
        "csrf": csrf_token,
        "expires": int(time.time()) + SESSION_LIFETIME_SECONDS,
    }
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(
        settings.session_secret.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256
    ).digest()
    return f"{encoded_payload}.{_b64encode(signature)}", csrf_token


def read_session(request: Request) -> dict[str, str] | None:
    if len(settings.session_secret) < 32:
        return None
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    try:
        encoded_payload, encoded_signature = token.split(".", maxsplit=1)
        provided_signature = base64.urlsafe_b64decode(encoded_signature + "=" * (-len(encoded_signature) % 4))
        expected_signature = hmac.new(
            settings.session_secret.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(provided_signature, expected_signature):
            return None
        payload_bytes = base64.urlsafe_b64decode(encoded_payload + "=" * (-len(encoded_payload) % 4))
        payload = json.loads(payload_bytes)
        if not isinstance(payload, dict):
            return None
        if int(payload["expires"]) <= int(time.time()):
            return None
        if payload.get("role") not in {"analyst", "reviewer"}:
            return None
        if not all(isinstance(payload.get(key), str) for key in ("username", "role", "csrf")):
            return None
        return {key: payload[key] for key in ("username", "role", "csrf")}
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def _require_role(
    request: Request,
    role: str,
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> dict[str, str]:
    if len(settings.session_secret) < 32:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Session authentication is not configured")
    session = read_session(request)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in required")
    if session["role"] != role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"{role.title()} role required")
    if csrf_token is None or not hmac.compare_digest(csrf_token, session["csrf"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Valid X-CSRF-Token required")
    return session


def require_analyst_access(
    request: Request,
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> dict[str, str]:
    return _require_role(request, "analyst", csrf_token)


def require_reviewer_access(
    request: Request,
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> dict[str, str]:
    return _require_role(request, "reviewer", csrf_token)


def require_authenticated_access(request: Request) -> dict[str, str | int]:
    if len(settings.session_secret) < 32:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Session authentication is not configured")
    session = read_session(request)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in required")
    return session


AnalystAccess = Annotated[dict[str, str], Depends(require_analyst_access)]
ReviewerAccess = Annotated[dict[str, str], Depends(require_reviewer_access)]
AuthenticatedAccess = Annotated[dict[str, str | int], Depends(require_authenticated_access)]