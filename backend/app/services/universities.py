import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "universities.json"


@dataclass(frozen=True)
class University:
    key: str
    name: str
    country_code: str
    country: str
    website: str
    domains: tuple[str, ...]
    openalex_id: str | None  # pin the verified OpenAlex institution id here to skip name lookup


@lru_cache
def load_universities() -> dict[str, University]:
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return {
        u["key"]: University(
            key=u["key"],
            name=u["name"],
            country_code=u["country_code"],
            country=u["country"],
            website=u["website"],
            domains=tuple(u["domains"]),
            openalex_id=u.get("openalex_id"),
        )
        for u in raw
    }


def list_universities(country_codes: list[str] | None = None) -> list[University]:
    codes = {c.upper() for c in country_codes} if country_codes else None
    return [u for u in load_universities().values() if codes is None or u.country_code in codes]


def select_universities(country_codes: list[str], keys: list[str]) -> list[University]:
    """Universities in the chosen countries; if keys are given, only those keys."""
    candidates = list_universities(country_codes)
    if keys:
        wanted = set(keys)
        candidates = [u for u in candidates if u.key in wanted]
    return candidates
