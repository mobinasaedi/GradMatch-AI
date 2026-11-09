# Dataset Schema (GradMatch-Dataset v1.0 plan)

## Collection targets (not collected yet)

| Item | Target |
|------|--------|
| Synthetic student profiles | 30 |
| Real professor profiles | 150 |
| Universities | 15 (3 per country) |
| Publications | ~750 (<= 5 per professor, 2021+) |
| Student-professor pairs for gold standard | ~1000 (of at most 4500) |

Students are synthetic (no real personal data). Professors, universities and papers come from public, citable sources.

## student_profiles.csv

| Column | Type | Example |
|--------|------|---------|
| student_id | string | STU001 |
| degree | category | Master's |
| field | string | Computer Engineering |
| gpa | float | 18.0 |
| research_interests | list | NLP, ML |
| skills | list | Python, PyTorch |
| research_experience | text | LLM robustness |
| preferred_countries | list | CA, DE |

## professors.csv

| Column | Type |
|--------|------|
| professor_id | string (OpenAlex author id) |
| full_name | string |
| university_id | string |
| country | string |
| department | string (verified on official site) |
| research_interests | text |
| recent_publications | list of work ids |
| academic_profile_url | URL |
| contact_email | string (only if public + verified) |
| email_verified | boolean |
| data_source | string |

## publications.csv

publication_id, professor_id, title, abstract, publication_year, doi, keywords, source

## gold_standard.csv (GradMatch-Gold-1.0)

student_id, professor_id, relevance (0-3), annotator_1, annotator_2, adjudicated

| Label | Meaning |
|-------|---------|
| 0 | unrelated |
| 1 | weakly related |
| 2 | related |
| 3 | highly related |

Labels follow a written guideline (to be written in `research/annotation_guideline.md`); two independent annotators, a third resolves disagreements; agreement via weighted Cohen's kappa or Krippendorff's alpha.

## Data-leakage rule
Hold out whole professors (or universities) as an independent test set so no professor's data appears in both tuning and test.
