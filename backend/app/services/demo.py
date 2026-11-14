"""Offline demo dataset: seed the database from ``data/raw/*.csv`` and rank locally.

Why this exists
---------------
The matching pipeline (discovery -> hybrid scorer -> explanations) is the part worth
demonstrating. A live OpenAlex search needs a free API key and network access, which is
a bad thing to depend on during a presentation. This module loads the 64 professors and
306 publications that were exported from OpenAlex into the local database and lets the
normal pipeline run against them, so the app is fully usable with zero credentials.

The seed is idempotent: re-running it only inserts professors/publications that are
missing and never duplicates rows.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Professor, Publication
from .universities import load_universities

log = logging.getLogger(__name__)

DEMO_SOURCE = "demo-dataset"
REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass
class SeedReport:
    professors_inserted: int = 0
    professors_skipped: int = 0
    publications_inserted: int = 0
    unknown_universities: tuple[str, ...] = ()
    source_files: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "professors_inserted": self.professors_inserted,
            "professors_skipped": self.professors_skipped,
            "publications_inserted": self.publications_inserted,
            "unknown_universities": list(self.unknown_universities),
            "source_files": list(self.source_files),
        }


def _split(value: str | None, separator: str = ";") -> list[str]:
    return [part.strip() for part in (value or "").split(separator) if part.strip()]


def demo_data_dir(override: str | None = None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    return REPO_ROOT / "data" / "raw"


def load_publication_rows(path: Path) -> dict[str, list[dict]]:
    """Group the publications CSV rows by professor id."""
    grouped: dict[str, list[dict]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            professor_id = (row.get("professor_id") or "").strip()
            if not professor_id:
                continue
            year = (row.get("publication_year") or "").strip()
            grouped.setdefault(professor_id, []).append(
                {
                    "work_id": (row.get("publication_id") or "").strip() or "unknown",
                    "title": (row.get("title") or "").strip() or "(untitled)",
                    "abstract": (row.get("abstract") or "").strip() or None,
                    "year": int(year) if year.isdigit() else None,
                    "doi": (row.get("doi") or "").strip() or None,
                    "keywords": _split(row.get("keywords")),
                }
            )
    return grouped


def seed_demo_dataset(db: Session, data_dir: Path | None = None) -> SeedReport:
    """Insert the sample dataset. Safe to call on every start-up."""
    data_dir = data_dir or demo_data_dir()
    professors_csv = data_dir / "professors.csv"
    publications_csv = data_dir / "publications.csv"
    report = SeedReport()
    if not professors_csv.exists():
        log.warning("demo dataset not found at %s", professors_csv)
        return report

    universities = load_universities()
    publications_by_professor = (
        load_publication_rows(publications_csv) if publications_csv.exists() else {}
    )

    existing = set(db.scalars(select(Professor.id)))
    unknown: set[str] = set()

    with professors_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            professor_id = (row.get("professor_id") or "").strip()
            university_key = (row.get("university_id") or "").strip()
            if not professor_id or not university_key:
                continue
            if professor_id in existing:
                report.professors_skipped += 1
                continue
            university = universities.get(university_key)
            if not university:
                unknown.add(university_key)
                report.professors_skipped += 1
                continue

            papers = publications_by_professor.get(professor_id, [])
            db.add(
                Professor(
                    id=professor_id,
                    name=(row.get("full_name") or "Unknown researcher").strip(),
                    university_key=university_key,
                    country_code=(row.get("country") or university.country_code).strip()[:2],
                    institution_name=university.name,
                    works_count=len(papers),
                    cited_by_count=0,
                    topics=_split(row.get("research_interests")),
                    openalex_url=(row.get("academic_profile_url") or "").strip()
                    or f"https://openalex.org/{professor_id}",
                    data_source=DEMO_SOURCE,
                )
            )
            for paper in papers:
                db.add(Publication(professor_id=professor_id, **paper))
                report.publications_inserted += 1
            report.professors_inserted += 1
            existing.add(professor_id)

    db.commit()
    report.unknown_universities = tuple(sorted(unknown))
    report.source_files = tuple(str(p) for p in (professors_csv, publications_csv) if p.exists())
    log.info(
        "demo dataset seeded: %s professors, %s publications",
        report.professors_inserted,
        report.publications_inserted,
    )
    return report


# --------------------------------------------------------------------------- local ranking
def professor_search_text(professor: Professor) -> str:
    parts = [professor.name, " ".join(professor.topics or [])]
    for paper in professor.publications or []:
        parts.append(paper.title or "")
        parts.append(" ".join(paper.keywords or []))
    return " ".join(parts).lower()


def local_candidates(
    db: Session,
    university_key: str,
    queries: list[str],
    *,
    limit: int = 40,
) -> list[Professor]:
    """Pick demo-dataset candidates for one university using keyword overlap."""
    professors = list(
        db.scalars(select(Professor).where(Professor.university_key == university_key))
    )
    if not professors:
        return []

    terms = [q.lower().strip() for q in queries if q and q.strip()]
    scored: list[tuple[float, Professor]] = []
    for professor in professors:
        text = professor_search_text(professor)
        hits = sum(text.count(term) for term in terms)
        # tiny recency/volume tie-breaker so equal keyword overlap stays stable
        newest = max((p.year or 0) for p in professor.publications or []) or 0
        score = hits * 100 + newest / 10000 + len(professor.publications or []) / 1000
        scored.append((score, professor))

    scored.sort(key=lambda pair: (-pair[0], pair[1].name))
    with_signal = [pair for pair in scored if pair[0] >= 100]
    return [professor for _, professor in (with_signal or scored)[:limit]]


def dataset_coverage(db: Session) -> dict[str, dict[str, int]]:
    """How many demo professors/publications exist per university key."""
    professors = dict(
        db.execute(select(Professor.university_key, func.count(Professor.id)).group_by(Professor.university_key)).all()
    )
    publications = dict(
        db.execute(
            select(Professor.university_key, func.count(Publication.id))
            .join(Professor, Professor.id == Publication.professor_id)
            .group_by(Professor.university_key)
        ).all()
    )
    return {
        key: {"professors": professors.get(key, 0), "publications": publications.get(key, 0)}
        for key in professors
    }
