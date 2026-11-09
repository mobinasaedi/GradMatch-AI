from types import SimpleNamespace

from app.services.matcher import (
    TfidfEmbedder,
    build_professor_doc,
    build_student_text,
    rank_professors,
)


def pub(title, abstract="", year=2024):
    return SimpleNamespace(title=title, abstract=abstract, year=year, doi=None, keywords=[])


def make_docs():
    nlp = build_professor_doc(
        "A1",
        ["Natural Language Processing"],
        [
            pub("Large language models for question answering", "large language models natural language processing"),
            pub("Robust NLP with transformers", "natural language processing robustness of language models"),
        ],
    )
    cv = build_professor_doc(
        "A2",
        ["Computer Vision"],
        [pub("Object detection in street scenes", "convolutional networks object detection image segmentation")],
    )
    return [cv, nlp]


def test_relevant_professor_ranks_first():
    student = build_student_text(["Natural Language Processing", "Large Language Models"], ["Python"], None)
    results = rank_professors(student, make_docs(), TfidfEmbedder(), alpha=0.6, top_k=10)
    assert [r.professor_id for r in results] == ["A1", "A2"]
    assert results[0].score > results[1].score


def test_explanation_is_grounded_in_data():
    student = build_student_text(["Natural Language Processing", "Large Language Models"], [], None)
    top = rank_professors(student, make_docs(), TfidfEmbedder(), alpha=0.6, top_k=1)[0]
    assert "Natural Language Processing" in top.matched_topics
    assert any("language" in t for t in top.shared_terms)
    assert top.evidence_papers and top.evidence_papers[0]["title"].startswith("Large language models")
    assert top.evidence_papers[0]["similarity"] >= top.evidence_papers[-1]["similarity"]
    assert top.summary


def test_top_k_and_empty_inputs():
    student = build_student_text(["Natural Language Processing"], [], None)
    assert len(rank_professors(student, make_docs(), TfidfEmbedder(), 0.6, top_k=1)) == 1
    assert rank_professors("", make_docs(), TfidfEmbedder(), 0.6, 10) == []
    assert rank_professors(student, [], TfidfEmbedder(), 0.6, 10) == []


def test_professor_without_papers_does_not_crash():
    student = build_student_text(["Natural Language Processing"], [], None)
    docs = [build_professor_doc("A9", ["Natural Language Processing"], [])]
    results = rank_professors(student, docs, TfidfEmbedder(), 0.6, 10)
    assert results[0].evidence_papers == []
