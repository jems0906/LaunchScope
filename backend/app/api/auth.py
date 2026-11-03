import hashlib
import hmac
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request, Response, status

from app.schemas import LoginInput
from app.security import (
    SESSION_COOKIE_NAME,
    SESSION_LIFETIME_SECONDS,
    issue_session,
    read_session,
)
from app.settings import settings

router = APIRouter(prefix="/api/auth", tags=["authentication"])


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, salt, digest = encoded_hash.split(":", maxsplit=2)
        if algorithm != "scrypt":
            return False
        expected = bytes.fromhex(digest)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt),
            n=2**14,
            r=8,
            p=1,
            dklen=len(expected),
            maxmem=64 * 1024 * 1024,
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


@router.get("/session")
def session_status(request: Request) -> dict[str, object]:
    session = read_session(request)
    if session is None:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "username": session["username"],
        "role": session["role"],
        "csrf_token": session["csrf"],
    }


@router.post("/login")
def login(payload: LoginInput, response: Response) -> dict[str, str | bool]:
    configured_users = (
        (settings.analyst_username, settings.analyst_password_hash, "analyst"),
        (settings.reviewer_username, settings.reviewer_password_hash, "reviewer"),
    )
    if len(settings.session_secret) < 32 or not any(
        username and password_hash for username, password_hash, _ in configured_users
    ):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Session accounts are not configured")
    match = next(
        (
            (role, password_hash)
            for username, password_hash, role in configured_users
            if username and hmac.compare_digest(payload.username, username)
        ),
        None,
    )
    if match is None or not verify_password(payload.password, match[1]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    role, _ = match
    token, csrf_token = issue_session(payload.username, role)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=SESSION_LIFETIME_SECONDS,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
        path="/",
    )
    return {"authenticated": True, "username": payload.username, "role": role, "csrf_token": csrf_token}


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    session = read_session(request)
    if session is not None and (csrf_token is None or not hmac.compare_digest(csrf_token, session["csrf"])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Valid X-CSRF-Token required")
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
    )