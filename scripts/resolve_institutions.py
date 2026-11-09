"""Print OpenAlex institution candidates for every supported university.

Run this once (needs OPENALEX_API_KEY), check the output by eye, then paste the correct
`openalex_id` for each university into backend/app/data/universities.json so the
backend never has to guess an institution from its name.

    cd backend && python ../scripts/resolve_institutions.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import get_settings  # noqa: E402
from app.services.openalex import OpenAlexClient, short_id  # noqa: E402
from app.services.universities import list_universities  # noqa: E402


def main() -> None:
    s = get_settings()
    if not s.openalex_api_key:
        print("Warning: OPENALEX_API_KEY is not set; OpenAlex will probably reject requests.\n")
    client = OpenAlexClient(api_key=s.openalex_api_key, base_url=s.openalex_base_url)
    for uni in list_universities():
        print(f"== {uni.key}: {uni.name} ({uni.country_code})")
        for cand in client.institution_candidates(uni.name, uni.country_code):
            print(f"   {short_id(cand['id']):<14} {cand['display_name']}  [{cand.get('type')}, works={cand.get('works_count')}]")


if __name__ == "__main__":
    main()
