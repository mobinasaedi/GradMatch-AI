"""Professor discovery: OpenAlex -> candidate professors + recent publications (cached in the DB)."""

import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import InstitutionCache, Professor, Publication, SearchCache, as_utc, utcnow
from .openalex import OpenAlexClient, reconstruct_abstract, short_id
from .universities import University

log = logging.getLogger(__name__)

# In CS/ML the last author is usually the PI; first authors are mostly students.
POSITION_WEIGHT = {"last": 1.0, "middle": 0.6, "first": 0.4}
MAX_PAPERS_PER_PROFESSOR = 8


def _is_fresh(dt, ttl_days: int) -> bool:
    dt = as_utc(dt)
    return dt is not None and utcnow() - dt < timedelta(days=ttl_days)


def resolve_institution_id(db: Session, client: OpenAlexClient, uni: University) -> str | None:
    if uni.openalex_id:
        return uni.openalex_id
    cached = db.get(InstitutionCache, uni.key)
    if cached:
        return cached.openalex_id
    found = client.find_institution(uni.name, uni.country_code)
    if not found:
        return None
    inst_id = short_id(found["id"])
    db.add(InstitutionCache(university_key=uni.key, openalex_id=inst_id, display_name=found["display_name"]))
    db.commit()
    return inst_id


def _belongs_to(authorship: dict, institution_id: str) -> bool:
    for inst in authorship.get("institutions", []) or []:
        if short_id(inst.get("id")) == institution_id:
            return True
        if institution_id in [short_id(x) for x in inst.get("lineage", []) or []]:
            return True
    return False


def _parse_work(work: dict) -> dict:
    return {
        "work_id": short_id(work["id"]),
        "title": work.get("title") or "(untitled)",
        "abstract": reconstruct_abstract(work.get("abstract_inverted_index")),
        "year": work.get("publication_year"),
        "doi": work.get("doi"),
        "keywords": [k.get("display_name") for k in work.get("keywords", []) or [] if k.get("display_name")],
    }


def _score_authors(works: list[dict], institution_id: str) -> dict[str, float]:
    scores: dict[str, float] = {}
    for work in works:
        for a in work.get("authorships", []) or []:
            if not _belongs_to(a, institution_id):
                continue
            aid = short_id((a.get("author") or {}).get("id"))
            if aid:
                scores[aid] = scores.get(aid, 0.0) + POSITION_WEIGHT.get(a.get("author_position"), 0.5)
    return scores


def _store_work(db: Session, professor_id: str, parsed: dict) -> None:
    exists = db.scalar(
        select(Publication.id).where(
            Publication.work_id == parsed["work_id"], Publication.professor_id == professor_id
        )
    )
    if not exists:
        db.add(Publication(professor_id=professor_id, **parsed))
        db.flush()  # autoflush is off; make the row visible to the next duplicate check


def discover_professors(
    db: Session,
    client: OpenAlexClient,
    uni: University,
    queries: list[str],
    *,
    from_year: int,
    max_candidates: int,
    min_works: int,
    cache_ttl_days: int,
) -> list[Professor]:
    """Return candidate professors for one university, fetching/caching as needed."""
    institution_id = resolve_institution_id(db, client, uni)
    if not institution_id:
        log.warning("Could not resolve OpenAlex institution for %s", uni.name)
        return []

    # 1) which authors are active on the student's topics at this institution?
    author_scores: dict[str, float] = {}
    fresh_works_by_author: dict[str, list[dict]] = {}
    for query in queries:
        key = f"authors:{institution_id}:{from_year}:{query.lower()}"
        cached = db.get(SearchCache, key)
        if cached and _is_fresh(cached.fetched_at, cache_ttl_days):
            for aid, score in cached.payload:
                author_scores[aid] = author_scores.get(aid, 0.0) + score
            continue

        works = client.search_works(institution_id, query, from_year)
        scores = _score_authors(works, institution_id)
        for aid, score in scores.items():
            author_scores[aid] = author_scores.get(aid, 0.0) + score
        for work in works:
            parsed = _parse_work(work)
            for a in work.get("authorships", []) or []:
                aid = short_id((a.get("author") or {}).get("id"))
                if aid in scores:
                    fresh_works_by_author.setdefault(aid, []).append(parsed)
        payload = [[aid, s] for aid, s in scores.items()]
        existing = db.get(SearchCache, key)
        if existing:
            existing.payload, existing.fetched_at = payload, utcnow()
        else:
            db.add(SearchCache(key=key, payload=payload))
        db.commit()

    top_ids = [aid for aid, _ in sorted(author_scores.items(), key=lambda kv: -kv[1])[:max_candidates]]
    if not top_ids:
        return []

    # 2) load known professors, fetch the missing/stale ones
    known = {p.id: p for p in db.scalars(select(Professor).where(Professor.id.in_(top_ids)))}
    to_fetch = [aid for aid in top_ids if aid not in known or not _is_fresh(known[aid].fetched_at, cache_ttl_days)]

    if to_fetch:
        accepted: list[str] = []
        for author in client.get_authors(to_fetch):
            aid = short_id(author["id"])
            inst_ids = [short_id(i.get("id")) for i in author.get("last_known_institutions", []) or []]
            if institution_id not in inst_ids or (author.get("works_count") or 0) < min_works:
                continue  # unverifiable affiliation or too junior/sparse to be a likely supervisor
            topics = [t["display_name"] for t in (author.get("topics") or [])[:8] if t.get("display_name")]
            prof = known.get(aid) or Professor(id=aid, university_key=uni.key)
            prof.name = author["display_name"]
            prof.country_code = uni.country_code
            prof.institution_name = uni.name
            prof.works_count = author.get("works_count") or 0
            prof.cited_by_count = author.get("cited_by_count") or 0
            prof.topics = topics
            prof.openalex_url = f"https://openalex.org/{aid}"
            prof.fetched_at = utcnow()
            db.merge(prof)
            accepted.append(aid)
        db.commit()

        # publications: topic-matched works we already have + each author's most recent works
        if accepted:
            for aid, works in fresh_works_by_author.items():
                if aid in accepted:
                    for parsed in works:
                        _store_work(db, aid, parsed)
            db.commit()
            accepted_set = set(accepted)
            for work in client.recent_works_by_authors(accepted, from_year):
                parsed = _parse_work(work)
                for a in work.get("authorships", []) or []:
                    aid = short_id((a.get("author") or {}).get("id"))
                    if aid in accepted_set:
                        _store_work(db, aid, parsed)
            db.commit()

    professors = list(db.scalars(select(Professor).where(Professor.id.in_(top_ids), Professor.university_key == uni.key)))
    return [p for p in professors if p.publications]
