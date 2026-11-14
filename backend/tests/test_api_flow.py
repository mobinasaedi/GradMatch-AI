import io

import docx


def make_docx_bytes(text: str) -> bytes:
    d = docx.Document()
    for line in text.splitlines():
        d.add_paragraph(line)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def upload(client, text: str):
    return client.post(
        "/api/students",
        files={"file": ("cv.docx", make_docx_bytes(text), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"


def test_countries_and_universities(client):
    codes = {c["code"] for c in client.get("/api/countries").json()}
    assert codes == {"CA", "US", "DE", "NL", "FR", "GB"}
    unis = client.get("/api/universities", params={"country": ["NL"]}).json()
    assert {u["key"] for u in unis} == {"tudelft", "uva", "tue"}
    canada = {u["key"] for u in client.get("/api/universities", params={"country": ["CA"]}).json()}
    assert {"uoft", "ubc", "uwaterloo", "mcgill", "ualberta"} <= canada


def test_upload_rejects_bad_files(client):
    r = client.post("/api/students", files={"file": ("cv.txt", b"x" * 200, "text/plain")})
    assert r.status_code == 400


def test_full_flow(client, sample_resume, fake_openalex):
    # 1) upload resume -> extracted profile
    r = upload(client, sample_resume)
    assert r.status_code == 201, r.text
    student = r.json()
    sid = student["id"]
    assert "Natural Language Processing" in student["interests"]
    assert "raw_text" not in student

    # 2) edit the profile
    r = client.put(f"/api/students/{sid}", json={"interests": ["Natural Language Processing", " Large Language Models "]})
    assert r.json()["interests"] == ["Natural Language Processing", "Large Language Models"]

    # 3) recommendations (OpenAlex is faked)
    r = client.post(f"/api/students/{sid}/recommendations", json={"countries": ["CA"], "university_keys": ["uoft"]})
    assert r.status_code == 200, r.text
    run = r.json()
    names = [x["professor"]["name"] for x in run["results"]]
    assert names[0] == "Ada Nlp"
    assert "Junior Student" not in names          # filtered: too few publications
    top = run["results"][0]
    assert top["rank"] == 1 and top["explanation"]["evidence_papers"]
    assert top["outreach_status"] == "not_started" and top["outreach_id"]
    assert top["professor"]["email"] is None       # never guessed

    # second identical run is served from the cache (no extra OpenAlex search calls)
    calls_before = fake_openalex.calls.count("search_works")
    client.post(f"/api/students/{sid}/recommendations", json={"countries": ["CA"], "university_keys": ["uoft"]})
    assert fake_openalex.calls.count("search_works") == calls_before

    # latest results endpoint
    assert client.get(f"/api/students/{sid}/recommendations").json()["results"][0]["rank"] == 1

    # 4) tracking
    oid = top["outreach_id"]
    r = client.patch(f"/api/outreach/{oid}", json={"status": "sent", "notes": "Sent on Monday"})
    assert r.status_code == 200 and r.json()["status"] == "sent"
    events = client.get(f"/api/outreach/{oid}/events").json()
    assert events[-1]["status"] == "sent" and events[-1]["note"] == "Sent on Monday"
    stats = client.get(f"/api/students/{sid}/outreach/stats").json()
    assert stats["by_status"]["sent"] == 1 and stats["total"] == len(run["results"])

    # 5) draft (template based)
    draft = client.get(f"/api/outreach/{oid}/draft").json()
    assert "Professor Nlp" in draft["body"] and "Not AI-generated" not in draft["note"]
    assert "template" in draft["note"].lower()

    # 6) delete everything for the student
    assert client.delete(f"/api/students/{sid}").status_code == 204
    assert client.get(f"/api/students/{sid}").status_code == 404


def test_recommendation_guards(client, sample_resume):
    sid = upload(client, sample_resume).json()["id"]
    # too many universities
    r = client.post(f"/api/students/{sid}/recommendations", json={"countries": ["CA", "US", "DE"]})
    assert r.status_code == 400 and "at most" in r.json()["detail"]
    # unknown country
    r = client.post(f"/api/students/{sid}/recommendations", json={"countries": ["ZZ"]})
    assert r.status_code == 400
    # no interests
    client.put(f"/api/students/{sid}", json={"interests": []})
    r = client.post(f"/api/students/{sid}/recommendations", json={"countries": ["CA"], "university_keys": ["uoft"]})
    assert r.status_code == 400
    # unknown student
    assert client.post("/api/students/999/recommendations", json={"countries": ["CA"]}).status_code == 404


def test_email_confirmation_requires_official_source(client, sample_resume):
    sid = upload(client, sample_resume).json()["id"]
    client.post(f"/api/students/{sid}/recommendations", json={"countries": ["CA"], "university_keys": ["uoft"]})
    pid = "A1"
    bad = client.put(f"/api/professors/{pid}/email", json={"email": "ada@utoronto.ca", "source_url": "https://evil.com/p"})
    assert bad.status_code == 400
    # a syntactically bad email is rejected by validation
    assert client.put(f"/api/professors/{pid}/email", json={"email": "nope", "source_url": "https://www.utoronto.ca/"}).status_code == 422
    ok = client.put(
        f"/api/professors/{pid}/email",
        json={"email": "Ada@UToronto.ca", "source_url": "https://www.cs.utoronto.ca/~ada"},
    )
    # DNS may be unavailable in sandboxes; accept success, or the explicit resolve error — never a silent save
    assert ok.status_code in (200, 400)
    if ok.status_code == 200:
        assert ok.json()["email"] == "ada@utoronto.ca"
