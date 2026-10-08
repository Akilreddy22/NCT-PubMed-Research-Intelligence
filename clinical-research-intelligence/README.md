# NCT & PubMed Research Intelligence Platform

A beginner-friendly clinical research monitoring tool built with **Python, FastAPI, SQLite, SQLAlchemy, BeautifulSoup and the Groq API**.

> **One sentence for the interview:** *The core extraction and comparison logic is deterministic Python code. The LLM (Groq) is only an extra intelligence layer for summarization and interpretation.*

---

## 1. Project overview
Researchers waste time re-reading ClinicalTrials.gov and PubMed. This app:

1. **NCT Change Log** - shows *exactly* what changed between two versions of a trial page (field, old value, new value, date, version).
2. **PubMed Intelligence** - searches PubMed, stores articles/authors/figures in SQLite, and asks Groq for a summary, key findings and figure interpretation.
3. **Clinical Trial Comparator** - enter *Drug + Indication*, get matching trials and a side-by-side comparison table, with Groq explaining each trial's purpose.

## 2. Features
| Module | Done with plain Python (no AI) | Done with Groq |
|---|---|---|
| NCT | HTML parsing, normalization, version storage, change detection, history | - |
| PubMed | E-utilities search, XML parsing, PMC figures, SQLite, image download | Summary, key findings, population, methodology, figure/caption interpretation |
| Trials | API call, field extraction, dosage regex, duration maths, comparison table, highlighting differences | The 7 "what is this trial about" answers |

## 3. Architecture
```
Browser (HTML/CSS/JS)  ->  FastAPI  ->  services (parsers, comparator, API clients)  ->  SQLite
                                                          |
                                                          +-> GroqService (only AI code)
```
```
app/api/*.py        endpoints (receive request, call services, return JSON)
app/services/*.py   the real logic (parser, comparator, PubMed/CT.gov clients, Groq)
app/models/*.py     SQLAlchemy tables
app/schemas/*.py    Pydantic request validation
frontend/           plain HTML/CSS/JS served by FastAPI
```
Database tables: `NCTStudy 1-* NCTVersion`, `NCTStudy 1-* NCTChange` · `Publication 1-* Author / Figure / AIAnalysis` · `ClinicalTrial 1-* TrialAnalysis`.

## 4. Technology stack
Python 3.10+, FastAPI, SQLAlchemy 2, Pydantic, SQLite, BeautifulSoup4, httpx, python-dotenv, Groq REST API, vanilla JS.
(We call Groq with `httpx` directly instead of an SDK so you can see and explain the raw HTTP request.)

## 5. Folder structure
```
clinical-research-intelligence/
|-- app/ (main.py, config.py, database.py, errors.py, api/, models/, schemas/, services/)
|-- frontend/ (index.html, nct.html, pubmed.html, trials.html, css/, js/)
|-- data/
|   |-- sample/  nct_v1.html  nct_v2.html  sample_pubmed.json  sample_trial.json   <- offline demo data
|   |-- nct/  figures/  pubmed/   <- created files (raw HTML versions, figure images)
|-- tests/   docs/   run.py   requirements.txt   .env.example   README.md
```

## 6. Installation
```bash
python -m venv venv
venv\Scripts\activate          # Windows        (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
```

## 7. Environment variables
Copy `.env.example` to `.env` and edit. **Never commit `.env`** (it is in `.gitignore`).
| Variable | Meaning |
|---|---|
| `GROQ_API_KEY` | your Groq key (never hard-coded) |
| `GROQ_MODEL` | text model, default `llama-3.3-70b-versatile` |
| `GROQ_VISION_MODEL` | image model, default `meta-llama/llama-4-scout-17b-16e-instruct` |
| `DATABASE_URL` | default `sqlite:///./data/app.db`; for the cloud use your Supabase PostgreSQL URL (section 9) |
| `NCBI_EMAIL`, `NCBI_API_KEY` | optional, make PubMed calls more polite/faster |
| `S3_*` | optional, not used in v1 (figures are saved locally) |

## 8. Groq API setup
1. Create a free account at https://console.groq.com and open **API Keys** -> *Create API Key*.
2. Put it in `.env`: `GROQ_API_KEY=gsk_...`
3. Restart the app. The dashboard shows **"Groq connected"**.
4. Free tier has rate limits: if you see *"rate limit reached"*, wait a minute. Model names change over time - if you get a "model not found" error, check https://console.groq.com/docs/models and update `GROQ_MODEL` / `GROQ_VISION_MODEL` in `.env`.

## 9. Database setup
**Local (default):** SQLite - nothing to do. Tables are created automatically at startup (`init_db()`); delete `data/app.db` to reset.

**Cloud (Supabase PostgreSQL):** the same code runs on PostgreSQL, you only change `DATABASE_URL`.
1. Create a free project at https://supabase.com (remember the database password).
2. Click **Connect** at the top of the dashboard and copy the **Session pooler** connection string
   (looks like `postgresql://postgres.<ref>:<PASSWORD>@aws-0-<region>.pooler.supabase.com:5432/postgres`).
   Use the pooler, not the "Direct connection": the direct host is IPv6-only and Render's free tier cannot reach it.
3. Put it in `.env` (local test) or in Render's Environment tab as `DATABASE_URL`. If the password has special characters (`@ : / #`), URL-encode them (`@` -> `%40`).
4. Start the app. Tables are created automatically; see them in Supabase **Table Editor**.
`database.py` converts `postgres://` to `postgresql+psycopg2://`, turns on SSL and reconnects automatically if an idle connection was closed.

## 10. Running locally
```bash
python run.py        # open http://127.0.0.1:8000    (API docs: /docs)
```

## 11. API endpoints
| Method & path | What it does |
|---|---|
| `GET /api/health` | Is the app up? Is Groq configured? (never returns the key) |
| `GET /api/stats` | Counts for the dashboard |
| `POST /api/nct/upload` | Upload ONE html file -> parsed -> stored as a new version |
| `POST /api/nct/compare` | Upload previous + current html -> change log |
| `POST /api/nct/compare-versions` | Compare two already-stored versions of a study |
| `POST /api/nct/fetch` | Give a clinicaltrials.gov URL -> download, store, compare with previous version |
| `POST /api/nct/demo` | Compare the bundled sample v1 vs v2 |
| `GET /api/nct` , `GET /api/nct/{nct_id}` | List studies / versions + change history |
| `GET /api/pubmed/search?query=&max_results=&use_sample=` | Search PubMed, store articles |
| `GET /api/pubmed/article/{pmid}` | One stored article (authors, figures, AI analysis) |
| `POST /api/pubmed/analyze` | Groq summary of an abstract (`{"pmid": ...}` or `{"abstract": ...}`) |
| `POST /api/pubmed/figures` | Get PMC full text + figure list + download images |
| `POST /api/pubmed/analyze-figure` | Groq analysis of one figure |
| `GET /api/trials/search?drug=&indication=&days=&use_sample=` | Search ClinicalTrials.gov, parse, store |
| `GET /api/trials/{nct_id}` | One stored trial |
| `POST /api/trials/analyze` | Groq explains the selected trials (cached in SQLite) |
| `POST /api/trials/compare` | Build the comparison table for 2-4 trials |

## 12. Demo instructions
Everything below works **offline** using `data/sample/`. See `docs/DEMO_SCRIPT.md` for the minute-by-minute script.
1. `/nct` -> **Run sample comparison** -> 9 changes (age 18-65 -> 18-70, status, enrollment ...).
2. `/pubmed` -> tick *Use sample data* -> Search -> open an article -> **Analyze with Groq** (needs key).
3. `/trials` -> tick *Use sample data* -> Search -> **Compare selected**.

## 13. Testing
```bash
pytest
```
37 tests: NCT parser, NCT comparison, PubMed XML parsing, trial parsing + comparison, Groq service (HTTP mocked - no real calls), API endpoints.

## 14. Deployment (Render + Supabase, all in the cloud)
1. Push the project to GitHub (check `.env` is NOT in the repo).
2. Create the Supabase project and copy the **Session pooler** URL (section 9).
3. On https://render.com -> **New > Web Service** -> connect the repo.
4. Build command: `pip install -r requirements.txt` - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. In Render's **Environment** tab add `DATABASE_URL` (Supabase URL) and `GROQ_API_KEY`.
6. Deploy and open the Render URL. FastAPI serves the frontend too, so there is nothing else to host.

**What persists:** all structured data (studies, versions, changes, articles, trials, AI results) is in Supabase, so it survives restarts. **What does not:** files written to Render's disk - the raw HTML copies in `data/nct/` and downloaded figure images in `data/figures/` (the extracted data is in the database, so comparisons still work, but figure thumbnails disappear after a restart). The next step is to move `app/services/storage.py` to Supabase Storage or Cloudflare R2 (both S3-compatible, via boto3).
Free Render services sleep after inactivity, so the first request can take ~30-60 s - open the site before your demo.

## 15. Limitations (be honest in the demo)
- **Live APIs were not reachable from the build environment**, so the live PubMed / ClinicalTrials.gov / Groq calls were written from the official docs and tested with mocks + sample data. First thing to do on your machine: run one live search of each and fix any small issue.
- ClinicalTrials.gov pages are rendered by JavaScript, so the downloaded HTML is often empty. The app detects this and uses the official API for the same study (labelled `fetched_via: api`). Comparing an HTML-sourced version with an API-sourced version can show formatting differences - the UI warns you.
- **Figure analysis:** Groq's Llama 4 Scout accepts images, so figures are analyzed as *image + caption* when the image file could be downloaded. If there is no image (or the image call fails) the app falls back to **caption/context-based analysis** and labels it as such. Only open-access PubMed Central articles expose figures; the PMC image URL pattern is best-effort.
- The sample NCT IDs/PMIDs are **synthetic** (NCT990000xx / PMID 990000xx).
- LLM output can be wrong. The prompts say "use only the given text / write 'Not stated'", but results should be reviewed by a human.
- Images are stored locally, not in S3/R2 (see `app/services/storage.py` - only that file changes later).

## 16. Future improvements
S3/R2 or Supabase Storage for images and raw HTML, scheduled monitoring (APScheduler) with email alerts, trial similarity scoring, better figure/table OCR, authentication, analytics dashboard, richer search filters.
