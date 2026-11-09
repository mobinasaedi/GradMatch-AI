# Daily Log

Format: date, what was done, what is next, blockers/decisions.

## 2026-11-07 (Day 1)

**Done**
- Reconciled the two scope documents: the *research design* (dataset, RQs, gold standard) is kept under `research/`; the *MVP scope* (resume -> top-10 professors -> manual email tracking, no paid services) drives the code.
- Backend (FastAPI): resume parsing (PDF/DOCX), rule-based profile extraction, OpenAlex client with retries/batching, discovery + caching, hybrid explainable matcher, official-page email lookup (SSRF-safe, never guesses), manual outreach tracking, template email draft.
- Frontend (React/Vite): upload -> profile review -> country/university selection -> top-10 with evidence -> tracker with chart.
- 32 backend tests (mocked OpenAlex), ruff clean, frontend production build OK.
- Docs: README, SRS v1 (MVP), architecture, roadmap.

**Decisions**
- OpenAlex now requires a free API key for real use -> `OPENALEX_API_KEY`, caching and per-run university cap to protect credits.
- `/authors?search=` only searches names, so discovery is works-first: search works by topic within an institution, then score authors by position.
- Institution IDs are resolved by name unless pinned in `universities.json` (pin them in Phase 0).

**Next**
- Phase 0 in `ROADMAP.md`: verify against the live API, pin institution IDs, run a real end-to-end search.

**Blockers / risks**
- Live OpenAlex behaviour not yet verified.
- Non-faculty authors may appear in results until the Phase 1 heuristics are in.
