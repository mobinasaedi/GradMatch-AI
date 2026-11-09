import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..auth import get_current_user
from ..models import User
from ..deps import get_embedder, get_openalex_client
from ..models import Outreach, Professor, Recommendation, RecommendationRun
from ..schemas import (
    ExplanationOut,
    ProfessorOut,
    RecommendationOut,
    RecommendationRunOut,
    RecommendRequest,
)
from ..services.discovery import discover_professors
from ..services.matcher import Embedder, build_professor_doc, build_student_text, rank_professors
from ..services.openalex import OpenAlexClient, OpenAlexError
from ..services.universities import select_universities
from .students import get_student_or_404

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/students/{student_id}/recommendations", tags=["recommendations"])


def _run_out(db: Session, run: RecommendationRun, warnings: list[str] | None = None) -> RecommendationRunOut:
    outreach = {
        o.professor_id: o
        for o in db.scalars(select(Outreach).where(Outreach.student_id == run.student_id))
    }
    results = []
    for rec in run.recommendations:
        o = outreach.get(rec.professor_id)
        results.append(
            RecommendationOut(
                rank=rec.rank,
                score=rec.score,
                semantic_score=rec.semantic_score,
                lexical_score=rec.lexical_score,
                professor=ProfessorOut.model_validate(rec.professor),
                explanation=ExplanationOut(**rec.explanation),
                outreach_id=o.id if o else None,
                outreach_status=o.status if o else None,
            )
        )
    return RecommendationRunOut(
        run_id=run.id,
        student_id=run.student_id,
        backend=run.backend,
        created_at=run.created_at,
        params=run.params,
        warnings=warnings or [],
        results=results,
    )


@router.post("", response_model=RecommendationRunOut)
def create_recommendations(
    student_id: int,
    body: RecommendRequest,
    db: Session = Depends(get_db),
    client: OpenAlexClient = Depends(get_openalex_client),
    embedder: Embedder = Depends(get_embedder),
    user: User = Depends(get_current_user),
):
    settings = get_settings()
    student = get_student_or_404(db, student_id, user)
    if not student.interests:
        raise HTTPException(400, "Add at least one research interest to your profile first.")

    unis = select_universities(body.countries, body.university_keys)
    if not unis:
        raise HTTPException(400, "No supported universities match the selected countries/universities.")
    if len(unis) > settings.max_universities_per_run:
        raise HTTPException(
            400,
            f"Please select at most {settings.max_universities_per_run} universities per search "
            f"(you selected {len(unis)}).",
        )

    queries = student.interests[:3]
    warnings: list[str] = []
    professors: list[Professor] = []
    for uni in unis:
        try:
            found = discover_professors(
                db,
                client,
                uni,
                queries,
                from_year=settings.openalex_from_year,
                max_candidates=settings.max_candidates_per_university,
                min_works=settings.min_author_works,
                cache_ttl_days=settings.cache_ttl_days,
            )
        except OpenAlexError as exc:
            log.warning("OpenAlex failed for %s: %s", uni.name, exc)
            warnings.append(f"{uni.name}: {exc}")
            continue
        if not found:
            warnings.append(f"{uni.name}: no matching researchers found.")
        professors.extend(found)

    if not professors:
        status = 502 if len(warnings) == len(unis) and any("OpenAlex" in w for w in warnings) else 404
        raise HTTPException(status, "No candidate professors found. " + " ".join(warnings))

    docs = [build_professor_doc(p.id, p.topics, p.publications) for p in professors]
    student_text = build_student_text(student.interests, student.skills, student.research_experience)
    matches = rank_professors(student_text, docs, embedder, settings.hybrid_alpha, body.top_k)

    run = RecommendationRun(
        student_id=student.id,
        params={"countries": body.countries, "university_keys": [u.key for u in unis], "top_k": body.top_k},
        backend=embedder.name,
        alpha=settings.hybrid_alpha,
    )
    db.add(run)
    db.flush()

    existing = {
        o.professor_id for o in db.scalars(select(Outreach).where(Outreach.student_id == student.id))
    }
    for rank, m in enumerate(matches, start=1):
        db.add(
            Recommendation(
                run_id=run.id,
                student_id=student.id,
                professor_id=m.professor_id,
                rank=rank,
                score=m.score,
                semantic_score=m.semantic,
                lexical_score=m.lexical,
                explanation={
                    "summary": m.summary,
                    "matched_topics": m.matched_topics,
                    "shared_terms": m.shared_terms,
                    "evidence_papers": m.evidence_papers,
                },
            )
        )
        if m.professor_id not in existing:
            db.add(Outreach(student_id=student.id, professor_id=m.professor_id))
    db.commit()
    db.refresh(run)
    return _run_out(db, run, warnings)


@router.get("", response_model=RecommendationRunOut)
def latest_recommendations(student_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_student_or_404(db, student_id, user)
    run = db.scalars(
        select(RecommendationRun)
        .where(RecommendationRun.student_id == student_id)
        .order_by(RecommendationRun.id.desc())
    ).first()
    if not run:
        raise HTTPException(404, "No recommendations yet.")
    return _run_out(db, run)
