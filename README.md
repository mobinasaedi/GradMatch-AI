# GradMatch AI

**An AI-based assistant that recommends research supervisors from your academic resume and helps you track your email outreach.**

Upload your academic resume, choose the countries and universities you care about, and get the **top 10 candidate supervisors** whose recent papers match your research profile, with an evidence-based explanation for each match. Then track the status of your emails to each professor.

> **Status: MVP (v0.1), runs locally.** The backend, frontend, authentication, tests and Docker files are in place. Live professor search through OpenAlex still needs to be verified with a real API key, and the service is not ready for public deployment (see [Known limitations](#known-limitations)).

## Features

| # | Feature | How it works |
|---|---------|--------------|
| 1 | Resume upload (PDF or DOCX) | PyMuPDF and python-docx extract the text; a rule-based extractor builds an editable research profile |
| 2 | Country and university selection | 5 countries x 3 universities, stored in `backend/app/data/universities.json` |
| 3 | Top-10 supervisor recommendation | OpenAlex works and authors, hybrid TF-IDF and optional Sentence-Transformers matching, with shared terms and evidence papers for each result |
| 4 | Email tracking | Manual status tracking inside the app, a public-email lookup on official university pages, and a template draft |
| 5 | Accounts | Email and password sign-in, Argon2id password hashing, signed HttpOnly session cookies, CSRF checks, password-reset endpoints, and per-account data ownership |

Out of scope for this version: admission or funding prediction, funding search, LLM-written emails, automatic sending, and Gmail sync.

## Design decisions

- **Explainable by construction.** The shared terms come from the TF-IDF contributions, and the evidence papers come from the same similarity scores that produce the ranking.
- **Never guesses emails.** An address is stored only after the user confirms one found on a page of the university's official domain.
- **Honest data limits.** OpenAlex does not say who is current faculty or who is accepting students. Results are *candidates*, and the interface says so. Always check the professor's official page.
- **Privacy.** Resume text stays in your own database, and deleting a student record removes it with all derived data.
- **API budget.** Searches are capped (`MAX_UNIVERSITIES_PER_RUN`) and cached (`CACHE_TTL_DAYS`).

## Architecture

```
React (Vite)  --/api-->  FastAPI  -->  SQLite (local) or PostgreSQL (Docker)
                           |--> OpenAlex API        professors and papers (free API key)
                           |--> local matcher       TF-IDF, optional Sentence-Transformers
                           '--> official university pages   public email lookup, triggered by the user
```

## Project layout

```
GradMatch-AI/
├── backend/        FastAPI app (app/), tests (tests/), requirements
├── frontend/       React and Vite interface
├── docs/           requirements, architecture, roadmap, daily log
├── research/       research questions and evaluation plan
├── scripts/        data collection helpers (OpenAlex to CSV)
├── data/           folder structure for datasets (CSV files are git-ignored)
├── .env.example    template for settings, copy it, never commit the real file
├── docker-compose.yml
├── Makefile
└── README.md
```

## Quick start on Windows (PowerShell)

Requirements: Python 3.11 or newer, Node.js 20 or newer. For live professor searches you also need a free OpenAlex API key from https://openalex.org/settings/api.

**1. Backend**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy ..\.env.example .env
```

Open `backend\.env` and set these values:

- `SECRET_KEY`: generate one with `.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"`
- `COOKIE_SECURE=false` (only for local use over http)
- `PUBLIC_APP_URL=http://localhost:5173`
- `OPENALEX_API_KEY`: leave empty to test sign-in, resume upload and profile editing; add your key for live searches

Then start the server:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

The API documentation is at http://localhost:8000/docs.

**2. Frontend** (in a second PowerShell window)

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open http://localhost:5173, create an account (the password must be at least 12 characters), upload your resume, correct the profile, choose universities, and view your recommendations.

**3. Tests**

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

The tests do not need network access.

### macOS or Linux

```bash
cp .env.example backend/.env     # then edit SECRET_KEY and the other values
make setup                       # creates the virtual environment and installs dependencies
make backend                     # http://localhost:8000
make frontend                    # http://localhost:5173 (new terminal)
make test
```

### Optional: semantic embeddings

```bash
cd backend
.venv/bin/pip install -r requirements-sbert.txt      # Windows: .\.venv\Scripts\pip.exe
# then set EMBEDDING_BACKEND=sbert in backend/.env
```

### Optional: Docker (PostgreSQL, backend, nginx frontend)

```bash
OPENALEX_API_KEY=your-key docker compose up --build
```

Then open http://localhost:8080. The Docker files have not been run in the authoring environment.

### Optional: pin OpenAlex institution IDs

```bash
cd backend
python ../scripts/resolve_institutions.py
```

Check the printed candidates and paste the correct `openalex_id` for each university into `backend/app/data/universities.json`. Without it, the backend finds institutions by name and caches the first match.

## Configuration

All settings live in `backend/.env` (see `.env.example`).

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Signs session cookies. Use a long random value and keep it private |
| `COOKIE_SECURE` | `true` behind HTTPS, `false` for local http |
| `PUBLIC_APP_URL` | Address of the frontend, used in password-reset links |
| `SMTP_*` | Mail server settings. Password-reset email is delivered only when these are set |
| `OPENALEX_API_KEY` | Needed for live professor searches |
| `DATABASE_URL` | SQLite by default; PostgreSQL in Docker |
| `EMBEDDING_BACKEND` | `tfidf` (offline) or `sbert` |
| `MAX_UNIVERSITIES_PER_RUN` | Limits OpenAlex usage per search |

Never commit `.env` or the database file. Both are listed in `.gitignore`.

## Known limitations

- OpenAlex calls are covered by mocked tests only. The first real run with an API key may need small query or field adjustments.
- Before any public launch it still needs rate limiting, email verification, HTTPS with `COOKIE_SECURE=true`, a managed PostgreSQL database with backups, and a working SMTP setup. The frontend and API should be served from the same origin.
- There are no database migrations yet (tables are created at startup).
- Scanned PDFs without a text layer are rejected, because there is no OCR.
- Results show research similarity. They are not predictions of admission or funding.

## Author

Mobina Saedi, Computer Engineering undergraduate at Islamic Azad University, Central Tehran Branch.
GitHub: https://github.com/mobinasaedi | Website: https://mobinasaedi.github.io

---

## راهنمای سریع (فارسی)

۱. وارد پوشه‌ی `backend` شوید، محیط مجازی بسازید و وابستگی‌ها را نصب کنید (دستورهای بالا).
۲. فایل `.env.example` را به `backend\.env` کپی کنید، `SECRET_KEY` را بسازید و (برای جستجوی زنده) کلید رایگان OpenAlex را در `OPENALEX_API_KEY` بگذارید.
۳. بک‌اند را با uvicorn و فرانت‌اند را با `npm.cmd run dev` اجرا کنید.
۴. در مرورگر `http://localhost:5173` را باز کنید، حساب بسازید، رزومه را آپلود کنید، پروفایل را اصلاح کنید، کشور و دانشگاه را انتخاب کنید و ۱۰ استاد پیشنهادی را با دلیلشان ببینید.
۵. وضعیت ایمیل هر استاد را در تب «Email tracker» دستی ثبت کنید.

نکته: نتایج «شباهت پژوهشی» هستند، نه پیش‌بینی پذیرش یا فاند. وابستگی استاد و ظرفیت پذیرش دانشجو را حتماً در سایت رسمی دانشگاه بررسی کنید.
