"""Demo dataset mode: the app must work end to end with no API key at all."""

import io

import docx
import pytest

RESUME = """Sara Ahmadi
Education
BSc in Computer Engineering, Example University. GPA: 18.2/20

Research Interests
Natural Language Processing, Large Language Models, Interpretability

Skills
Python, PyTorch, Hugging Face, scikit-learn

Research Experience
Bachelor thesis on retrieval-augmented generation for question answering.
"""


def _docx(text: str) -> bytes:
    document = docx.Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _upload(client) -> int:
    response = client.post(
        "/api/students",
        files={
            "file": (
                "cv.docx",
                _docx(RESUME),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.fixture()
def seeded(client):
    response = client.post("/api/meta/seed")
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["professors_inserted"] > 0
    # second call is idempotent
    assert client.post("/api/meta/seed").json()["professors_inserted"] == 0
    return report


def test_meta_endpoints(client):
    stats = client.get("/api/meta/stats").json()
    assert stats["database_dialect"] == "sqlite"
    assert stats["app_version"]
    names = {table["table"] for table in stats["tables"]}
    assert {"users", "students", "professors", "publications"} <= names
    assert stats["demo_seeded"] is False  # nothing loaded yet in this fresh database

    keys = {integration["key"]: integration for integration in client.get("/api/meta/integrations").json()}
    assert keys["openalex"]["required"] is True
    assert keys["openalex"]["configured"] is False
    assert keys["openalex"]["signup_url"].startswith("https://openalex.org")


def test_meta_stats_counts_the_seeded_dataset(client, seeded):
    stats = client.get("/api/meta/stats").json()
    assert stats["demo_seeded"] is True
    assert stats["dataset_coverage"]["uoft"]["professors"] > 0
    assert stats["counts"]["publications"] >= stats["counts"]["professors"]


def test_demo_search_without_api_key(client, seeded):
    student_id = _upload(client)
    response = client.post(
        f"/api/students/{student_id}/recommendations",
        json={"countries": ["CA"], "university_keys": ["uoft"], "top_k": 10},
    )
    assert response.status_code == 200, response.text
    run = response.json()
    assert run["data_source"] == "demo-dataset"
    assert 0 < len(run["results"]) <= 10
    assert any("demo" in warning.lower() for warning in run["warnings"])

    top = run["results"][0]
    assert top["professor"]["institution_name"] == "University of Toronto"
    assert 35 <= top["fit"] <= 97
    # the displayed fit must not change the ordering produced by the matcher
    fits = [item["fit"] for item in run["results"]]
    assert fits == sorted(fits, reverse=True)


def test_demo_search_falls_back_to_the_api_for_universities_without_local_data(client, seeded):
    """McGill has no bundled professors, so the live client is tried (stubbed in tests)."""
    student_id = _upload(client)
    response = client.post(
        f"/api/students/{student_id}/recommendations",
        json={"countries": ["CA"], "university_keys": ["mcgill"], "top_k": 5},
    )
    assert response.status_code in (200, 404, 502)
    if response.status_code == 200:
        assert response.json()["data_source"] == "openalex"


def test_overview_and_run_history(client, seeded):
    student_id = _upload(client)
    run = client.post(
        f"/api/students/{student_id}/recommendations",
        json={"countries": ["CA"], "university_keys": ["uoft"], "top_k": 10},
    ).json()

    overview = client.get(f"/api/students/{student_id}/overview").json()
    assert overview["matches"] == len(run["results"])
    assert overview["runs"] == 1
    assert overview["best_fit"] >= overview["avg_fit"]
    assert overview["profile_completeness"] > 0
    assert sum(bucket["count"] for bucket in overview["score_buckets"]) == overview["matches"]
    assert len(overview["activity"]) == 14

    outreach_id = run["results"][0]["outreach_id"]
    client.patch(f"/api/outreach/{outreach_id}", json={"status": "replied", "notes": "Positive reply"})
    overview = client.get(f"/api/students/{student_id}/overview").json()
    assert overview["funnel"]["replied"] == 1
    assert overview["reply_rate"] > 0

    runs = client.get(f"/api/students/{student_id}/runs").json()
    assert runs[0]["run_id"] == run["run_id"]
    assert runs[0]["data_source"] == "demo-dataset"

    reopened = client.get(f"/api/students/{student_id}/recommendations/{run['run_id']}")
    assert reopened.status_code == 200
    assert reopened.json()["run_id"] == run["run_id"]


def test_ai_draft_falls_back_to_template_without_key(client, seeded):
    student_id = _upload(client)
    run = client.post(
        f"/api/students/{student_id}/recommendations",
        json={"countries": ["CA"], "university_keys": ["uoft"], "top_k": 3},
    ).json()
    outreach_id = run["results"][0]["outreach_id"]
    draft = client.post(f"/api/outreach/{outreach_id}/draft").json()
    assert draft["engine"] == "template"
    assert "LLM_API_KEY" in draft["note"]
    assert "Dear Professor" in draft["body"]
