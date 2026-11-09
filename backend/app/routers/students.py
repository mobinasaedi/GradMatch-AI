from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..auth import get_current_user
from ..models import User
from ..models import Outreach, OutreachEvent, Recommendation, RecommendationRun, Student
from ..schemas import StudentOut, StudentUpdate
from ..services.profile_extractor import extract_profile
from ..services.resume_parser import ResumeParseError, extract_text

router = APIRouter(prefix="/api/students", tags=["students"])


def get_student_or_404(db: Session, student_id: int, user: User) -> Student:
    student = db.scalar(select(Student).where(Student.id == student_id, Student.user_id == user.id))
    if not student:
        raise HTTPException(404, "Student not found")
    return student


@router.get("/mine", response_model=StudentOut | None)
def my_student(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalar(select(Student).where(Student.user_id == user.id).order_by(Student.id.desc()))


@router.post("", response_model=StudentOut, status_code=201)
def upload_resume(file: UploadFile, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    settings = get_settings()
    max_bytes = settings.upload_max_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)
    try:
        text = extract_text(file.filename or "", data, max_bytes)
    except ResumeParseError as exc:
        raise HTTPException(400, str(exc)) from exc

    profile = extract_profile(text)
    student = Student(
        user_id=user.id,
        filename=file.filename or "resume",
        raw_text=text,
        name=profile.name,
        field=profile.field,
        education=profile.education,
        gpa=profile.gpa,
        interests=profile.interests,
        skills=profile.skills,
        research_experience=profile.research_experience,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.get("/{student_id}", response_model=StudentOut)
def get_student(student_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_student_or_404(db, student_id, user)


@router.put("/{student_id}", response_model=StudentOut)
def update_student(student_id: int, body: StudentUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    student = get_student_or_404(db, student_id, user)
    for key, value in body.model_dump(exclude_unset=True).items():
        if key in ("interests", "skills") and value is not None:
            value = [v.strip() for v in value if v.strip()]
        setattr(student, key, value)
    db.commit()
    db.refresh(student)
    return student


@router.delete("/{student_id}", status_code=204)
def delete_student(student_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Removes the resume text, profile, recommendations and tracking data of a student."""
    student = get_student_or_404(db, student_id, user)
    outreach_ids = list(db.scalars(select(Outreach.id).where(Outreach.student_id == student_id)))
    if outreach_ids:
        db.execute(delete(OutreachEvent).where(OutreachEvent.outreach_id.in_(outreach_ids)))
    db.execute(delete(Outreach).where(Outreach.student_id == student_id))
    db.execute(delete(Recommendation).where(Recommendation.student_id == student_id))
    db.execute(delete(RecommendationRun).where(RecommendationRun.student_id == student_id))
    db.delete(student)
    db.commit()
