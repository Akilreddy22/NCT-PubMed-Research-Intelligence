// Builds docs/Research_Intelligence_Demo.pptx and docs/PPT_SPEAKER_NOTES.md
// Run:  node tools/build_ppt.js     (needs the pptxgenjs package)
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");
const notes = require("./notes.js");
const { applyTheme } = require("/mnt/skills/public/pptx/scripts/apply_theme.js");

const ROOT = path.join(__dirname, "..");
const SHOT = n => path.join(ROOT, "docs", "screenshots", n);
const THEME = { name: "Clinical Teal", headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: "1B2733", lt1: "FFFFFF", dk2: "0F2A43", lt2: "E8F3F3", accent1: "0E7C86", accent2: "6D4AC4",
            accent3: "F2A33A", accent4: "2E8B57", accent5: "C0392B", accent6: "6B7C8F", hlink: "0E7C86", folHlink: "6D4AC4" } };

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";           // 10 x 5.625 inches
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "NCT & PubMed Research Intelligence Platform";
const C = pres.SchemeColor;
const AI_TINT = "EFE9FB";

pres.defineSlideMaster({ title: "TITLE_DARK", background: { color: C.text2 }, objects: [] });
pres.defineSlideMaster({
  title: "CONTENT", background: { color: C.background1 },
  slideNumber: { x: 9.2, y: 5.25, w: 0.5, h: 0.25, fontSize: 10, color: C.accent6, align: "right" },
  objects: [{ placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 9, h: 0.75, fontSize: 32, bold: true,
                                          color: C.text2, valign: "middle", align: "left", margin: 0 }, text: "" } }],
});

const KIND = {
  py:   { fill: C.accent1, color: C.background1 },
  ai:   { fill: C.accent2, color: C.background1 },
  db:   { fill: C.text2,   color: C.background1 },
  soft: { fill: C.background2, color: C.text1 },
  aiSoft: { fill: AI_TINT, color: C.text1 },
};
function box(s, text, x, y, w, h, kind = "soft", size = 13, opts = {}) {
  const k = KIND[kind];
  s.addText(text, Object.assign({ shape: pres.ShapeType.roundRect, rectRadius: 0.08, x, y, w, h, fill: { color: k.fill },
    color: k.color, fontSize: size, align: "center", valign: "middle", margin: 4, objectName: "box " + text.slice(0, 18) }, opts));
}
function arrow(s, x1, y1, x2, y2) {
  s.addShape(pres.ShapeType.line, { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1),
    flipH: x2 < x1, flipV: y2 < y1, line: { color: C.accent6, width: 1.75, endArrowType: "triangle" } });
}
function flow(s, labels, kinds, x, y, w, h, gap, size = 12) {
  const bw = (w - gap * (labels.length - 1)) / labels.length;
  labels.forEach((t, i) => {
    box(s, t, x + i * (bw + gap), y, bw, h, kinds[i], size);
    if (i < labels.length - 1) arrow(s, x + i * (bw + gap) + bw + 0.02, y + h / 2, x + (i + 1) * (bw + gap) - 0.02, y + h / 2);
  });
}
function content(title, idx) {
  const s = pres.addSlide({ masterName: "CONTENT" });
  s.addText(title, { placeholder: "title" });
  s.addNotes(`WHAT IS ON THE SLIDE\n${notes[idx].on}\n\nWHAT TO SAY\n${notes[idx].say}\n\nPOSSIBLE INTERVIEWER QUESTION\n${notes[idx].q}\n\nSIMPLE ANSWER\n${notes[idx].a}`);
  return s;
}
const legend = (s, x, y) => {
  box(s, "Plain Python (no AI)", x, y, 1.9, 0.32, "py", 11);
  box(s, "Groq AI", x + 2.05, y, 1.1, 0.32, "ai", 11);
};

// ---------- 1 Title
{
  const s = pres.addSlide({ masterName: "TITLE_DARK" });
  s.addNotes(`WHAT IS ON THE SLIDE\n${notes[0].on}\n\nWHAT TO SAY\n${notes[0].say}\n\nPOSSIBLE INTERVIEWER QUESTION\n${notes[0].q}\n\nSIMPLE ANSWER\n${notes[0].a}`);
  s.addText("NCT & PubMed Research Intelligence Platform", { x: 0.7, y: 1.2, w: 8.6, h: 1.6, fontSize: 40, bold: true, fontFace: "Cambria",
    color: C.background1, margin: 0, valign: "top", isTextBox: true });
  s.addText("Clinical Research Monitoring, Analysis & Trial Comparison", { x: 0.7, y: 3.0, w: 8.6, h: 0.5, fontSize: 20, color: C.background2, margin: 0, isTextBox: true });
  ["Python", "FastAPI", "SQLite", "BeautifulSoup", "Groq"].forEach((t, i) =>
    box(s, t, 0.7 + i * 1.5, 4.2, 1.35, 0.42, i === 4 ? "ai" : "py", 13));
}

// ---------- 2 Problem
{
  const s = content("Problem Statement", 1);
  const items = ["Researchers manually review ClinicalTrials.gov and PubMed", "Trial pages change over time",
    "Hard to see exactly what changed", "Comparing many trials by hand is slow", "Papers hold lots of unstructured information"];
  items.forEach((t, i) => {
    const y = 1.3 + i * 0.76;
    s.addText(String(i + 1), { shape: pres.ShapeType.ellipse, x: 0.5, y, w: 0.55, h: 0.55, fill: { color: C.accent1 }, color: C.background1,
      fontSize: 18, bold: true, align: "center", valign: "middle", margin: 0, objectName: "num " + (i + 1) });
    s.addText(t, { x: 1.3, y, w: 5.2, h: 0.55, fontSize: 18, color: C.text1, valign: "middle", margin: 0, isTextBox: true });
  });
  s.addText("\"Updated\" is not enough.\nResearchers need to know what changed.", { shape: pres.ShapeType.roundRect, rectRadius: 0.1,
    x: 6.8, y: 1.5, w: 2.7, h: 2.9, fill: { color: C.background2 }, color: C.text2, fontSize: 20, italic: true, align: "center", valign: "middle", margin: 10, objectName: "quote" });
}

// ---------- 3 Objective
{
  const s = content("Project Objective", 2);
  const mods = [["1", "NCT Change Tracking", "Version history and an exact change log: field, old value, new value, date", "py"],
                ["2", "PubMed Research Intelligence", "Search, store and summarize articles and figures", "ai"],
                ["3", "Clinical Trial Comparator", "Drug + indication in, side-by-side trial table out", "py"]];
  mods.forEach(([n, t, d, k], i) => {
    const x = 0.5 + i * 3.05;
    s.addShape(pres.ShapeType.roundRect, { x, y: 1.4, w: 2.85, h: 3.3, rectRadius: 0.1, fill: { color: C.background2 }, objectName: "card " + n });
    s.addText(n, { shape: pres.ShapeType.ellipse, x: x + 0.25, y: 1.65, w: 0.6, h: 0.6, fill: { color: KIND[k].fill }, color: C.background1, fontSize: 22, bold: true, align: "center", valign: "middle", margin: 0, objectName: "n " + n });
    s.addText(t, { x: x + 0.25, y: 2.45, w: 2.4, h: 0.75, fontSize: 18, bold: true, color: C.text2, margin: 0, valign: "top", isTextBox: true });
    s.addText(d, { x: x + 0.25, y: 3.25, w: 2.4, h: 1.2, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true });
  });
}

// ---------- 4 Solution
{
  const s = content("Proposed Solution", 3);
  const rows = [["NCT change log", ["ClinicalTrials.gov", "NCT Parser", "SQLite", "Version Comparison", "Change Log"], ["soft", "py", "db", "py", "py"]],
                ["PubMed intelligence", ["PubMed", "Article Extraction", "SQLite", "Groq AI", "Research Summary"], ["soft", "py", "db", "ai", "ai"]],
                ["Trial comparator", ["ClinicalTrials.gov", "Trial Extraction", "SQLite", "Groq Understanding", "Trial Comparison"], ["soft", "py", "db", "ai", "py"]]];
  rows.forEach(([label, steps, kinds], i) => {
    const y = 1.2 + i * 1.3;
    s.addText(label, { x: 0.5, y, w: 4, h: 0.3, fontSize: 14, bold: true, color: C.accent1, margin: 0, isTextBox: true });
    flow(s, steps, kinds, 0.5, y + 0.35, 9, 0.65, 0.3, 12);
  });
  legend(s, 0.5, 5.0);
}

// ---------- 5 Architecture
{
  const s = content("Overall Architecture", 4);
  box(s, "User", 0.5, 1.2, 1.2, 0.45, "soft", 13); arrow(s, 1.72, 1.43, 2.1, 1.43);
  box(s, "HTML / JS UI", 2.12, 1.2, 1.7, 0.45, "soft", 13); arrow(s, 3.84, 1.43, 4.2, 1.43);
  box(s, "FastAPI", 4.22, 1.2, 1.5, 0.45, "py", 13);
  legend(s, 6.3, 1.27);
  const mods = [["NCT Module", "py", "ClinicalTrials.gov"], ["PubMed Module", "py", "PubMed API"], ["Trial Module", "py", "ClinicalTrials.gov"]];
  mods.forEach(([t, k, src], i) => {
    const x = 0.5 + i * 3.05;
    arrow(s, 4.97, 1.67, x + 1.4, 2.0);
    box(s, t, x, 2.0, 2.8, 0.5, k, 14);
    arrow(s, x + 1.4, 2.52, x + 1.4, 2.85);
    box(s, src, x, 2.85, 2.8, 0.45, "soft", 13);
    arrow(s, x + 1.4, 3.32, x + 1.4, 3.65);
  });
  box(s, "SQLite database (SQLAlchemy models)", 0.5, 3.65, 8.9, 0.5, "db", 14);
  arrow(s, 4.95, 4.17, 4.95, 4.5);
  box(s, "Groq Service - summaries, trial understanding, figure analysis", 2.0, 4.5, 5.9, 0.5, "ai", 14);
}

// ---------- 6 Tech stack
{
  const s = content("Technology Stack", 5);
  const rows = [["Layer", "Technology"], ["Language", "Python"], ["Backend", "FastAPI"], ["Database", "SQLite local / PostgreSQL (Supabase)"], ["ORM", "SQLAlchemy"],
    ["Validation", "Pydantic"], ["HTML Parsing", "BeautifulSoup"], ["Research API", "PubMed (E-utilities)"], ["Trial Data", "ClinicalTrials.gov API"],
    ["AI", "Groq API"], ["Frontend", "HTML / CSS / JavaScript"], ["Deployment", "Render + Supabase"]];
  s.addTable(rows.map((r, i) => r.map(c => ({ text: c, options: i === 0 ? { bold: true, color: C.background1, fill: { color: C.text2 } } :
    { color: C.text1, fill: { color: i % 2 ? C.background1 : C.background2 }, bold: c === "Groq API" } }))),
    { x: 0.5, y: 1.2, w: 5.6, colW: [2.0, 3.6], rowH: 0.3, fontSize: 13, border: { type: "solid", color: "D5DDE5", pt: 0.5 }, valign: "middle", margin: [0, 0.1, 0, 0.1] });
  s.addText([{ text: "Kept simple on purpose", options: { bold: true, fontSize: 18, color: C.text2, breakLine: true } },
    { text: "No Docker, Redis, Celery or React.", options: { bullet: true, breakLine: true } },
    { text: "Every library has one clear job.", options: { bullet: true, breakLine: true } },
    { text: "Groq is called with plain HTTP, so the request is easy to explain.", options: { bullet: true } }],
    { x: 6.5, y: 1.3, w: 3.0, h: 2.8, fontSize: 14, color: C.text1, valign: "top", paraSpaceAfter: 8, margin: 0, isTextBox: true });
}

// ---------- 7 NCT change detection
{
  const s = content("NCT Change Detection", 6);
  const rowsY = [1.35, 3.25];
  [["Previous HTML", "previous"], ["Current HTML", "current"]].forEach(([t], r) => {
    const y = rowsY[r];
    flow(s, [t, "Parser", "Normalized JSON"], ["soft", "py", "py"], 0.5, y, 4.3, 0.8, 0.3, 12);
    arrow(s, 4.83, y + 0.4, 5.2, y + 0.4);
  });
  box(s, "Compare\n(Python function)\n\nadded\nremoved\nmodified", 5.22, 1.35, 1.6, 2.7, "py", 13);
  s.addShape(pres.ShapeType.roundRect, { x: 7.1, y: 1.35, w: 2.4, h: 2.7, rectRadius: 0.08, fill: { color: C.background2 }, objectName: "example card" });
  s.addText([{ text: "Eligibility", options: { bold: true, color: C.text2, fontSize: 15, breakLine: true } },
    { text: "Previous:", options: { bold: true, fontSize: 12, color: C.accent5, breakLine: true } },
    { text: "Age 18\u201365", options: { fontSize: 14, breakLine: true } },
    { text: "Current:", options: { bold: true, fontSize: 12, color: C.accent4, breakLine: true } },
    { text: "Age 18\u201370", options: { fontSize: 14, breakLine: true } },
    { text: "MODIFIED", options: { bold: true, fontSize: 14, color: C.accent3 } }],
    { x: 7.25, y: 1.45, w: 2.1, h: 2.5, color: C.text1, valign: "top", paraSpaceAfter: 4, margin: 0, isTextBox: true });
  s.addText("Layout, whitespace and case differences are ignored. Only real content changes are reported.", { x: 0.5, y: 4.35, w: 9, h: 0.6, fontSize: 14, italic: true, color: C.text2, margin: 0, isTextBox: true });
}

// ---------- 8 PubMed
{
  const s = content("PubMed Module", 7);
  flow(s, ["Search Query", "PubMed API", "Article Metadata", "SQLite", "Groq", "Summary + Findings"], ["soft", "py", "py", "db", "ai", "ai"], 0.5, 1.35, 9, 0.8, 0.22, 12);
  s.addShape(pres.ShapeType.roundRect, { x: 0.5, y: 2.6, w: 4.35, h: 2.3, rectRadius: 0.08, fill: { color: C.background2 }, objectName: "py card" });
  s.addText([{ text: "Python does", options: { bold: true, fontSize: 16, color: C.accent1, breakLine: true } },
    { text: "esearch: query to PMIDs", options: { bullet: true, breakLine: true } }, { text: "efetch: PMIDs to XML", options: { bullet: true, breakLine: true } },
    { text: "Parse title, authors, abstract, DOI", options: { bullet: true, breakLine: true } }, { text: "Download PMC figures", options: { bullet: true } }],
    { x: 0.7, y: 2.7, w: 4.0, h: 2.1, fontSize: 14, color: C.text1, valign: "top", paraSpaceAfter: 4, margin: 0, isTextBox: true });
  s.addShape(pres.ShapeType.roundRect, { x: 5.15, y: 2.6, w: 4.35, h: 2.3, rectRadius: 0.08, fill: { color: AI_TINT }, objectName: "ai card" });
  s.addText([{ text: "Groq does", options: { bold: true, fontSize: 16, color: C.accent2, breakLine: true } },
    { text: "Summary and key findings", options: { bullet: true, breakLine: true } }, { text: "Study type, population, method", options: { bullet: true, breakLine: true } },
    { text: "Figure analysis: image + caption, or caption only (labelled)", options: { bullet: true } }],
    { x: 5.35, y: 2.7, w: 4.0, h: 2.1, fontSize: 14, color: C.text1, valign: "top", paraSpaceAfter: 4, margin: 0, isTextBox: true });
}

// ---------- 9 Trial comparator
{
  const s = content("Clinical Trial Comparator", 8);
  flow(s, ["Drug + Indication", "ClinicalTrials.gov", "Relevant Trials", "Structured Data", "Groq", "Comparison Table"], ["soft", "py", "py", "py", "ai", "py"], 0.5, 1.35, 9, 0.8, 0.22, 12);
  s.addShape(pres.ShapeType.roundRect, { x: 0.5, y: 2.6, w: 4.35, h: 2.3, rectRadius: 0.08, fill: { color: C.background2 }, objectName: "py card" });
  s.addText([{ text: "Python extracts", options: { bold: true, fontSize: 16, color: C.accent1, breakLine: true } },
    { text: "Drugs, doses, arms, phase, design", options: { bullet: true, breakLine: true } }, { text: "Criteria, outcomes, duration", options: { bullet: true, breakLine: true } },
    { text: "Sites, sponsor, age, sex, dates", options: { bullet: true, breakLine: true } }, { text: "Table + highlights differences", options: { bullet: true } }],
    { x: 0.7, y: 2.7, w: 4.0, h: 2.1, fontSize: 14, color: C.text1, valign: "top", paraSpaceAfter: 4, margin: 0, isTextBox: true });
  s.addShape(pres.ShapeType.roundRect, { x: 5.15, y: 2.6, w: 4.35, h: 2.3, rectRadius: 0.08, fill: { color: AI_TINT }, objectName: "ai card" });
  s.addText([{ text: "Groq answers 7 questions", options: { bold: true, fontSize: 16, color: C.accent2, breakLine: true } },
    { text: "What is it investigating?", options: { bullet: true, breakLine: true } }, { text: "Which drug, indication, population?", options: { bullet: true, breakLine: true } },
    { text: "Primary objective", options: { bullet: true, breakLine: true } }, { text: "What is different? Which stage?", options: { bullet: true } }],
    { x: 5.35, y: 2.7, w: 4.0, h: 2.1, fontSize: 14, color: C.text1, valign: "top", paraSpaceAfter: 4, margin: 0, isTextBox: true });
}

// ---------- 10 Database
{
  const s = content("Database Design", 9);
  const groups = [["NCT tracking", "NCTStudy", ["NCTVersion", "NCTChange"], "py"], ["PubMed", "Publication", ["Author", "Figure", "AIAnalysis"], "ai"], ["Trials", "ClinicalTrial", ["TrialAnalysis"], "py"]];
  groups.forEach(([label, parent, kids, k], i) => {
    const x = 0.5 + i * 3.05;
    s.addText(label, { x, y: 1.2, w: 2.8, h: 0.3, fontSize: 14, bold: true, color: C.text2, margin: 0, isTextBox: true });
    box(s, parent, x, 1.55, 2.8, 0.55, "db", 15);
    const lastY = 2.5 + (kids.length - 1) * 0.62 + 0.25;
    s.addShape(pres.ShapeType.line, { x: x + 0.3, y: 2.12, w: 0, h: lastY - 2.12, line: { color: C.accent6, width: 1.75 } });
    kids.forEach((kid, j) => {
      const y = 2.5 + j * 0.62;
      arrow(s, x + 0.3, y + 0.25, x + 0.5, y + 0.25);
      box(s, kid, x + 0.5, y, 2.3, 0.5, k, 14);
    });
  });
  s.addText("One study has many versions and changes \u00b7 one publication has many authors, figures and AI analyses \u00b7 one trial has analyses. Images are files; the database stores only the path.",
    { x: 0.5, y: 4.4, w: 9, h: 0.65, fontSize: 14, color: C.text1, margin: 0, isTextBox: true });
}

// ---------- 11 API
{
  const s = content("API Architecture", 10);
  const rows = [["Method", "Endpoint", "What it does"], ["POST", "/api/nct/compare", "Two HTML files in, change log out"], ["POST", "/api/nct/fetch", "URL in, stores a version and compares"],
    ["GET", "/api/pubmed/search", "Searches PubMed and saves articles"], ["POST", "/api/pubmed/analyze", "Abstract to Groq summary"],
    ["GET", "/api/trials/search", "Drug + indication to trials"], ["POST", "/api/trials/analyze", "Groq explains the selected trials"], ["POST", "/api/trials/compare", "Builds the comparison table"]];
  s.addTable(rows.map((r, i) => r.map((c, j) => ({ text: c, options: i === 0 ? { bold: true, color: C.background1, fill: { color: C.text2 } } :
    { color: j === 1 ? C.accent1 : C.text1, bold: j < 2, fontFace: j === 1 ? "Courier New" : undefined, fill: { color: i % 2 ? C.background1 : C.background2 } } }))),
    { x: 0.5, y: 1.25, w: 9, colW: [1.0, 3.2, 4.8], rowH: 0.42, fontSize: 13, border: { type: "solid", color: "D5DDE5", pt: 0.5 }, valign: "middle", margin: [0, 0.1, 0, 0.1] });
  s.addText("All endpoints return JSON. Errors return a friendly message with the right status code. Try them live at /docs.", { x: 0.5, y: 4.8, w: 8.6, h: 0.35, fontSize: 13, italic: true, color: C.text2, margin: 0, isTextBox: true });
}

// ---------- 12 UI
{
  const s = content("User Interface", 11);
  const shots = [["01_dashboard.png", "Dashboard", "Counts and shortcuts to each module"], ["02_nct_changes.png", "NCT change log", "Old vs new value, change type, version"],
                 ["03b_pubmed_detail.png", "PubMed article", "Abstract, AI summary, figures"], ["04_trial_comparison.png", "Trial comparison", "Differing rows highlighted"]];
  shots.forEach(([f, t, d], i) => {
    const x = 0.5 + (i % 2) * 4.6, y = 1.2 + Math.floor(i / 2) * 2.05;
    s.addImage({ path: SHOT(f), x, y, w: 4.3, h: 2.755, sizing: { type: "crop", x: 0, y: 0, w: 4.3, h: 1.5 }, altText: t + " screenshot" });
    s.addText([{ text: t + " - ", options: { bold: true, color: C.text2 } }, { text: d, options: { color: C.text1 } }],
      { x, y: y + 1.55, w: 4.3, h: 0.3, fontSize: 12, valign: "middle", margin: 0, isTextBox: true });
  });
}

// ---------- 13 AI usage
{
  const s = content("AI Usage", 12);
  s.addShape(pres.ShapeType.roundRect, { x: 0.5, y: 1.2, w: 4.4, h: 3.75, rectRadius: 0.08, fill: { color: C.background2 }, objectName: "no-ai card" });
  s.addText([{ text: "Without AI (plain Python)", options: { bold: true, fontSize: 17, color: C.accent1, breakLine: true } },
    ...["HTML parsing", "Data extraction", "Normalization", "Version comparison", "API calls", "Database storage", "Filtering", "Comparison table"].map((t, i, a) => ({ text: t, options: { bullet: true, breakLine: i < a.length - 1 } }))],
    { x: 0.7, y: 1.3, w: 4.0, h: 3.55, fontSize: 14, color: C.text1, valign: "top", paraSpaceAfter: 3, margin: 0, isTextBox: true });
  s.addShape(pres.ShapeType.roundRect, { x: 5.1, y: 1.2, w: 4.4, h: 3.75, rectRadius: 0.08, fill: { color: AI_TINT }, objectName: "ai card" });
  s.addText([{ text: "With Groq", options: { bold: true, fontSize: 17, color: C.accent2, breakLine: true } },
    ...["Article summarization", "Research interpretation", "Trial understanding", "Key findings generation", "Figure / caption interpretation"].map((t, i, a) => ({ text: t, options: { bullet: true, breakLine: i < a.length - 1 } }))],
    { x: 5.3, y: 1.3, w: 4.0, h: 2.4, fontSize: 14, color: C.text1, valign: "top", paraSpaceAfter: 3, margin: 0, isTextBox: true });
  s.addText("The core logic is deterministic Python. The LLM is an extra layer.", { x: 5.3, y: 3.75, w: 4.0, h: 1.0, fontSize: 15, bold: true, italic: true, color: C.accent2, valign: "middle", margin: 0, isTextBox: true });
}

// ---------- 14 Demo flow
{
  const s = content("Demo Flow", 13);
  const demos = [["Demo 1", "Upload two NCT HTML files", "Previous \u2192 Current \u2192 Detected changes", "py"],
                 ["Demo 2", "Search PubMed", "Article \u2192 Abstract \u2192 Groq summary", "ai"],
                 ["Demo 3", "Drug + Disease", "Trial A vs Trial B vs Trial C", "py"]];
  demos.forEach(([n, t, d, k], i) => {
    const x = 0.5 + i * 3.05;
    s.addShape(pres.ShapeType.roundRect, { x, y: 1.4, w: 2.85, h: 3.2, rectRadius: 0.1, fill: { color: C.background2 }, objectName: "demo card " + n });
    box(s, n, x + 0.25, 1.65, 1.2, 0.45, k, 14);
    s.addText(t, { x: x + 0.25, y: 2.3, w: 2.4, h: 0.8, fontSize: 18, bold: true, color: C.text2, margin: 0, valign: "top", isTextBox: true });
    s.addText(d, { x: x + 0.25, y: 3.3, w: 2.4, h: 1.0, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true });
    if (i < 2) arrow(s, x + 2.87, 3.0, x + 3.03, 3.0);
  });
}

// ---------- 15 Future
{
  const s = content("Future Enhancements", 14);
  const items = ["S3 / R2 file storage", "Supabase Storage", "Scheduled NCT monitoring", "Email alerts", "Better image analysis", "Authentication", "Advanced search", "Trial similarity discovery", "Cloud deployment", "Analytics dashboard"];
  items.forEach((t, i) => {
    const x = 0.5 + (i % 5) * 1.82, y = 1.5 + Math.floor(i / 5) * 1.7;
    s.addText(t, { shape: pres.ShapeType.roundRect, rectRadius: 0.08, x, y, w: 1.65, h: 1.4, fill: { color: i % 2 ? C.background2 : AI_TINT }, color: C.text2, fontSize: 14, bold: true, align: "center", valign: "middle", margin: 6, objectName: "future " + t });
  });
}

pres.writeFile({ fileName: path.join(ROOT, "docs", "Research_Intelligence_Demo.pptx") }).then(async f => {
  await applyTheme(f, THEME);
  const md = ["# PPT speaker notes\n", "Each slide: what is on it, what to say, a possible interviewer question and a simple answer.\n"];
  notes.forEach((n, i) => md.push(`\n## Slide ${i + 1} - ${n.title}\n\n**What is on the slide:** ${n.on}\n\n**What I should say:** ${n.say}\n\n**Possible interviewer question:** ${n.q}\n\n**Simple answer:** ${n.a}\n`));
  fs.writeFileSync(path.join(ROOT, "docs", "PPT_SPEAKER_NOTES.md"), md.join(""));
  console.log("written", f);
});
