from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
import smtplib

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import User

_password_hasher = PasswordHasher()
COOKIE_NAME = "gradmatch_session"
CSRF_COOKIE = "gradmatch_csrf"


def _serializer():
    secret = get_settings().secret_key
    if not secret or len(secret) < 32:
        raise RuntimeError("SECRET_KEY must be configured with at least 32 characters")
    return URLSafeTimedSerializer(secret, salt="gradmatch-auth-v1")


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _password_hasher.verify(hashed, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def _csrf_value() -> str:
    return secrets.token_urlsafe(32)


def set_login_cookies(response: Response, user: User) -> None:
    settings = get_settings()
    token = _serializer().dumps({"uid": user.id, "ver": user.auth_version})
    csrf = _csrf_value()
    common = {"secure": settings.cookie_secure, "samesite": "lax", "path": "/"}
    response.set_cookie(COOKIE_NAME, token, httponly=True, max_age=43200, **common)
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, max_age=43200, **common)


def clear_login_cookies(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(401, "Please sign in to continue.")
    try:
        data = _serializer().loads(token, max_age=43200)
    except (BadSignature, SignatureExpired):
        raise HTTPException(401, "Your session has expired. Please sign in again.") from None
    user = db.scalar(select(User).where(User.id == data.get("uid"), User.is_active.is_(True)))
    if not user or user.auth_version != data.get("ver"):
        raise HTTPException(401, "Your session is no longer valid. Please sign in again.")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        cookie_csrf = request.cookies.get(CSRF_COOKIE)
        header_csrf = request.headers.get("X-CSRF-Token")
        if not cookie_csrf or not header_csrf or not secrets.compare_digest(cookie_csrf, header_csrf):
            raise HTTPException(403, "Security check failed. Refresh the page and try again.")
    return user


def send_password_reset_email(email: str, token: str) -> None:
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_from:
        # Do not log or return reset tokens. Configure SMTP before enabling public recovery.
        return
    message = EmailMessage()
    message["Subject"] = "Reset your GradMatch AI password"
    message["From"] = settings.smtp_from
    message["To"] = email
    link = f"{settings.public_app_url.rstrip('/')}/?reset_token={token}"
    message.set_content(
        "We received a request to reset your GradMatch AI password.\n\n"
        f"Use this one-time link within 30 minutes: {link}\n\n"
        "If you did not request this, you can ignore this message."
    )
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        if settings.smtp_starttls:
            server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password or "")
        server.send_message(message)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def csrf_for_frontend(request: Request) -> str | None:
    return request.cookies.get(CSRF_COOKIE)
