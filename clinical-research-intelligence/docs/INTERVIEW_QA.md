# Questions the interviewer can ask

Each question has: **Fresher-friendly answer** and **Example from this project**. Read the code behind each example once so you can show it.


## Python

**1. What is a dictionary and why did you use it so much?**

- **Answer:** A dictionary stores key-value pairs, like a form with labelled fields. It is the natural Python shape for JSON.
- **Example from this project:** `parse_nct_html()` returns `{"study_title": ..., "eligibility": {"inclusion": ...}}`. Comparing two dictionaries is how I find changes.

**2. What does your `flatten()` function do and why is it needed?**

- **Answer:** It turns nested dictionaries into one level using dotted names, so one simple loop can compare every field.
- **Example from this project:** `{"eligibility": {"inclusion": "x"}}` becomes `{"eligibility.inclusion": "x"}` in `nct_comparator.py`.

**3. How do you handle errors in Python?**

- **Answer:** With `try/except`, and by raising my own exception with a friendly message when something predictable goes wrong.
- **Example from this project:** Services raise `ServiceError("PubMed is not reachable...", 503)`; `main.py` converts it to clean JSON so the user never sees a stack trace.

**4. Why did you use regular expressions?**

- **Answer:** Regex finds patterns in text, e.g. numbers or IDs, when the exact words vary.
- **Example from this project:** `NCT\d{8}` finds the NCT ID; `DOSE_PATTERN` finds '200 mg ...' in intervention text; `split_criteria` finds 'Inclusion Criteria:' headings.


## FastAPI

**5. What is FastAPI and why not Flask?**

- **Answer:** FastAPI is a Python web framework that turns functions into API endpoints, validates input automatically with Pydantic and generates `/docs` for free. Flask also works; the spec allowed both. I chose FastAPI because the spec named it.
- **Example from this project:** `@router.post("/compare")` on a function in `app/api/nct.py` becomes the endpoint `POST /api/nct/compare`.

**6. What is a router?**

- **Answer:** A way to split endpoints into files and mount them in the main app.
- **Example from this project:** `nct.py`, `pubmed.py`, `trials.py` each have an `APIRouter`; `main.py` calls `app.include_router(...)` for each.

**7. What does `Depends(get_db)` do?**

- **Answer:** Dependency injection: FastAPI runs `get_db()` before the endpoint, passes the database session in, and closes it afterwards.
- **Example from this project:** Every endpoint that needs the DB has `db: Session = Depends(get_db)`.

**8. What is Pydantic used for?**

- **Answer:** To define the expected shape of incoming JSON. If it does not match, FastAPI replies 422 automatically.
- **Example from this project:** `TrialCompareRequest` requires 2-4 NCT IDs; sending 1 returns 422 (tested in `test_trials_validation`).


## SQL / SQLite

**9. Why SQLite?**

- **Answer:** It is a single file with no server to install - ideal for a prototype. SQLAlchemy lets me move to PostgreSQL later by changing `DATABASE_URL`.
- **Example from this project:** `data/app.db` holds all tables.

**10. What is a foreign key?**

- **Answer:** A column that points to a row in another table, linking them.
- **Example from this project:** `nct_versions.study_id` points to `nct_studies.id`, so one study has many versions.

**11. Why store some data as JSON text in a column?**

- **Answer:** For nested/variable data that I only read back whole, JSON text is simpler than many tables. I still use real columns for things I filter on.
- **Example from this project:** `ClinicalTrial.data_json` stores the whole parsed trial; `nct_id`, `phase`, `recruitment_status` are normal columns.


## BeautifulSoup / parsing

**12. How does your parser work?**

- **Answer:** Remove noise, collect every label/value pair (table rows, definition lists, headings + following text), map labels to field names with an alias table, then normalize values.
- **Example from this project:** `parse_nct_html()` in `nct_parser.py`; 'Overall Status' and 'Recruitment Status' both map to `recruitment_status`.

**13. How do you make the comparison ignore layout changes?**

- **Answer:** I compare extracted text, not HTML. Whitespace is collapsed, case is ignored, dash styles unified and lists compared without order.
- **Example from this project:** `nct_v2.html` has different tags, banners and spacing, yet only the 9 real changes are reported.

**14. What if the website changes its HTML?**

- **Answer:** The alias table is based on visible labels, which change less than tags. If a label is new, I add it to `ALIASES`. This is also why the official API is a more stable source.
- **Example from this project:** `/api/nct/fetch` falls back to the ClinicalTrials.gov API when the HTML has too few fields.


## REST APIs

**15. GET vs POST?**

- **Answer:** GET reads data without side effects; POST sends data to be processed or created.
- **Example from this project:** `GET /api/pubmed/search` vs `POST /api/nct/compare` (sends files).

**16. What do status codes 200, 400, 404, 422, 503 mean?**

- **Answer:** 200 OK; 400 client sent something wrong; 404 not found; 422 JSON failed validation; 503 an external service is unavailable.
- **Example from this project:** Empty search -> 400; unknown NCT ID -> 404; Groq key missing -> 503.

**17. How does the frontend call the backend?**

- **Answer:** JavaScript `fetch()` sends an HTTP request and reads the JSON reply.
- **Example from this project:** `api()` in `frontend/js/common.js` wraps `fetch` and turns errors into readable messages.


## ClinicalTrials.gov

**18. How do you get trial data?**

- **Answer:** From the free official API v2: `GET /api/v2/studies?query.intr=<drug>&query.cond=<disease>`. It returns JSON.
- **Example from this project:** `get_trials()` in `clinical_trials_service.py`.

**19. Why not scrape the website for trials?**

- **Answer:** The site is JavaScript-rendered, so plain HTML often has no data. The API is official, stable and structured.
- **Example from this project:** For the version tracker I still support HTML upload, because the task requires it.

**20. How did you get dosages and study duration?**

- **Answer:** Dosage with a regex over intervention/arm descriptions; duration by subtracting start and completion dates in months - plain Python, no AI.
- **Example from this project:** `DOSE_PATTERN` and `_months_between()`; NCT99000001: 2025-04 to 2027-12 = 32 months.


## PubMed

**21. How is PubMed searched?**

- **Answer:** NCBI E-utilities. `esearch` turns a query into PMIDs; `efetch` turns PMIDs into XML with all details.
- **Example from this project:** `search_pubmed()` then `get_pubmed_article()` then `parse_pubmed_xml()`.

**22. How do you get images?**

- **Answer:** Only open-access articles in PubMed Central have full text. I fetch the PMC XML, read each `<fig>` (label, caption, file name), download the image and save it locally; the DB stores only the path.
- **Example from this project:** `parse_pmc_xml()`, `download_image()`, `storage.save_figure()`.

**23. Why is the abstract sometimes in several parts?**

- **Answer:** Structured abstracts have several `AbstractText` tags (BACKGROUND, METHODS ...). I join them with their labels.
- **Example from this project:** `parse_pubmed_article()`.


## Groq / LLM

**24. Where exactly do you use AI and where not?**

- **Answer:** AI only interprets text Python already extracted: article summaries, trial explanations, figure interpretation. Parsing, comparison, storage and filtering are plain Python.
- **Example from this project:** Only `groq_service.py` talks to Groq.

**25. How does a Groq request work?**

- **Answer:** An HTTP POST with the API key in a header and a list of messages (system instructions + user text). I ask for JSON output and parse it.
- **Example from this project:** `GroqService._chat()`.

**26. How do you reduce hallucinations?**

- **Answer:** The system prompt says use only the given text and answer 'Not stated' if unsure, temperature is low (0.2), output keys are fixed, and the UI labels results as AI-generated.
- **Example from this project:** `summarize_article()` prompt; `_with_defaults()`.

**27. Is your figure analysis really multimodal?**

- **Answer:** Yes when the image file was downloaded - I send the image (base64) plus caption to Llama 4 Scout and label it 'image+caption'. Otherwise it falls back to caption/context-only and says so on screen.
- **Example from this project:** `analyze_figure()` returns `analysis_type`; tested in `test_figure_mode_is_labelled_honestly`.

**28. How do you protect the API key?**

- **Answer:** It lives in `.env`, which is git-ignored. The code reads it with `os.getenv`; `/api/health` only says true/false and error messages never contain it.
- **Example from this project:** `config.py`, `.gitignore`, `.env.example`.


## Database design

**29. Explain your NCT tables.**

- **Answer:** `NCTStudy` is one trial; `NCTVersion` is each saved snapshot (raw file path + extracted JSON); `NCTChange` is each detected difference between two versions.
- **Example from this project:** Study NCT99000001 has versions 1 and 2 and 9 change rows.

**30. How do you avoid duplicate versions or articles?**

- **Answer:** A SHA-256 hash of the extracted JSON identifies identical versions; PMID and NCT ID are unique columns and I use upsert logic.
- **Example from this project:** `save_version()`, `save_publication()`, `save_trial()`.

**31. Why not store images in SQLite?**

- **Answer:** Databases are poor at big files. Files go to storage (local now, S3/R2 later) and the DB keeps a reference.
- **Example from this project:** `Figure.local_path`; swap `storage.py` for boto3 later.


## Architecture

**32. Why separate api / services / models?**

- **Answer:** Separation of concerns: endpoints handle HTTP, services contain logic (easy to test without a server), models define data.
- **Example from this project:** `compare_nct_versions()` is tested without FastAPI.

**33. How did you make the demo reliable without internet?**

- **Answer:** Bundled sample data and a 'Use sample data' option that uses the same parsing and storage code.
- **Example from this project:** `data/sample/*` and the `use_sample` parameter.

**34. How would you add scheduled monitoring?**

- **Answer:** A scheduler (APScheduler or a cron job) calling the same `/api/nct/fetch` logic daily, plus email alerts when `change_count > 0`.
- **Example from this project:** Listed in Future Improvements.


## Deployment

**35. How do you deploy it?**

- **Answer:** Render web service: build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, and add `GROQ_API_KEY` and the Supabase `DATABASE_URL` as environment variables. FastAPI also serves the frontend.
- **Example from this project:** README section 14.

**36. What is the problem with SQLite on free hosting?**

- **Answer:** Render's disk is temporary, so a SQLite file would be lost on restart. That is why the cloud version uses Supabase PostgreSQL - only `DATABASE_URL` changes.
- **Example from this project:** SQLAlchemy models stay the same.


## Project-specific

**37. What was the hardest part?**

- **Answer:** Making comparison meaningful: separating real changes from layout noise, and handling lists and multi-line text so the log shows exactly which item was added or removed.
- **Example from this project:** `added_items` / `removed_items` in `compare_nct_versions()`.

**38. What would you improve with more time?**

- **Answer:** Live-test and harden the external APIs, add PostgreSQL and S3, scheduled monitoring, trial similarity scoring and better figure handling.
- **Example from this project:** README section 16.

**39. How do you know your code works?**

- **Answer:** 37 automated tests (parser, comparison, PubMed parsing, trial parsing, mocked Groq, API endpoints) plus a repeatable sample demo.
- **Example from this project:** `pytest`.

**40. What are the limitations?**

- **Answer:** LLM output can be wrong; figures exist only for open-access articles; JS-only trial pages need the API; the live APIs still need a first run on a networked machine.
- **Example from this project:** README section 15.


---
Total questions: 40
