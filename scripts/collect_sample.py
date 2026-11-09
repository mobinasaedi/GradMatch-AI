"""Sprint-1 data collection: export a small real sample of candidate professors + papers to CSV.

Follows the research schema in research/dataset_schema.md (professors.csv / publications.csv).
Needs OPENALEX_API_KEY. Each run costs OpenAlex credits, results are cached in the local DB.

    cd backend
    python ../scripts/collect_sample.py --universities uoft tum uva \
        --topics "natural language processing" "large language models" "machine learning"
"""

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.services.discovery import discover_professors  # noqa: E402
from app.services.openalex import OpenAlexClient  # noqa: E402
from app.services.universities import load_universities  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universities", nargs="+", default=["uoft", "tum", "uva"])
    parser.add_argument("--topics", nargs="+", default=["natural language processing", "machine learning"])
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "raw")
    args = parser.parse_args()

    settings = get_settings()
    client = OpenAlexClient(api_key=settings.openalex_api_key, base_url=settings.openalex_base_url)
    unis = load_universities()
    init_db()
    args.out.mkdir(parents=True, exist_ok=True)

    prof_rows, pub_rows = [], []
    with SessionLocal() as db:
        for key in args.universities:
            uni = unis[key]
            found = discover_professors(
                db, client, uni, args.topics,
                from_year=settings.openalex_from_year,
                max_candidates=settings.max_candidates_per_university,
                min_works=settings.min_author_works,
                cache_ttl_days=settings.cache_ttl_days,
            )
            print(f"{uni.name}: {len(found)} candidate professors")
            for p in found:
                pubs = sorted(p.publications, key=lambda x: x.year or 0, reverse=True)[:5]
                prof_rows.append({
                    "professor_id": p.id, "full_name": p.name, "university_id": uni.key,
                    "country": uni.country_code, "department": "",  # needs official-site verification
                    "research_interests": "; ".join(p.topics),
                    "recent_publications": "; ".join(x.work_id for x in pubs),
                    "academic_profile_url": p.openalex_url, "contact_email": p.email or "",
                    "email_verified": bool(p.email), "data_source": "OpenAlex",
                    "collected_at": date.today().isoformat(),
                })
                for x in pubs:
                    pub_rows.append({
                        "publication_id": x.work_id, "professor_id": p.id, "title": x.title,
                        "abstract": x.abstract or "", "publication_year": x.year, "doi": x.doi or "",
                        "keywords": "; ".join(x.keywords or []), "source": "OpenAlex",
                    })

    for name, rows in (("professors.csv", prof_rows), ("publications.csv", pub_rows)):
        if not rows:
            continue
        with open(args.out / name, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {args.out / name} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
