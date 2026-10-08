# PPT speaker notes
Each slide: what is on it, what to say, a possible interviewer question and a simple answer.

## Slide 1 - Title

**What is on the slide:** Project name, subtitle, and the tech stack line.

**What I should say:** Hello, I'm presenting the NCT & PubMed Research Intelligence Platform. It helps researchers see what changed on clinical trial pages, understand PubMed papers, and compare clinical trials. I built it with Python, FastAPI, SQLite and the Groq API.

**Possible interviewer question:** Why did you choose this project structure / stack?

**Simple answer:** The assignment named Python, FastAPI and SQLite, so I used those. I kept everything simple so I can explain every part: plain Python for the logic and an LLM only where it adds value.

## Slide 2 - Problem Statement

**What is on the slide:** Five pain points researchers face with ClinicalTrials.gov and PubMed.

**What I should say:** Researchers manually review ClinicalTrials.gov and PubMed. Trial pages change over time, but the site only says 'updated' - it does not show exactly what changed. Comparing many trials by hand is slow, and papers contain a lot of unstructured text. My project automates these four things.

**Possible interviewer question:** Who is the user of this system?

**Simple answer:** A clinical researcher or analyst who monitors a drug or disease area and wants a quick, structured view instead of opening dozens of pages.

## Slide 3 - Project Objective

**What is on the slide:** Three modules: NCT change tracking, PubMed research intelligence, clinical trial comparator.

**What I should say:** The platform has three modules inside one FastAPI application. Module 1 tracks versions of an NCT page and lists exact changes. Module 2 searches PubMed, stores articles and uses AI to summarize them. Module 3 takes a drug and an indication and shows a side-by-side comparison of trials.

**Possible interviewer question:** Are the three modules connected?

**Simple answer:** They share one database, one UI and one AI service. Module 1 and 3 both use ClinicalTrials.gov data and the same field names, so a trial can be tracked and compared.

## Slide 4 - Proposed Solution

**What is on the slide:** Three pipelines: NCT change log, PubMed AI summary, trial comparison. Violet boxes use Groq AI; teal boxes are plain Python.

**What I should say:** Each module is a pipeline. For NCT: download, parse, store in SQLite, compare, show the change log - no AI. For PubMed: extract article data, store it, then Groq produces the summary. For trials: extract in Python, store, Groq explains each trial, and the comparison table is built by Python.

**Possible interviewer question:** Why store data in a database instead of just comparing live?

**Simple answer:** To keep history. To say 'what changed' I must have the older version saved, and storing parsed data also avoids calling the APIs again and again.

## Slide 5 - Overall Architecture

**What is on the slide:** User, HTML/JS UI, FastAPI, three modules, external sources, SQLite, Groq service. Legend shows AI vs non-AI.

**What I should say:** The user works in a plain HTML/JavaScript UI. It calls FastAPI. FastAPI routes the request to a module, which calls ClinicalTrials.gov or PubMed, saves results in SQLite, and only when needed calls the Groq service. Teal means plain Python, violet means AI. All AI code is in one file.

**Possible interviewer question:** Why is all Groq code in one file?

**Simple answer:** It keeps the AI layer replaceable and easy to test - I can swap the model or provider by changing one file, and tests can fake it.

## Slide 6 - Technology Stack

**What is on the slide:** Table of layers and technologies, plus a note on simplicity.

**What I should say:** Python and FastAPI for the backend, SQLAlchemy with SQLite locally and PostgreSQL on Supabase in the cloud, Pydantic for validation, BeautifulSoup for HTML parsing. Data comes from the official PubMed and ClinicalTrials.gov APIs. Groq provides the LLM. The frontend is plain HTML, CSS and JavaScript, deployed on Render.

**Possible interviewer question:** Why SQLite?

**Simple answer:** SQLite needs no server, so it is ideal for local development and tests. For the cloud I use Supabase PostgreSQL by changing only DATABASE_URL, because SQLAlchemy hides the difference.

## Slide 7 - NCT Change Detection

**What is on the slide:** Both HTML versions go through the parser to normalized JSON, then compare. Example: eligibility age changed from 18-65 to 18-70 - MODIFIED.

**What I should say:** Both versions are parsed into the same dictionary shape. Parsing removes banners, scripts and layout, collapses whitespace and ignores case. Then my compare function flattens the dictionaries and labels each field added, removed or modified, with the old value, new value, time and version numbers. This is plain Python - no AI.

**Possible interviewer question:** How do you avoid false changes when only the layout changed?

**Simple answer:** I compare extracted, normalized text rather than HTML. In my sample, the second page has different tags and banners, but only the 9 real changes are reported.

## Slide 8 - PubMed Module

**What is on the slide:** Pipeline: search, PubMed API, article metadata, SQLite, Groq, summary and key findings. Note on figures.

**What I should say:** I search with the official NCBI E-utilities: esearch returns article IDs and efetch returns XML. I parse the XML in Python and save publications, authors and figures in SQLite. Groq then summarizes the abstract. For open-access articles I also download figures; if the image is available the model sees the image plus caption, otherwise only caption and context, and the UI says which one was used.

**Possible interviewer question:** Can the AI really read images?

**Simple answer:** Groq's Llama 4 Scout model accepts images, so yes when I have the image file. When I don't, I do not pretend - the result is labelled caption/context-based.

## Slide 9 - Clinical Trial Comparator

**What is on the slide:** Pipeline from drug + indication to comparison table, and what Python extracts versus what Groq answers.

**What I should say:** The researcher enters a drug and an indication. I call the ClinicalTrials.gov API, and Python extracts drugs, doses, arms, phase, design, criteria, outcomes, duration and locations. Groq only answers seven standard questions such as what the trial investigates and what makes it different. The table and the highlighting of differences are also plain Python.

**Possible interviewer question:** Why not let the AI extract the trial fields too?

**Simple answer:** Structured fields are better and cheaper to extract with normal code - it is exact, testable and does not hallucinate. AI is for interpretation, which code cannot do.

## Slide 10 - Database Design

**What is on the slide:** Tables grouped by module with one-to-many relationships.

**What I should say:** Module 1: one study has many versions and many changes. Module 2: one publication has many authors, figures and AI analyses. Module 3: one trial has analyses. Images are saved as files and the database only keeps their path. Full parsed trials are stored as JSON text plus a few real columns for filtering.

**Possible interviewer question:** What is a one-to-many relationship?

**Simple answer:** One row in a table is linked to many rows in another - for example one NCT study has many versions. It is implemented with a foreign key such as study_id.

## Slide 11 - API Architecture

**What is on the slide:** Table of the main endpoints, with method, path and purpose.

**What I should say:** FastAPI exposes REST endpoints. POST /api/nct/compare takes two HTML files and returns the change log. GET /api/pubmed/search searches PubMed. POST /api/pubmed/analyze sends an abstract to Groq. GET /api/trials/search finds trials, and POST /api/trials/compare returns the comparison table. /docs shows all of them interactively.

**Possible interviewer question:** What is the difference between GET and POST?

**Simple answer:** GET only reads data. POST sends data, such as files or JSON, for the server to process.

## Slide 12 - User Interface

**What is on the slide:** Four real screenshots: dashboard, NCT change log, PubMed article detail, trial comparison.

**What I should say:** The UI is plain HTML, CSS and JavaScript served by FastAPI. The dashboard shows counts and shortcuts. The NCT page shows a change table with side-by-side view. The PubMed page shows the abstract, AI summary and figures. The trial page shows a comparison table where rows that differ are highlighted.

**Possible interviewer question:** Why not use React?

**Simple answer:** The UI is simple, and plain JavaScript keeps the project easy to understand and deploy as one app. React would add tooling without much benefit here.

## Slide 13 - AI Usage

**What is on the slide:** Two columns: what is done without AI (Python) and what is done with Groq.

**What I should say:** This is the key slide. Parsing, extraction, normalization, version comparison, API calls, database work, filtering and the comparison table are normal Python. Groq is used only for article summaries, research interpretation, trial understanding, key findings and figure interpretation. The core engineering is deterministic code; the LLM is an extra intelligence layer.

**Possible interviewer question:** How do you control AI mistakes?

**Simple answer:** The prompt says to use only the given text and answer 'Not stated' if unsure; the output has fixed keys; results are labelled AI-generated; and the important comparison never depends on AI.

## Slide 14 - Demo Flow

**What is on the slide:** Three demos in order: NCT comparison, PubMed summary, trial comparison.

**What I should say:** Demo 1: compare two NCT versions and show the detected age change. Demo 2: search PubMed, open an article and get the Groq summary. Demo 3: search pembrolizumab with melanoma and compare three trials side by side. Everything also works offline with sample data.

**Possible interviewer question:** What if the internet fails during a demo?

**Simple answer:** I included sample NCT, PubMed and trial data, and a 'use sample data' option, so the demo runs without external APIs.

## Slide 15 - Future Enhancements

**What is on the slide:** Ten possible improvements.

**What I should say:** Next steps are S3, R2 or Supabase Storage for images, scheduled NCT monitoring with email alerts, better image analysis, authentication, advanced search, similarity-based trial discovery, cloud deployment and an analytics dashboard. I would also run the live APIs for a longer period and harden the parsers.

**Possible interviewer question:** What is the biggest limitation today?

**Simple answer:** The live external APIs need a networked test run and AI output needs human review. Files such as figure images are on Render's temporary disk and need S3-style storage; the data itself is safe in Supabase.
