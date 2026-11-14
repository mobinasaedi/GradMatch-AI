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
from ..services.demo import DEMO_SOURCE, local_candidates
from ..services.discovery import discover_professors
from ..services.matcher import Embedder, build_professor_doc, build_student_text, rank_professors
from ..services.openalex import OpenAlexClient, OpenAlexError
from ..services.scoring import fit_values
from ..services.universities import select_universities, load_universities
from .students import get_student_or_404

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/students/{student_id}/recommendations", tags=["recommendations"])


def _fit_values(values: list[float]) -> list[float]:
    return fit_values(values)


def _run_out(db: Session, run: RecommendationRun, warnings: list[str] | None = None) -> RecommendationRunOut:
    outreach = {
        o.professor_id: o
        for o in db.scalars(select(Outreach).where(Outreach.student_id == run.student_id))
    }
    recs = list(run.recommendations)
    fits = _fit_values([rec.score for rec in recs])
    sem_fits = _fit_values([rec.semantic_score for rec in recs])
    lex_fits = _fit_values([rec.lexical_score for rec in recs])

    results = []
    for index, rec in enumerate(recs):
        o = outreach.get(rec.professor_id)
        results.append(
            RecommendationOut(
                rank=rec.rank,
                score=rec.score,
                semantic_score=rec.semantic_score,
                lexical_score=rec.lexical_score,
                fit=fits[index],
                fit_semantic=sem_fits[index],
                fit_lexical=lex_fits[index],
                professor=ProfessorOut.model_validate(rec.professor),
                explanation=ExplanationOut(**rec.explanation),
                outreach_id=o.id if o else None,
                outreach_status=o.status if o else None,
            )
        )

    params = run.params or {}
    return RecommendationRunOut(
        run_id=run.id,
        student_id=run.student_id,
        backend=run.backend,
        data_source=str(params.get("data_source", "openalex")),
        created_at=run.created_at,
        params=params,
        warnings=warnings or [],
        results=results,
    )


def _demo_candidates(db: Session, uni_key: str, queries: list[str], limit: int) -> list[Professor]:
    candidates = local_candidates(db, uni_key, queries, limit=limit)
    return [p for p in candidates if p.publications]


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
    sources: set[str] = set()

    # Preferred source: live OpenAlex. Without a key (or when the API fails and demo mode is
    # on) the very same pipeline runs on the bundled dataset, so a live demo never dies.
    for uni in unis:
        found: list[Professor] = []
        if settings.openalex_api_key:
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
                if found:
                    sources.add("openalex")
            except OpenAlexError as exc:
                log.warning("OpenAlex failed for %s: %s", uni.name, exc)
                warnings.append(f"{uni.name}: {exc}")
                if settings.demo_mode:
                    found = _demo_candidates(db, uni.key, queries, settings.demo_max_candidates)
                    if found:
                        sources.add(DEMO_SOURCE)
                        warnings.append(
                            f"{uni.name}: served from the bundled demo dataset instead "
                            f"({len(found)} candidates)."
                        )
        else:
            if settings.demo_mode:
                found = _demo_candidates(db, uni.key, queries, settings.demo_max_candidates)
                if found:
                    sources.add(DEMO_SOURCE)
            if not found:
                # No key and nothing local: still try the API, which may sit behind a proxy.
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
                    if found:
                        sources.add("openalex")
                except OpenAlexError as exc:
                    log.warning("OpenAlex failed for %s: %s", uni.name, exc)
                    warnings.append(f"{uni.name}: {exc}")
        if not found:
            warnings.append(
                f"{uni.name}: no matching researchers found "
                f"(the bundled demo dataset covers Toronto, Amsterdam and TU Munich)."
            )
        professors.extend(found)

    data_source = DEMO_SOURCE if sources == {DEMO_SOURCE} else ("openalex" if sources else "none")

    if not professors:
        if not settings.openalex_api_key:
            raise HTTPException(
                404,
                "No local candidates for the selected universities. The bundled dataset covers "
                "Toronto, Amsterdam and TU Munich; add a free OPENALEX_API_KEY to search every "
                "university live.",
            )
        status = 502 if len(warnings) == len(unis) and any("OpenAlex" in w for w in warnings) else 404
        raise HTTPException(status, "No candidate professors found. " + " ".join(warnings))
    # de-duplicate: the same researcher can surface through more than one selected university
    seen: set[str] = set()
    unique: list[Professor] = []
    for professor in professors:
        if professor.id not in seen:
            seen.add(professor.id)
            unique.append(professor)
    professors = unique

    docs = [build_professor_doc(p.id, p.topics, p.publications) for p in professors]
    student_text = build_student_text(student.interests, student.skills, student.research_experience)
    matches = rank_professors(student_text, docs, embedder, settings.hybrid_alpha, body.top_k)

    if data_source == DEMO_SOURCE:
        warnings.insert(
            0,
            "Offline demo mode: candidates come from the bundled Toronto / Amsterdam / TU Munich "
            "dataset. Add a free OpenAlex API key for live, any-university search.",
        )

    uni_names = {u.key: u.name for u in load_universities().values()}
    run = RecommendationRun(
        student_id=student.id,
        params={
            "countries": body.countries,
            "university_keys": [u.key for u in unis],
            "university_names": [uni_names.get(u.key, u.key) for u in unis],
            "top_k": body.top_k,
            "data_source": data_source,
        },
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


@router.get("/{run_id}", response_model=RecommendationRunOut)
def get_run(student_id: int, run_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Re-open an older search from the run history."""
    get_student_or_404(db, student_id, user)
    run = db.get(RecommendationRun, run_id)
    if not run or run.student_id != student_id:
        raise HTTPException(404, "Search not found.")
    return _run_out(db, run)
