# GradMatch AI: Software Requirements Specification (MVP v1.0)

| Field | Value |
|-------|-------|
| Project | GradMatch AI: An AI-Based Academic Supervisor Recommendation and Email Tracking System |
| Version | 1.0 (MVP, course deliverable) |
| Domain | Web application + applied NLP |
| Degree / countries | Master's; Canada, USA, Germany, Netherlands, France |
| Stack | React, Python/FastAPI, PostgreSQL, OpenAlex, local Sentence Transformers / TF-IDF |
| Constraint | No paid services |

## 1. Purpose

Help prospective graduate students find relevant research supervisors by analysing an academic resume, restricting the search to chosen countries/universities, recommending the 10 best-matching professors with reasons, and tracking email communication.

## 2. Scope

### In scope (v1)
1. Student profile and resume processing (PDF/DOCX).
2. Country and university selection.
3. Academic data collection (OpenAlex; public email lookup on official pages).
4. AI-based professor matching (hybrid TF-IDF / semantic).
5. Top-10 recommendation with explanation.
6. Email contact and communication tracking (manual status updates).

### Out of scope (future versions)
Admission-probability prediction; scholarship/funding search and analysis; LLM-generated emails; automatic email sending; Gmail integration and reply detection; advanced analytics/research experiments dashboard; large multi-country databases.

## 3. Actors

| Actor | Responsibility |
|-------|----------------|
| Student | Uploads resume, edits profile, selects targets, reviews matches, tracks outreach |
| System | Parses, matches, explains, stores |
| OpenAlex API | Source of researchers and publications |
| University website | Source of public emails (user-triggered lookup) |

## 4. Functional requirements

| ID | Requirement | Priority | Status (v0.1 draft) |
|----|-------------|----------|---------------------|
| FR-01 | Accept PDF/DOCX resume (<= 5 MB), reject unsupported/corrupt/empty files with clear messages | High | Implemented, tested |
| FR-02 | Extract name, field, GPA, research interests, skills, research experience; let the user edit the result | High | Implemented (rule-based), tested |
| FR-03 | Let the user choose one or more countries and optionally specific universities; limit the search to them | High | Implemented, tested |
| FR-04 | Retrieve candidate professors and recent publications (>= 2021) from OpenAlex | High | Implemented; live API untested |
| FR-05 | Rank candidates by similarity between the student profile and professor topics/papers (TF-IDF baseline, optional Sentence Transformers hybrid) | High | Implemented, tested (TF-IDF) |
| FR-06 | Show the top 10 with university, research areas, score and reason | High | Implemented |
| FR-07 | Explain each recommendation with shared topics/terms and evidence papers derived from the actual scores | High | Implemented, tested |
| FR-08 | Show a professor's public email only if found on an official page and confirmed by the user; store source URL; never guess | High | Implemented, tested |
| FR-09 | Track per-professor status (not started, draft ready, sent, replied, follow-up needed, closed) with notes and history | High | Implemented, tested |
| FR-10 | Provide a deterministic, editable email template (no LLM) | Low | Implemented |
| FR-11 | Let the user delete all their data | Medium | Implemented, tested |
| FR-12 | User accounts and authentication | Medium | Not started |

## 5. Non-functional requirements

| ID | Requirement |
|----|-------------|
| NFR-01 Cost | Only free software/services (OpenAlex free key, local models) |
| NFR-02 Privacy | Resume text stored only in the application database; deletable on request; no resume content sent to third parties |
| NFR-03 Data quality | Every external datum carries its source; emails carry a source URL; the UI states that OpenAlex results are candidates to verify |
| NFR-04 Reliability | Retries with backoff for OpenAlex 429/5xx; per-university failures reported as warnings, not crashes |
| NFR-05 Budget | Searches capped per run and cached to respect the OpenAlex credit budget |
| NFR-06 Explainability | Explanations are computed from the ranking inputs, not generated free-form |
| NFR-07 Maintainability | Separated service layer, typed API schemas, automated tests, CI |
| NFR-08 Security | Official-domain-only URL fetching with HTTPS, redirect re-validation and private-IP blocking; upload size/type limits |

## 6. Acceptance criteria (selected)

**FR-05 / FR-07 (matching)**
1. Given a profile with NLP/LLM interests and two candidate professors (NLP vs. computer vision), the NLP professor ranks first.
2. Each result lists at least one evidence paper taken from that professor's stored publications, ordered by similarity.
3. Shared terms are terms present in both texts, ranked by their contribution to the TF-IDF cosine.
4. With the TF-IDF backend the system works fully offline.

**FR-08 (email)**
1. A page outside the university's official domain is rejected.
2. If no email is found, the field stays empty and the system says so.
3. A stored email always has a source URL on the official domain.

**FR-09 (tracking)**
1. Changing status or notes appends an event with a timestamp.
2. Stats endpoint returns counts for every status.

## 7. Traceability to modules

| Module | Requirements | Code |
|--------|--------------|------|
| Student profile & resume processing | FR-01, FR-02, FR-11 | `services/resume_parser.py`, `services/profile_extractor.py`, `routers/students.py` |
| Country & university selection | FR-03 | `services/universities.py`, `data/universities.json`, `routers/universities.py` |
| Academic data collection | FR-04, FR-08 | `services/openalex.py`, `services/discovery.py`, `services/email_finder.py` |
| AI-based professor matching | FR-05, FR-07 | `services/matcher.py` |
| Top-10 recommendation | FR-06 | `routers/recommendations.py`, `frontend/.../Results.jsx` |
| Email contact & tracking | FR-09, FR-10 | `routers/outreach.py`, `services/draft.py`, `frontend/.../Tracker.jsx` |

## 8. Assumptions and limitations

- OpenAlex author data does not indicate faculty status or openings; candidates are filtered heuristically (affiliation match, minimum works count, last-author weighting) and must be verified on official pages.
- Rule-based extraction is vocabulary-driven and tuned for CS/ML/NLP resumes.
- Scores are cosine-based similarity values, not probabilities.
