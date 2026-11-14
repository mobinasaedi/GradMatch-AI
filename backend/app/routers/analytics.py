"""Analytics for the presenter dashboard: aggregates over the latest search run and outreach."""

from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..auth import get_current_user
from ..models import Outreach, OutreachEvent, RecommendationRun, Student, User, as_utc, utcnow
from ..schemas import (
    ActivityPoint,
    LabelCount,
    OutreachStatus,
    RunSummaryOut,
    StudentOverviewOut,
)
from ..services.scoring import fit_values
from .students import get_student_or_404

router = APIRouter(prefix="/api/students/{student_id}", tags=["analytics"])

SCORE_BUCKETS: list[tuple[str, float, float]] = [
    ("under 50", 0, 50),
    ("50–65", 50, 65),
    ("65–80", 65, 80),
    ("80+", 80, 100.0001),
]


def _latest_run(db: Session, student_id: int) -> RecommendationRun | None:
    return db.scalars(
        select(RecommendationRun)
        .where(RecommendationRun.student_id == student_id)
        .order_by(RecommendationRun.id.desc())
    ).first()


@router.get("/runs", response_model=list[RunSummaryOut])
def list_runs(student_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_student_or_404(db, student_id, user)
    runs = db.scalars(
        select(RecommendationRun)
        .where(RecommendationRun.student_id == student_id)
        .order_by(RecommendationRun.id.desc())
        .limit(20)
    ).all()
    out: list[RunSummaryOut] = []
    for run in runs:
        scores = [rec.score for rec in run.recommendations]
        fits = fit_values(scores)
        params = run.params or {}
        out.append(
            RunSummaryOut(
                run_id=run.id,
                created_at=run.created_at,
                backend=run.backend,
                data_source=str(params.get("data_source", "openalex")),
                results_count=len(scores),
                avg_score=round(sum(scores) / len(scores), 1) if scores else 0.0,
                best_score=round(max(scores), 1) if scores else 0.0,
                avg_fit=round(sum(fits) / len(fits), 1) if fits else 0.0,
                best_fit=round(max(fits), 1) if fits else 0.0,
                university_names=list(params.get("university_names") or []),
                top_k=int(params.get("top_k", 10)),
            )
        )
    return out


@router.get("/overview", response_model=StudentOverviewOut)
def overview(student_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    student = get_student_or_404(db, student_id, user)

    run = _latest_run(db, student_id)
    recs = list(run.recommendations) if run else []
    scores = [rec.score for rec in recs]
    fits = fit_values(scores)

    outreach_rows = list(db.scalars(select(Outreach).where(Outreach.student_id == student_id)))
    statuses = Counter(row.status for row in outreach_rows)
    funnel = {status.value: statuses.get(status.value, 0) for status in OutreachStatus}

    contacted = sum(funnel[s] for s in ("sent", "replied", "follow_up_needed", "closed"))
    replies = funnel["replied"]
    reply_rate = round(replies / contacted * 100, 1) if contacted else 0.0

    score_buckets = [
        LabelCount(label=label, count=sum(1 for f in fits if low <= f < high))
        for label, low, high in SCORE_BUCKETS
    ]

    topic_counter: Counter[str] = Counter()
    university_counter: Counter[str] = Counter()
    for rec in recs:
        for topic in (rec.explanation or {}).get("matched_topics", []) or []:
            topic_counter[topic] += 1
        if rec.professor:
            university_counter[rec.professor.institution_name] += 1

    # 14-day activity from the outreach event log
    today = utcnow().date()
    start = today - timedelta(days=13)
    events = list(
        db.scalars(
            select(OutreachEvent)
            .join(Outreach, Outreach.id == OutreachEvent.outreach_id)
            .where(Outreach.student_id == student_id)
        )
    )
    per_day: dict[str, dict[str, int]] = {
        (start + timedelta(days=i)).isoformat(): {"events": 0, "replies": 0} for i in range(14)
    }
    for event in events:
        created = as_utc(event.created_at)
        if not created:
            continue
        key = created.date().isoformat()
        if key not in per_day:
            continue
        per_day[key]["events"] += 1
        if event.status == OutreachStatus.replied.value:
            per_day[key]["replies"] += 1
    activity = [ActivityPoint(date=day, **counts) for day, counts in sorted(per_day.items())]

    filled = [
        bool(student.name),
        bool(student.field),
        bool(student.gpa),
        bool(student.interests),
        bool(student.skills),
        bool((student.research_experience or "").strip()),
    ]

    return StudentOverviewOut(
        matches=len(recs),
        avg_fit=round(sum(fits) / len(fits), 1) if fits else 0.0,
        best_fit=round(max(fits), 1) if fits else 0.0,
        runs=int(db.query(RecommendationRun).filter(RecommendationRun.student_id == student_id).count()),
        contacted=contacted,
        replies=replies,
        reply_rate=reply_rate,
        funnel=funnel,
        score_buckets=score_buckets,
        top_topics=[LabelCount(label=k, count=v) for k, v in topic_counter.most_common(6)],
        universities=[LabelCount(label=k, count=v) for k, v in university_counter.most_common(6)],
        activity=activity,
        profile_completeness=round(sum(1 for f in filled if f) / len(filled) * 100),
        latest_run_at=run.created_at if run else None,
    )
