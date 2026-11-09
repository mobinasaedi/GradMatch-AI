from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..auth import get_current_user
from ..models import Professor, utcnow
from ..schemas import EmailConfirm, EmailLookupOut, EmailLookupRequest, ProfessorOut
from ..services.email_finder import (
    EmailLookupError,
    build_note,
    extract_emails,
    fetch_page,
    validate_official_url,
)
from ..services.universities import load_universities

router = APIRouter(prefix="/api/professors", tags=["professors"], dependencies=[Depends(get_current_user)])


def _professor_and_domains(db: Session, professor_id: str):
    prof = db.get(Professor, professor_id)
    if not prof:
        raise HTTPException(404, "Professor not found")
    uni = load_universities().get(prof.university_key)
    if not uni:
        raise HTTPException(400, "Unknown university for this professor")
    return prof, uni.domains


@router.post("/{professor_id}/email-lookup", response_model=EmailLookupOut)
def email_lookup(professor_id: str, body: EmailLookupRequest, db: Session = Depends(get_db)):
    """Scan an official faculty page for public emails. Nothing is stored yet."""
    prof, domains = _professor_and_domains(db, professor_id)
    try:
        final_url, page = fetch_page(body.page_url, domains)
    except EmailLookupError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # network errors
        raise HTTPException(502, f"Could not fetch the page: {exc}") from exc

    result = extract_emails(page, prof.name)
    prof.email_checked_at = utcnow()
    db.commit()
    return EmailLookupOut(source_url=final_url, note=build_note(result), **result)


@router.put("/{professor_id}/email", response_model=ProfessorOut)
def confirm_email(professor_id: str, body: EmailConfirm, db: Session = Depends(get_db)):
    """Store an email the user verified on an official page (source URL is required)."""
    prof, domains = _professor_and_domains(db, professor_id)
    try:
        validate_official_url(body.source_url, domains)
    except EmailLookupError as exc:
        raise HTTPException(400, str(exc)) from exc
    prof.email = body.email.lower()
    prof.email_source_url = body.source_url
    prof.email_checked_at = utcnow()
    db.commit()
    db.refresh(prof)
    return prof


@router.delete("/{professor_id}/email", response_model=ProfessorOut)
def clear_email(professor_id: str, db: Session = Depends(get_db)):
    prof, _ = _professor_and_domains(db, professor_id)
    prof.email = None
    prof.email_source_url = None
    db.commit()
    db.refresh(prof)
    return prof
