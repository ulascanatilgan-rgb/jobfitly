# JobFitly.

**Five relevant jobs. Once a day.** A deliberately minimal job-matching web app for candidates. Built with Flask, SQLite and responsive vanilla JavaScript.

## Product

1. **CV** — Upload a text-based PDF, DOCX or TXT (5 MB limit). Text is extracted server-side; original file is not retained.
2. **Skills** — 15 self-ratings (0–10) measuring preferred work style and skills. Self-assessments, not validated psychometric tests.
3. **Search** — Country, city, preferred language, keywords, and six quick choices for role / sector / company / work style.
4. **Run** — One explicit run per user per **Europe/Brussels calendar day**. Fetches from authorized sources, checks publication recency (default 14 days), tests listing links, ranks matches and returns **up to five**. No fabricated listings.
5. **Watchlist & History** — Save roles and revisit prior dated runs.
6. **Application kit** — Generate exactly seven concise motivation points and a CV draft grounded in the uploaded CV and job requirements. Export both as PDF; verify content before submitting.

All scores are heuristic **relevance ratings**, *not hiring probabilities*. A listing link returning HTTP 200 is not absolute proof the job has not been filled; always confirm on the original page.

## Run locally

Requirements: Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set SECRET_KEY in your shell (or load the .env using `set -a; source .env; set +a`)
python app.py
```

Open `http://localhost:8080`. `/health` returns `{ "status": "ok" }`.

## Deploy from GitHub to Railway

1. Railway → **New Project → Deploy from GitHub Repo** → choose `ulascanatilgan-rgb/jobfitly`.
2. Add a persistent **volume mounted at `/data`**. This is mandatory for SQLite user accounts, watchlists and history.
3. Under **Variables**, set:

| Variable | Example / meaning |
| --- | --- |
| `SECRET_KEY` | Required: random 48+ character secret. Never commit it. |
| `DATABASE_PATH` | `/data/jobfitly.sqlite3` |
| `COOKIE_SECURE` | `1` (HTTPS only) |
| `APP_TIMEZONE` | `Europe/Brussels` |
| `OPENAI_API_KEY` | Required for Run and AI application drafts; paid OpenAI API account needed. |
| `OPENAI_MODEL` | `gpt-4.1-mini` for CV and motivations (Chat Completions). |
| `OPENAI_SEARCH_MODEL` | `gpt-4.1-mini` for Responses API web_search; optional override. |
| `MAX_JOB_AGE_DAYS` | `14` (1–30; job recency filter) |

4. Railway detects Python dependencies with **Railpack**. `railway.json` includes a Gunicorn start command and health check.
5. Generate a Railway domain and check `/health`, then test registration, CV upload, profile save, Run and PDF export.

### Job sources

- **OpenAI Responses API web_search:** searches the public web for relevant vacancies when Run is clicked. No Adzuna key needed.
- Candidate CV excerpt (with simple contact redaction), 15 skill ratings and search preferences shape the search. Published dates must be recent; the exact listing URL must appear in web-search sources and return HTTP 200. This is best-effort, **not a guarantee the vacancy is still open**.
- Search prioritizes employer-hosted career pages. No LinkedIn/Indeed scraping. Verify site and indexing terms before public launch.
- **JobFitly shows fewer than five rather than inventing jobs**. A run with no verified matches is not consumed.
- OpenAI web search charges per tool call and model tokens. The total depends on how many searches the model chooses to make: set an API budget and monitor usage.

### Important limitations before launch

This is an **MVP**, not a fully audited public SaaS. Before inviting users, implement email confirmation/password reset, robust login throttling and bot controls, backups with retention and disaster recovery, GDPR privacy / data-processing documentation, user consent to send CV text to OpenAI, monitoring, secure handling of sensitive CV data, and manual/live-source QA. For scaling, move from single-file SQLite to managed PostgreSQL and encrypted storage.

Users can delete their account and its stored CV text, saved jobs, runs, and generated application drafts. Original CV uploads are discarded after text extraction.

## Development

```bash
python -m py_compile app.py
node --check static/app.js
pytest -q
```

Stack: Flask, Gunicorn, SQLite, ReportLab, pypdf, python-docx, optional OpenAI web_search.

Brand: white `#FFFFFF`, near-black `#131313`, burgundy `#850D45`, Manrope typeface, approved JobFitly. wordmark.