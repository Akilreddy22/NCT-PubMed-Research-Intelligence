# Demo script (about 14 minutes)

Before you start: `python run.py`, open http://127.0.0.1:8000 in a browser, put your `GROQ_API_KEY` in `.env` (dashboard must say **Groq connected**). Have `docs/screenshots` open as a backup if something fails.

| Time | What to click | What to say |
|---|---|---|
| **0:00 - 1:00 Introduction** | Dashboard `/` | "This is a clinical research intelligence tool with three modules: NCT change tracking, PubMed analysis and a clinical trial comparator. It is built with Python, FastAPI, SQLite and the Groq API." |
| **1:00 - 2:00 Problem** | Stay on dashboard | "Trial pages change often and researchers cannot see what changed. Comparing many trials and reading papers by hand is slow." |
| **2:00 - 4:00 Architecture** | Show the architecture slide (slide 5) | "The browser calls FastAPI. FastAPI calls services - parser, comparator, PubMed and ClinicalTrials.gov clients. Everything is stored in SQLite. Only one file, `groq_service.py`, talks to the AI." |
| **4:00 - 7:00 NCT demo** | `/nct` -> **Run sample comparison** | "I have two versions of the same trial page. The parser extracts fields, normalizes them and my comparison function reports 9 changes." Point at *Eligibility > Inclusion* (Age 18-65 -> 18-70), *Recruitment Status*, *Enrollment 100 -> 120*. Click **Side-by-side**. Say: "The HTML also had different tags and banners, but they are ignored because I compare extracted text. No AI here." Scroll to *Detailed change history* and show the version drop-downs. |
| **7:00 - 9:00 PubMed demo** | `/pubmed` -> search "cancer immunotherapy" (or tick sample) -> **View details** -> **Analyze with Groq** | "PubMed is searched with the official E-utilities API, XML is parsed with Python and saved in SQLite. The Groq model then gives a summary, key findings, study type and population from the abstract." |
| **9:00 - 9:45 Figures** | Click **Get full text & figures** (or show sample captions) -> **Analyze figure** | "If the article is open access I download figures. If I have the image, the model sees image + caption. If not, it uses caption and context only and the screen says 'caption/context-based'. I do not fake image analysis." |
| **9:45 - 12:00 Trial comparison** | `/trials` -> Drug *Pembrolizumab*, Indication *Melanoma* -> Search -> tick 3 trials -> **Explain selected with Groq** -> **Compare selected** | "Python extracted drug, dose, arms, phase, design, criteria, outcomes, duration and sites. Groq only explains what each trial is trying to do." Tick *Show only rows that differ*. "Yellow rows show where trials differ - phase, design, population, outcomes." |
| **12:00 - 13:00 AI usage** | Slide 13 | "Parsing, normalization, comparison, storage, filtering and API calls are deterministic Python. The LLM is only an additional layer for summarization and interpretation." |
| **13:00 - 13:40 Database** | Slide 10 or DB Browser | "Studies have versions and changes; publications have authors, figures and AI analyses; trials have analyses. Images are stored as files, not in SQLite." |
| **13:40 - 14:30 Future** | Slide 15 | "Next: PostgreSQL, S3/R2, scheduled monitoring with email alerts, trial similarity and better figure analysis. Honest limitation: live APIs were developed from documentation and sample data, and Groq output must be reviewed by a human." |

## If something breaks
- No internet -> tick **Use sample data** everywhere (NCT demo always works).
- Groq error "rate limit" -> wait a minute; trial analyses already made are cached.
- Groq "model not found" -> update `GROQ_MODEL` in `.env`.
