from functools import lru_cache

from .config import get_settings
from .services.matcher import Embedder, make_embedder
from .services.openalex import OpenAlexClient


@lru_cache
def _embedder(backend: str, model: str) -> Embedder:
    return make_embedder(backend, model)


def get_embedder() -> Embedder:
    s = get_settings()
    return _embedder(s.embedding_backend, s.sbert_model)


@lru_cache
def _client(api_key: str | None, base_url: str) -> OpenAlexClient:
    return OpenAlexClient(api_key=api_key, base_url=base_url)


def get_openalex_client() -> OpenAlexClient:
    s = get_settings()
    return _client(s.openalex_api_key, s.openalex_base_url)
