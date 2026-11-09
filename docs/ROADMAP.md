# Roadmap

Tasks are sized to roughly one working session each so the project can move forward a little every day. Tick items off and log them in `DAILY_LOG.md`.

## Phase 0: Verify the draft (do first)

- [ ] Create a free OpenAlex key, put it in `backend/.env`
- [ ] Run `scripts/resolve_institutions.py`, pin the correct `openalex_id` for all 15 universities
- [ ] Run `scripts/collect_sample.py` for Toronto, TUM, Amsterdam; inspect `data/raw/*.csv`
- [ ] Check live response fields against `openalex.py` (`select` lists, `last_known_institutions`, `keywords`, filter names); fix mismatches
- [ ] Run the full UI flow with a real resume; note anything confusing
- [ ] Push to GitHub and confirm CI is green

## Phase 1: Data quality (biggest risk to recommendation quality)

- [ ] Heuristic to exclude non-faculty (PhD students, postdocs): works_count/h-index thresholds, last-author ratio, first-publication year
- [ ] Deduplicate authors (OpenAlex sometimes splits one person into several IDs)
- [ ] Add university/department info to professors; link to official faculty directory pages
- [ ] Handle papers without abstracts (title + keywords fallback already exists; measure the impact)
- [ ] Per-university "last verified" metadata

## Phase 2: Matching quality

- [ ] Switch default to Sentence Transformers; compare with TF-IDF on a handful of hand-checked resumes
- [ ] Better profile extraction: more topics/skills, multilingual headings (Persian/English resumes)
- [ ] Let the user weight interests, add negative filters ("not computer vision")
- [ ] Diversity re-ranking so one lab does not fill all 10 slots
- [ ] Cache embeddings per professor in the DB

## Phase 3: Evaluation (from `research/`)

- [ ] 30 synthetic student profiles (`data/evaluation/student_profiles.csv`)
- [ ] Annotation guideline (0-3 relevance) + labelling sheet for ~1000 pairs
- [ ] Two annotators + agreement score (weighted Cohen's kappa)
- [ ] Metrics script: Precision@5, Recall@10, nDCG@10, MRR for keyword vs TF-IDF vs semantic vs hybrid
- [ ] Ablation: interests only vs +skills vs +publications vs all
- [ ] Small human study on explanation usefulness/faithfulness

## Phase 4: Product hardening

- [ ] Authentication (FR-12) and per-user data isolation
- [ ] Alembic migrations
- [ ] Rate limiting on upload and recommendation endpoints
- [ ] Background job + progress indicator for slow searches
- [ ] Frontend polish: loading skeletons, empty states, mobile layout, i18n (fa/en)
- [ ] OCR option for scanned resumes
- [ ] Frontend tests (Vitest + Testing Library); Playwright smoke test

## Phase 5: Later ideas (explicitly out of the MVP)

- Funding/scholarship extraction from official pages
- LLM-assisted email drafting with evidence-grounded prompts and human approval
- Gmail integration (send + reply detection) with minimal OAuth scopes
- Admission/funding prediction (needs real outcome data, not just research similarity)
