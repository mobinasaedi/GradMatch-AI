# Methodology

## Data collection pipeline

1. Fix the university sampling frame (15 universities, 3 per country).
2. Resolve OpenAlex institution ids (`scripts/resolve_institutions.py`) and pin them.
3. Discover candidate professors per university and topic (works-first search, author position weighting).
4. Retrieve recent publications (2021+), max 5 per professor for the dataset.
5. Enrich/verify with Crossref / Semantic Scholar (match by DOI; do not merge records without checking duplicates).
6. Verify affiliation and public email on official university pages; store source URL and check date.
7. Clean: deduplicate, standardise institution names, validate DOIs, flag missing abstracts, check dates.
8. Version the result as `GradMatch-Dataset-v1.0`; every new collection creates a new version.

`scripts/collect_sample.py` implements steps 3-4 for a first sample.

## Evaluation plan

1. **Baseline comparison:** keyword vs TF-IDF vs Sentence Transformers vs hybrid on the gold standard (RQ1).
2. **Feature ablation:** interests / +skills / +publications / all (RQ2).
3. **Explainability study:** faithfulness, evidence coverage, understandability, factual accuracy (RQ3).

## Threats to validity

| Risk | Mitigation |
|------|------------|
| Incomplete professor data | multiple sources, official-site verification |
| Duplicate authors | entity resolution |
| Stale information | verification date on every record |
| Missing abstracts | title + keyword fallback; report the share affected |
| Ranking bias | ablation, inspect by country/university |
| API rate limits / credits | caching, retries, per-run caps |
| Small gold standard | more pairs, independent annotators, report sampling limits |
| Data leakage | hold out professors/universities |
