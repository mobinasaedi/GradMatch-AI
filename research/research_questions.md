# Research Questions

**Objective:** design and evaluate a framework that matches student research profiles with academic supervisors using semantic matching and explainable AI.

**Scope decision:** version 1 evaluates *research-relevance matching quality*, not admission or funding prediction (those need different data; a professor can be a perfect research fit and still have no openings or funding).

## RQ1: Semantic matching performance (primary)
Does semantic matching outperform keyword-based methods in identifying relevant supervisors?

- H1: nDCG@10(Semantic) > nDCG@10(Keyword)
- Methods: keyword matching, TF-IDF, Sentence Transformers, hybrid
- Metrics: Precision@5, Recall@10, nDCG@10, MRR

## RQ2: Contribution of multiple information sources
Does combining skills, research interests and publications improve recommendation quality?

| Experiment | Input features |
|------------|----------------|
| E1 | Research interests |
| E2 | Research interests + skills |
| E3 | Research interests + publications |
| E4 | All features |

- H2: Performance(E4) > Performance(E1), tested with an ablation study.

## RQ3: Explainability and trustworthiness
Can the system give understandable, evidence-based reasons for each recommendation?

- Faithfulness: is the explanation consistent with the real computation?
- Evidence coverage: is each reason linked to a real paper/record?
- Human understandability: can an evaluator understand the reason?
- Factual accuracy: is the displayed information correct?

## RQ4: Funding information reliability (exploratory, deferred)
How reliably can funding information be extracted from official university sources? Postponed beyond the MVP.

## Note on numbers
Dataset sizes in `dataset_schema.md` are *collection targets*, not results. No experimental results exist yet.
