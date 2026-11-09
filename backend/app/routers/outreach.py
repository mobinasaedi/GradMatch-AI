from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..auth import get_current_user
from ..models import User
from ..models import Outreach, OutreachEvent, Recommendation, Student
from ..schemas import (
    DraftOut,
    OutreachEventOut,
    OutreachOut,
    OutreachStats,
    OutreachStatus,
    OutreachUpdate,
    ProfessorOut,
)
from ..services.draft import build_draft
from .students import get_student_or_404

router = APIRouter(prefix="/api", tags=["outreach"])


def _out(o: Outreach) -> OutreachOut:
    return OutreachOut(
        id=o.id,
        student_id=o.student_id,
        professor=ProfessorOut.model_validate(o.professor),
        status=o.status,
        notes=o.notes,
        updated_at=o.updated_at,
    )


def _get_outreach(db: Session, outreach_id: int, user: User) -> Outreach:
    o = db.scalar(select(Outreach).join(Student, Student.id == Outreach.student_id).where(Outreach.id == outreach_id, Student.user_id == user.id))
    if not o:
        raise HTTPException(404, "Outreach record not found")
    return o


@router.get("/students/{student_id}/outreach", response_model=list[OutreachOut])
def list_outreach(student_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_student_or_404(db, student_id, user)
    rows = db.scalars(
        select(Outreach).where(Outreach.student_id == student_id).order_by(Outreach.updated_at.desc())
    )
    return [_out(o) for o in rows]


@router.get("/students/{student_id}/outreach/stats", response_model=OutreachStats)
def outreach_stats(student_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_student_or_404(db, student_id, user)
    counts = Counter(db.scalars(select(Outreach.status).where(Outreach.student_id == student_id)))
    by_status = {s.value: counts.get(s.value, 0) for s in OutreachStatus}
    return OutreachStats(total=sum(by_status.values()), by_status=by_status)


@router.patch("/outreach/{outreach_id}", response_model=OutreachOut)
def update_outreach(outreach_id: int, body: OutreachUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    o = _get_outreach(db, outreach_id, user)
    changed_status = body.status is not None and body.status.value != o.status
    note_changed = body.notes is not None and body.notes != (o.notes or "")

    if body.status is not None:
        o.status = body.status.value
    if body.notes is not None:
        o.notes = body.notes
    if changed_status or note_changed:
        db.add(
            OutreachEvent(
                outreach_id=o.id,
                status=o.status,
                note=body.notes if note_changed else None,
            )
        )
    db.commit()
    db.refresh(o)
    return _out(o)


@router.get("/outreach/{outreach_id}/events", response_model=list[OutreachEventOut])
def outreach_events(outreach_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _get_outreach(db, outreach_id, user).events


@router.get("/outreach/{outreach_id}/draft", response_model=DraftOut)
def outreach_draft(outreach_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    o = _get_outreach(db, outreach_id, user)
    student = db.get(Student, o.student_id)
    rec = db.scalars(
        select(Recommendation)
        .where(Recommendation.student_id == o.student_id, Recommendation.professor_id == o.professor_id)
        .order_by(Recommendation.id.desc())
    ).first()
    subject, body = build_draft(
        student.name if student else None,
        student.field if student else None,
        o.professor.name,
        rec.explanation if rec else None,
    )
    return DraftOut(subject=subject, body=body)
