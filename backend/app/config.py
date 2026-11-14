from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str = "local-development-only-change-this-secret-key-before-deployment"
    cookie_secure: bool = False
    public_app_url: str = "http://localhost:5173"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_starttls: bool = True

    # Database: PostgreSQL in production/docker, SQLite is fine for local dev.
    database_url: str = "sqlite:///./gradmatch.db"

    # OpenAlex now expects a free API key (https://openalex.org/settings/api).
    openalex_api_key: str | None = None
    openalex_base_url: str = "https://api.openalex.org"
    # Only publications from this year onwards are used for matching.
    openalex_from_year: int = 2021

    # ------------------------------------------------------------------ demo / offline mode
    # When no OpenAlex key is configured, the app still works end to end:
    # candidates are ranked from the professors/publications shipped in data/raw.
    demo_mode: bool = True
    auto_seed_demo: bool = True
    demo_data_dir: str = ""  # empty -> <repo>/data/raw
    demo_max_candidates: int = 40

    # ------------------------------------------- optional LLM for AI email drafts
    # Any OpenAI-compatible endpoint works (OpenAI, DeepSeek, OpenRouter, Groq, Ollama).
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 45.0

    # "tfidf" (offline baseline, no model download) or "sbert" (Sentence Transformers).
    embedding_backend: str = "tfidf"
    sbert_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    # Weight of the semantic score in the hybrid score (the rest is TF-IDF/lexical).
    hybrid_alpha: float = 0.6

    # Limits that protect the (free) OpenAlex credit budget and the server.
    max_universities_per_run: int = 5
    max_candidates_per_university: int = 25
    min_author_works: int = 10
    cache_ttl_days: int = 7
    upload_max_mb: int = 5

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
