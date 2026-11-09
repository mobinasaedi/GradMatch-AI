# Architecture

```
frontend (React, Vite, Recharts)
   |  /api/*
backend (FastAPI)
   routers/        HTTP layer: students, universities, recommendations, professors, outreach
   services/       business logic (no HTTP types)
      resume_parser      PDF/DOCX -> text
      profile_extractor  text -> profile (sections + taxonomy)
      openalex           API client (retries, api_key, batching)
      discovery          institution -> candidate professors + papers (cached in DB)
      matcher            TF-IDF / Sentence-Transformers ranking + explanations
      email_finder       official-page email lookup (SSRF-safe)
      draft              deterministic email template
   models.py       SQLAlchemy tables
   schemas.py      Pydantic request/response models
```

## Recommendation flow

1. `POST /api/students` -> text extraction -> rule-based profile (user edits via `PUT`).
2. `POST /api/students/{id}/recommendations` with countries (+ optional university keys):
   1. Resolve each university to an OpenAlex institution id (pinned in JSON, else looked up by name and cached).
   2. For the top-3 student interests: `GET /works?search=<interest>&filter=authorships.institutions.lineage:<inst>,from_publication_date:<year>`.
   3. Score authors from those works (author position weights: last 1.0, middle 0.6, first 0.4); keep the top N.
   4. Fetch author records, keep those whose `last_known_institutions` contains the institution and `works_count >= MIN_AUTHOR_WORKS`.
   5. Fetch each kept author's recent works (batched); store professors + publications.
   6. Build a student text and one text per professor (topics + titles + keywords + abstracts of up to 8 recent papers).
   7. Rank (see below), persist the run, create tracking rows, return the top K.

## Scoring

```
semantic = 0.5 * sim(student, professor profile) + 0.5 * mean(top-3 paper similarities)
lexical  = TF-IDF cosine(student, professor profile)

tfidf backend : score = semantic                      (offline baseline)
sbert backend : score = alpha * semantic + (1-alpha) * lexical     (alpha = HYBRID_ALPHA)
```

Scores are shown x100. They are similarity values, not probabilities, and are only comparable within one run.

## Explanations (faithful by construction)

- `shared_terms`: TF-IDF terms with the largest `student_weight * professor_weight`; these literally sum to the lexical score.
- `evidence_papers`: the three papers with the highest similarity to the student; the same numbers feed `semantic`.
- `matched_topics`: taxonomy topics found in both texts.

## Email handling

`POST /api/professors/{id}/email-lookup` fetches a user-supplied page only if it is HTTPS, on the university's official domain, resolves to a public IP, and every redirect stays on-domain. Candidates are returned; only `PUT /api/professors/{id}/email` (user confirmation + source URL) stores one.

## Caching

- `search_cache`: (institution, year, query) -> scored author ids, TTL `CACHE_TTL_DAYS`.
- `professors` / `publications`: re-used while fresh; a repeated identical search makes no OpenAlex search calls (covered by a test).
- `institution_cache`: name -> OpenAlex institution id.

## Testing strategy

OpenAlex is replaced by `FakeOpenAlex` (tests/conftest.py) and `httpx.MockTransport`, so the suite needs no network or key. A small live smoke script is on the roadmap.
