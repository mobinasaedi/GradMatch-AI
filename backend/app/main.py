from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import __version__
from .routers import auth
from .config import get_settings
from .db import SessionLocal, engine, get_db, init_db
from .models import Professor, Publication
from .routers import analytics, meta, outreach, professors, recommendations, students, universities
from .services.demo import demo_data_dir, seed_demo_dataset


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    settings = get_settings()
    if settings.auto_seed_demo:
        with SessionLocal() as db:
            has_professors = db.scalar(select(func.count()).select_from(Professor)) or 0
            if not has_professors:
                # First start: load the bundled dataset so the app is usable without any key.
                seed_demo_dataset(db, demo_data_dir(settings.demo_data_dir or None))
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="GradMatch AI",
        version=__version__,
        description="Resume-based academic supervisor recommendation and email tracking.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["meta"])
    def health(db: Session = Depends(get_db)):
        professors_indexed = db.scalar(select(func.count()).select_from(Professor)) or 0
        publications_indexed = db.scalar(select(func.count()).select_from(Publication)) or 0
        return {
            "status": "ok",
            "version": __version__,
            "embedding_backend": settings.embedding_backend,
            "openalex_key_configured": bool(settings.openalex_api_key),
            "llm_configured": bool(settings.llm_api_key),
            "database": engine.dialect.name,
            "demo_mode": settings.demo_mode,
            "professors_indexed": professors_indexed,
            "publications_indexed": publications_indexed,
        }

    app.include_router(auth.router)
    for module in (meta, students, universities, analytics, recommendations, professors, outreach):
        app.include_router(module.router)
    return app


app = create_app()
