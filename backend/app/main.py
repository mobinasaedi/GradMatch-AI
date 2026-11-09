from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .routers import auth
from .config import get_settings
from .db import init_db
from .routers import outreach, professors, recommendations, students, universities


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="GradMatch AI",
        version=__version__,
        description="Resume-based academic supervisor recommendation and email tracking (MVP).",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["meta"])
    def health():
        return {
            "status": "ok",
            "version": __version__,
            "embedding_backend": settings.embedding_backend,
            "openalex_key_configured": bool(settings.openalex_api_key),
        }

    app.include_router(auth.router)
    for module in (students, universities, recommendations, professors, outreach):
        app.include_router(module.router)
    return app


app = create_app()
