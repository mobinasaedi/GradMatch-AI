"""Thin OpenAlex client (httpx).

Notes
- OpenAlex requires a free API key for real use (`api_key` query parameter).
- List requests cost credits, so everything above this layer caches aggressively.
- `page size` is capped at 100 by the API.
"""

import time
from collections.abc import Callable, Iterable

import httpx

WORK_SELECT = "id,title,publication_year,doi,authorships,abstract_inverted_index,keywords"
AUTHOR_SELECT = "id,display_name,works_count,cited_by_count,last_known_institutions,topics"


class OpenAlexError(RuntimeError):
    pass


def short_id(openalex_url: str | None) -> str | None:
    if not openalex_url:
        return None
    return openalex_url.rstrip("/").rsplit("/", 1)[-1]


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    if not inverted_index:
        return None
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted_index.items():
        positions.extend((i, word) for i in idxs)
    return " ".join(w for _, w in sorted(positions)) or None


def chunks(items: list, size: int) -> Iterable[list]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


class OpenAlexClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.openalex.org",
        http: httpx.Client | None = None,
        max_retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.http = http or httpx.Client(timeout=30)
        self.max_retries = max_retries
        self._sleep = sleep

    # ------------------------------------------------------------------ core
    def _get(self, path: str, params: dict) -> dict:
        params = dict(params)
        if self.api_key:
            params["api_key"] = self.api_key
        url = f"{self.base_url}{path}"

        for attempt in range(self.max_retries + 1):
            try:
                resp = self.http.get(url, params=params)
            except httpx.TransportError as exc:
                if attempt == self.max_retries:
                    raise OpenAlexError(f"Network error talking to OpenAlex: {exc}") from exc
                self._sleep(2**attempt)
                continue

            if resp.status_code in (429, 500, 502, 503, 504):
                if attempt == self.max_retries:
                    raise OpenAlexError(f"OpenAlex unavailable (HTTP {resp.status_code}).")
                retry_after = resp.headers.get("Retry-After")
                self._sleep(float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt)
                continue
            if resp.status_code in (401, 403, 409):
                raise OpenAlexError(
                    "OpenAlex rejected the request. Set OPENALEX_API_KEY "
                    "(free key: https://openalex.org/settings/api)."
                )
            if resp.status_code >= 400:
                raise OpenAlexError(f"OpenAlex error HTTP {resp.status_code}: {resp.text[:200]}")
            return resp.json()
        raise OpenAlexError("unreachable")  # pragma: no cover

    # ------------------------------------------------------------ institutions
    def institution_candidates(self, name: str, country_code: str, limit: int = 5) -> list[dict]:
        data = self._get(
            "/institutions",
            {
                "search": name,
                "filter": f"country_code:{country_code}",
                "per_page": limit,
                "select": "id,display_name,country_code,type,works_count,ror",
            },
        )
        return data.get("results", [])

    def find_institution(self, name: str, country_code: str) -> dict | None:
        results = self.institution_candidates(name, country_code)
        if not results:
            return None
        lowered = name.lower()
        for r in results:
            if (r.get("display_name") or "").lower() == lowered:
                return r
        return results[0]

    # ------------------------------------------------------------------ works
    def search_works(self, institution_id: str, query: str, from_year: int, per_page: int = 100) -> list[dict]:
        data = self._get(
            "/works",
            {
                "search": query,
                "filter": (
                    f"authorships.institutions.lineage:{institution_id},"
                    f"from_publication_date:{from_year}-01-01"
                ),
                "per_page": min(per_page, 100),
                "select": WORK_SELECT,
            },
        )
        return data.get("results", [])

    def recent_works_by_authors(self, author_ids: list[str], from_year: int, batch: int = 15) -> list[dict]:
        works: list[dict] = []
        for group in chunks(author_ids, batch):
            data = self._get(
                "/works",
                {
                    "filter": (
                        f"authorships.author.id:{'|'.join(group)},"
                        f"from_publication_date:{from_year}-01-01"
                    ),
                    "sort": "publication_date:desc",
                    "per_page": 100,
                    "select": WORK_SELECT,
                },
            )
            works.extend(data.get("results", []))
        return works

    # ---------------------------------------------------------------- authors
    def get_authors(self, author_ids: list[str]) -> list[dict]:
        authors: list[dict] = []
        for group in chunks(author_ids, 50):
            data = self._get(
                "/authors",
                {"filter": f"openalex:{'|'.join(group)}", "per_page": 50, "select": AUTHOR_SELECT},
            )
            authors.extend(data.get("results", []))
        return authors
