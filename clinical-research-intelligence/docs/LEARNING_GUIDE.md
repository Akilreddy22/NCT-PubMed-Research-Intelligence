# Learning guide - the 12 phases explained

For each phase: **What / Why / Files / How to run / Expected output / Test / Common errors.**
All phases are already implemented in this project; read them in order and re-type the code yourself to learn it.

## Plain-language glossary
- **FastAPI** = receives requests from the frontend and calls Python functions.
- **SQLite** = stores our structured data in one local file (`data/app.db`).
- **SQLAlchemy** = lets Python talk to SQLite using classes (models) instead of SQL text.
- **Pydantic** = checks that incoming JSON has the right shape (e.g. `url` must be a string).
- **BeautifulSoup** = reads HTML and lets Python find the useful pieces.
- **REST API** = URLs that return data (JSON). `GET` reads, `POST` sends data.
- **httpx** = Python library that makes HTTP requests (like a browser, without a screen).
- **Groq** = hosted LLM service used only for summarizing/interpreting text.
- **S3/R2** = cloud file storage. We start with local folders; only `storage.py` changes later.

---
## Phase 1 - Project setup, FastAPI, SQLite, health endpoint
**What:** folders, virtual environment, `requirements.txt`, `app/main.py`, `app/database.py`, `app/config.py`, `/api/health`, basic pages.
**Why:** a clean skeleton makes every later phase "add a file". `config.py` reads `.env` once so no key is hard-coded.
**Key code:** `create_engine(url)` opens the DB; `SessionLocal()` is one DB conversation; `get_db()` gives a session to each request and closes it; `Base.metadata.create_all()` creates tables.
**Run:** `python run.py` -> open http://127.0.0.1:8000/api/health
**Expected:** `{"status":"ok","groq_configured":false}` (true once your key is in `.env`).
**Test:** `pytest tests/test_api.py::test_health`
**Common errors:** `ModuleNotFoundError: app` -> run commands from the project root. `Address already in use` -> another server is on port 8000; close it or change the port in `run.py`.

## Phase 2 - NCT parser
**What:** `parse_nct_html(html) -> dict` in `app/services/nct_parser.py`.
```
HTML -> BeautifulSoup -> remove noise -> collect label/value "blocks" -> map aliases -> normalize -> dict -> SQLite
```
**How it works:** (1) delete `<script>/<style>/<nav>/banners`; (2) read every table row `th|td`, `dt|dd`, and every heading plus the text under it; (3) look labels up in `ALIASES` ("overall status" -> `recruitment_status`); (4) clean values - `"100 participants"` -> `100`, split "Inclusion/Exclusion Criteria".
**Run:** `python -c "from app.services.nct_parser import parse_nct_html; import json; print(json.dumps(parse_nct_html(open('data/sample/nct_v1.html').read()), indent=1))"`
**Test:** `pytest tests/test_nct_parser.py`
**Common errors:** field is empty -> the page uses a label that is not in `ALIASES`; add it. `NCT ID` empty -> regex `NCT\d{8}` found nothing.

## Phase 3 - NCT comparison
**What:** `compare_nct_versions(previous, current)` in `nct_comparator.py`.
**How:** flatten nested dicts (`eligibility.inclusion`), then for each field: empty->value = *added*, value->empty = *removed*, different = *modified*. "Different" is decided on a normalized copy (lower case, same dash, single spaces, lists order-insensitive) so layout noise is ignored.
**Run:** click **Run sample comparison** on `/nct`. **Expected:** 9 modified fields incl. `Eligibility > Inclusion: Age 18-65 -> Age 18-70`.
**Test:** `pytest tests/test_nct_comparison.py`

## Phase 4 - Fetch from URL + version storage
**What:** `POST /api/nct/fetch`. Validates the URL (must be clinicaltrials.gov), downloads HTML, parses it; if almost nothing was found (JavaScript-only page) it uses the official API instead. Saves a new `NCTVersion` (raw file in `data/nct/`, JSON in DB), compares with the previous version, saves `NCTChange` rows.
**Tables:** `NCTStudy (1) -> (many) NCTVersion`; `NCTChange` points to the study and to the two versions compared.
**Common errors:** *Invalid URL* (not clinicaltrials.gov); *HTTP 403/503* (no internet / blocked) -> friendly message shown.

## Phase 5 - PubMed search
**What:** `search_pubmed(query)` calls `esearch.fcgi` -> list of PMIDs. `get_pubmed_article(pmids)` calls `efetch.fcgi` -> XML. `parse_pubmed_article(element)` -> dict (title, abstract parts joined, authors, journal, date, DOI, PMCID, keywords, study type from PublicationType, topic from MeSH, references).
**Run:** `/pubmed` -> search "cancer immunotherapy" (or tick sample).
**Test:** `pytest tests/test_pubmed.py`
**Common errors:** HTTP 429 -> too many calls (we wait 0.4 s between calls; add `NCBI_API_KEY` to go faster).

## Phase 6 - Store PubMed in SQLite
`save_publication()` inserts or updates by PMID (so re-searching never duplicates), replaces authors, adds new figures. `publication_to_dict()` converts DB rows to JSON for the browser.

## Phase 7 - Groq integration
**Request:** `POST https://api.groq.com/openai/v1/chat/completions` with header `Authorization: Bearer <key>` and body `{"model", "messages":[system, user], "response_format":{"type":"json_object"}}`.
**Reply:** `choices[0].message.content` is a JSON string -> `json.loads` -> dict. The **system prompt** says "use only the given text, write 'Not stated' if unknown, return exactly these keys". `_with_defaults` guarantees every key exists.
**Endpoint:** `POST /api/pubmed/analyze` body `{"pmid":"99000001"}` or `{"abstract":"..."}`.
**Errors handled:** no key (503), bad key (401), rate limit (429), network (503), invalid JSON (502).

## Phase 8 - Clinical trial search
`get_trials(drug, indication)` -> ClinicalTrials.gov API v2 (`query.intr`, `query.cond`, optional `filter.advanced=AREA[LastUpdatePostDate]RANGE[date,MAX]` for "last 30 days"). `parse_trial(study)` does *all* extraction in Python: drugs, dosages (regex), arms, phase, design, enrollment, criteria split, outcomes, duration in months, sites, sponsor. `save_trial()` upserts into `clinical_trials`.

## Phase 9 - Groq trial understanding
`build_trial_text(data)` makes a compact text of the *already extracted* data; `GroqService.analyze_trial()` returns 7 answers (investigating, intervention, indication, population, primary_objective, differentiator, development_stage). Saved in `trial_analyses` so the same trial is never paid for twice.

## Phase 10 - Comparison UI
`build_comparison()` (Python) creates one row per category and sets `differs=True` when values are not all equal. JS only draws it; yellow rows = differences; checkbox "show only differences".

## Phase 11 - Figures
`POST /api/pubmed/figures`: if the article has a PMC id -> download JATS XML -> `<fig>` tags give label, caption, image file -> download image -> `storage.save_figure()` (local folder; DB keeps only the path). `POST /api/pubmed/analyze-figure`: if the image file exists -> multimodal call (Llama 4 Scout) with image + caption + context, label **image+caption**; otherwise caption/context-only, label **caption/context-based**. The label is shown in the UI so the demo stays honest.

## Phase 12 - Tests
`pytest` -> 37 tests. Groq tests replace `httpx.post` with a fake, so they are free and need no key. API tests use a temporary DB (`tests/conftest.py`).
