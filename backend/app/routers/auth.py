from datetime import UTC, datetime, timedelta
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import (clear_login_cookies, hash_password, send_password_reset_email,
                    set_login_cookies, token_digest, verify_password)
from ..db import get_db
from ..models import PasswordResetToken, User
from ..schemas import AuthUserOut, ForgotPasswordIn, LoginIn, RegisterIn, ResetPasswordIn

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register", response_model=AuthUserOut, status_code=201)
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists.")
    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    set_login_cookies(response, user)
    return user


@router.post("/login", response_model=AuthUserOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Email or password is incorrect.")
    set_login_cookies(response, user)
    return user


@router.post("/logout", status_code=204)
def logout(response: Response):
    clear_login_cookies(response)
    return response


@router.get("/me", response_model=AuthUserOut)
def me(request: Request, db: Session = Depends(get_db)):
    from ..auth import get_current_user
    return get_current_user(request, db)


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordIn, db: Session = Depends(get_db)):
    # Same response whether or not the email exists, to prevent account enumeration.
    user = db.scalar(select(User).where(User.email == body.email.strip().lower(), User.is_active.is_(True)))
    if user:
        raw = secrets.token_urlsafe(40)
        db.add(PasswordResetToken(
            user_id=user.id,
            token_hash=token_digest(raw),
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        ))
        db.commit()
        try:
            send_password_reset_email(user.email, raw)
        except Exception:
            # Avoid leaking account existence or SMTP details to callers.
            pass
    return {"message": "If an account exists for that email, a reset link will be sent."}


@router.post("/reset-password")
def reset_password(body: ResetPasswordIn, db: Session = Depends(get_db)):
    now = datetime.now(UTC)
    record = db.scalar(select(PasswordResetToken).where(
        PasswordResetToken.token_hash == token_digest(body.token),
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at > now,
    ))
    if not record:
        raise HTTPException(400, "This reset link is invalid or has expired.")
    user = db.get(User, record.user_id)
    if not user or not user.is_active:
        raise HTTPException(400, "This reset link is invalid or has expired.")
    record.used_at = now
    user.password_hash = hash_password(body.password)
    user.auth_version += 1
    db.commit()
    return {"message": "Password updated. Please sign in with your new password."}
