"""Meta endpoints: what the app is, what is inside the database, and which keys are set."""

from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import func, inspect, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .. import __version__
from ..config import get_settings
from ..db import engine, get_db
from ..auth import get_current_user
from ..models import Outreach, Professor, Publication, Recommendation, RecommendationRun, Student, User
from ..schemas import IntegrationStatus, MetaStatsOut, TableStat
from ..services.demo import DEMO_SOURCE, dataset_coverage, demo_data_dir, seed_demo_dataset

router = APIRouter(prefix="/api/meta", tags=["meta"])

_TABLES = {
    "users": User,
    "students": Student,
    "professors": Professor,
    "publications": Publication,
    "recommendation_runs": RecommendationRun,
    "recommendations": Recommendation,
    "outreach": Outreach,
}


def _mask(url: str) -> str:
    """Hide credentials before showing the connection string in the UI."""
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    if "@" in rest:
        credentials, host = rest.rsplit("@", 1)
        user = credentials.split(":", 1)[0]
        return f"{scheme}://{user}:***@{host}"
    return url


def integrations() -> list[IntegrationStatus]:
    settings = get_settings()
    return [
        IntegrationStatus(
            key="openalex",
            name="OpenAlex API",
            required=True,
            configured=bool(settings.openalex_api_key),
            purpose="Live discovery of professors and their recent publications for any university.",
            signup_url="https://openalex.org/settings/api",
            env_var="OPENALEX_API_KEY",
            docs_hint="Free. Register, open Settings → API key, copy it into backend/.env.",
        ),
        IntegrationStatus(
            key="llm",
            name="LLM for AI email drafts (optional)",
            required=False,
            configured=bool(settings.llm_api_key),
            purpose="Writes a personalised outreach email instead of the built-in template.",
            signup_url="https://platform.openai.com/api-keys",
            env_var="LLM_API_KEY",
            docs_hint="Any OpenAI-compatible API works: OpenAI, DeepSeek, OpenRouter, Groq or local Ollama.",
        ),
        IntegrationStatus(
            key="smtp",
            name="SMTP for password reset (optional)",
            required=False,
            configured=bool(settings.smtp_host and settings.smtp_from),
            purpose="Delivers password-reset links by email.",
            signup_url="https://ethereal.email/",
            env_var="SMTP_HOST / SMTP_FROM",
            docs_hint="Any mailbox works; for a demo, Ethereal gives a free throw-away SMTP inbox.",
        ),
        IntegrationStatus(
            key="sbert",
            name="Sentence-Transformers embeddings (optional)",
            required=False,
            configured=settings.embedding_backend == "sbert",
            purpose="Switches the semantic scorer from the offline TF-IDF baseline to a transformer model.",
            signup_url="https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2",
            env_var="EMBEDDING_BACKEND=sbert",
            docs_hint="No key needed: pip install -r requirements-sbert.txt and flip the setting.",
        ),
    ]


@router.get("/integrations", response_model=list[IntegrationStatus])
def get_integrations() -> list[IntegrationStatus]:
    return integrations()


@router.post("/seed")
def seed(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """(Re)load the bundled demo dataset. Idempotent: existing rows are skipped."""
    settings = get_settings()
    report = seed_demo_dataset(db, demo_data_dir(settings.demo_data_dir or None))
    return report.as_dict()


@router.get("/stats", response_model=MetaStatsOut)
def stats(db: Session = Depends(get_db)) -> MetaStatsOut:
    settings = get_settings()
    target: Engine = db.get_bind()
    table_names = set(inspect(target).get_table_names())

    tables: list[TableStat] = []
    counts: dict[str, int] = {}
    for name, model in _TABLES.items():
        if name not in table_names:
            continue
        rows = int(db.scalar(select(func.count()).select_from(model)) or 0)
        tables.append(TableStat(table=name, rows=rows))
        counts[name] = rows

    demo_professors = int(
        db.scalar(
            select(func.count()).select_from(Professor).where(Professor.data_source == DEMO_SOURCE)
        )
        or 0
    )
    coverage = dataset_coverage(db)
    data_dir = demo_data_dir(settings.demo_data_dir or None)

    return MetaStatsOut(
        app_version=__version__,
        database_dialect=target.dialect.name,
        database_url=_mask(str(target.url)),
        tables=sorted(tables, key=lambda t: -t.rows),
        counts=counts,
        demo_mode=settings.demo_mode,
        demo_seeded=demo_professors > 0,
        demo_data_dir=str(Path(data_dir)),
        dataset_coverage=coverage,
        integrations=integrations(),
    )
