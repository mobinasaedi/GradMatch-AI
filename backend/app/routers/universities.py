from fastapi import APIRouter, Query

from ..schemas import UniversityOut
from ..services.universities import list_universities

router = APIRouter(prefix="/api", tags=["universities"])


@router.get("/countries")
def countries() -> list[dict]:
    seen: dict[str, str] = {}
    for u in list_universities():
        seen[u.country_code] = u.country
    return [{"code": c, "name": n} for c, n in sorted(seen.items(), key=lambda kv: kv[1])]


@router.get("/universities", response_model=list[UniversityOut])
def universities(country: list[str] = Query(default=[])):
    return [
        UniversityOut(key=u.key, name=u.name, country_code=u.country_code, country=u.country, website=u.website)
        for u in list_universities(country or None)
    ]
