"""Hybrid, explainable student <-> professor matching.

score = alpha * semantic + (1 - alpha) * lexical          (sbert backend)
score = semantic (== TF-IDF based)                         (tfidf backend: offline baseline)

semantic = 0.5 * sim(student, professor profile) + 0.5 * mean(top-3 paper similarities)
lexical  = TF-IDF cosine(student, professor profile)

Every explanation field is derived from the same numbers that produced the score:
- shared_terms:    the TF-IDF terms contributing most to the lexical cosine
- evidence_papers: the papers with the highest similarity to the student
- matched_topics:  taxonomy topics present in both the student and the professor text
"""

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from .taxonomy import TOPICS, count_term

MAX_PAPERS = 8


@dataclass
class PaperDoc:
    title: str
    year: int | None
    doi: str | None
    text: str


@dataclass
class ProfessorDoc:
    professor_id: str
    text: str
    papers: list[PaperDoc] = field(default_factory=list)


@dataclass
class MatchResult:
    professor_id: str
    score: float
    semantic: float
    lexical: float
    shared_terms: list[str]
    matched_topics: list[str]
    evidence_papers: list[dict]
    summary: str


class Embedder(Protocol):
    name: str

    def similarity(self, query: str, docs: list[str]) -> np.ndarray: ...


class TfidfEmbedder:
    name = "tfidf"

    def similarity(self, query: str, docs: list[str]) -> np.ndarray:
        if not docs:
            return np.zeros(0)
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        try:
            matrix = vec.fit_transform([query] + docs)
        except ValueError:  # empty vocabulary
            return np.zeros(len(docs))
        return (matrix[1:] @ matrix[0].T).toarray().ravel()


class SentenceTransformerEmbedder:
    name = "sbert"

    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer  # optional dependency

        self.model = SentenceTransformer(model_name)

    def similarity(self, query: str, docs: list[str]) -> np.ndarray:
        if not docs:
            return np.zeros(0)
        vectors = self.model.encode([query] + docs, normalize_embeddings=True, show_progress_bar=False)
        return np.clip(vectors[1:] @ vectors[0], 0.0, 1.0)


def make_embedder(backend: str, sbert_model: str) -> Embedder:
    if backend == "sbert":
        try:
            return SentenceTransformerEmbedder(sbert_model)
        except ImportError as exc:
            raise RuntimeError(
                "EMBEDDING_BACKEND=sbert needs: pip install -r requirements-sbert.txt"
            ) from exc
    return TfidfEmbedder()


# --------------------------------------------------------------------------- text builders
def build_student_text(interests: list[str], skills: list[str], experience: str | None) -> str:
    interest_text = ". ".join(interests)
    parts = [interest_text, interest_text, " ".join(skills)]  # interests weighted x2
    if experience:
        parts.append(experience)
    return "\n".join(p for p in parts if p)


def build_professor_doc(professor_id: str, topics: list[str], publications: list) -> ProfessorDoc:
    pubs = sorted(publications, key=lambda p: p.year or 0, reverse=True)[:MAX_PAPERS]
    papers = []
    for p in pubs:
        text = " ".join(filter(None, [p.title, " ".join(p.keywords or []), p.abstract]))
        papers.append(PaperDoc(title=p.title, year=p.year, doi=p.doi, text=text))
    text = " ".join([" ".join(topics)] + [paper.text for paper in papers])
    return ProfessorDoc(professor_id=professor_id, text=text, papers=papers)


# --------------------------------------------------------------------------- lexical + explanations
def lexical_scores(query: str, docs: list[ProfessorDoc]) -> tuple[np.ndarray, list[list[str]]]:
    """TF-IDF cosine per professor plus the terms that contributed most to it."""
    if not docs:
        return np.zeros(0), []
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
    try:
        matrix = vec.fit_transform([query] + [d.text for d in docs])
    except ValueError:
        return np.zeros(len(docs)), [[] for _ in docs]
    terms = np.array(vec.get_feature_names_out())
    q = matrix[0].toarray().ravel()
    sims, shared = [], []
    for i in range(len(docs)):
        d = matrix[i + 1].toarray().ravel()
        contrib = q * d
        sims.append(float(contrib.sum()))
        top = np.argsort(-contrib)[:12]
        picked: list[str] = []
        for idx in top:
            if contrib[idx] <= 0:
                break
            term = str(terms[idx])
            # keep bigrams, drop unigrams already covered by a picked bigram
            if any(term in p.split() for p in picked if " " in p):
                continue
            picked.append(term)
            if len(picked) == 6:
                break
        shared.append(picked)
    return np.array(sims), shared


def matched_topics(student_text: str, professor_text: str) -> list[str]:
    out = []
    for topic, aliases in TOPICS.items():
        names = aliases + [topic]
        if any(count_term(student_text, n) for n in names) and any(count_term(professor_text, n) for n in names):
            out.append(topic)
    return out


def _summary(topics: list[str], terms: list[str], papers: list[dict]) -> str:
    bits = []
    if topics:
        bits.append("shared research topics: " + ", ".join(topics[:3]))
    if terms:
        bits.append("overlapping terms: " + ", ".join(terms[:4]))
    if papers:
        p = papers[0]
        year = f" ({p['year']})" if p.get("year") else ""
        bits.append(f"most relevant recent paper: \"{p['title']}\"{year}")
    return "; ".join(bits).capitalize() + "." if bits else "Weak overlap with your profile."


# --------------------------------------------------------------------------- main entry point
def rank_professors(
    student_text: str,
    docs: list[ProfessorDoc],
    embedder: Embedder,
    alpha: float,
    top_k: int,
) -> list[MatchResult]:
    if not docs or not student_text.strip():
        return []

    lexical, shared_terms = lexical_scores(student_text, docs)

    profile_sim = embedder.similarity(student_text, [d.text for d in docs])
    flat_papers = [(i, p) for i, d in enumerate(docs) for p in d.papers]
    paper_sim = embedder.similarity(student_text, [p.text for _, p in flat_papers]) if flat_papers else np.zeros(0)

    per_prof: dict[int, list[tuple[float, PaperDoc]]] = {i: [] for i in range(len(docs))}
    for (i, paper), sim in zip(flat_papers, paper_sim, strict=True):
        per_prof[i].append((float(sim), paper))

    results: list[MatchResult] = []
    for i, doc in enumerate(docs):
        ranked = sorted(per_prof[i], key=lambda t: -t[0])
        top3 = [s for s, _ in ranked[:3]]
        semantic = 0.5 * float(profile_sim[i]) + 0.5 * (float(np.mean(top3)) if top3 else 0.0)
        lex = float(lexical[i])
        score = semantic if embedder.name == "tfidf" else alpha * semantic + (1 - alpha) * lex
        evidence = [
            {"title": p.title, "year": p.year, "doi": p.doi, "similarity": round(s * 100, 1)}
            for s, p in ranked[:3]
        ]
        topics = matched_topics(student_text, doc.text)
        results.append(
            MatchResult(
                professor_id=doc.professor_id,
                score=round(score * 100, 1),
                semantic=round(semantic * 100, 1),
                lexical=round(lex * 100, 1),
                shared_terms=shared_terms[i],
                matched_topics=topics,
                evidence_papers=evidence,
                summary=_summary(topics, shared_terms[i], evidence),
            )
        )

    results.sort(key=lambda r: -r.score)
    return results[:top_k]
