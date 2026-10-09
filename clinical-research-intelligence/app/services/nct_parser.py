"""
nct_parser.py - turns a ClinicalTrials.gov style HTML page into a clean Python dictionary.

HOW IT WORKS (4 steps, no AI):
  1. Remove noise     : delete <script>, <style>, <nav>, banners ... (layout-only stuff).
  2. Collect "blocks" : find every  label -> value  pair on the page.
        a) table rows   <tr><th>Label</th><td>Value</td></tr>
        b) definition lists   <dt>Label</dt><dd>Value</dd>
        c) headings   <h2>Label</h2> followed by <p>/<ul> text, up to the next heading
  3. Map labels to our field names using an ALIASES table
        ("overall status" and "recruitment status" both -> recruitment_status).
  4. Normalize        : collapse whitespace, turn "100 participants" into the number 100,
        split "Inclusion Criteria / Exclusion Criteria" text, etc.
The same dictionary "shape" is also produced by clinical_trials_service.parse_trial()
for API data, so both modules speak the same language.
"""
import re

from bs4 import BeautifulSoup, Tag

HEADINGS = ["h1", "h2", "h3", "h4"]
NOISE_TAGS = ["script", "style", "noscript", "nav", "footer", "aside", "iframe"]
NOISE_CLASS_WORDS = ("banner", "cookie", "advert", "breadcrumb")

# canonical field  ->  possible labels found on pages (lower case, no colon)
ALIASES = {
    "brief_summary": ["brief summary", "study summary"],
    "detailed_description": ["detailed description"],
    "conditions": ["conditions", "condition"],
    "interventions": ["interventions", "intervention"],
    "arms": ["arms and interventions", "arms", "arm groups", "treatment arms"],
    "primary_outcomes": ["primary outcome measures", "primary outcomes", "primary outcome"],
    "secondary_outcomes": ["secondary outcome measures", "secondary outcomes", "secondary outcome"],
    "eligibility_text": ["eligibility criteria", "eligibility"],
    "inclusion": ["inclusion criteria"],
    "exclusion": ["exclusion criteria"],
    "locations": ["locations", "contacts and locations", "study locations"],
    "investigators": ["investigators", "study officials", "principal investigator"],
    "participants": ["participants"],
    "sponsor": ["lead sponsor", "sponsor"],
    "collaborators": ["collaborators"],
    "recruitment_status": ["recruitment status", "overall status", "status"],
    "start_date": ["study start", "start date"],
    "primary_completion_date": ["primary completion", "primary completion date"],
    "completion_date": ["study completion", "study completion date", "completion date"],
    "last_update_date": ["last update posted", "last update"],
    "enrollment": ["enrollment", "estimated enrollment", "actual enrollment"],
    "phase": ["phase", "phases"],
    "study_type": ["study type"],
    "allocation": ["allocation", "randomization"],
    "intervention_model": ["intervention model"],
    "masking": ["masking"],
    "primary_purpose": ["primary purpose"],
    "min_age": ["minimum age"],
    "max_age": ["maximum age"],
    "sex": ["sex", "gender", "sexes eligible for study"],
    "healthy_volunteers": ["accepts healthy volunteers", "healthy volunteers"],
}


# ---------------------------------------------------------------- small helpers
def normalize_text(text) -> str:
    """Collapse all whitespace (spaces, tabs, new lines, &nbsp;) into single spaces."""
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text).replace("\xa0", " ")).strip()


def _label(text) -> str:
    """'Recruitment Status:' -> 'recruitment status'"""
    return normalize_text(text).lower().rstrip(":").strip()


def clean_lines(text: str) -> str:
    """Make a bullet text tidy: one criterion per line, bullet symbols removed."""
    lines = []
    for line in str(text).splitlines():
        line = normalize_text(re.sub(r"^\s*[\*\-\u2022]+\s*", "", line))
        if line:
            lines.append(line)
    return "\n".join(lines)


def split_criteria(text: str):
    """
    Eligibility text often looks like:
        'Inclusion Criteria: * a * b   Exclusion Criteria: * c'
    Return (inclusion_text, exclusion_text).
    """
    if not text:
        return "", ""
    inc = re.search(r"inclusion criteria\s*:?", text, re.I)
    exc = re.search(r"exclusion criteria\s*:?", text, re.I)
    if inc and exc:
        if inc.start() < exc.start():
            inclusion, exclusion = text[inc.end():exc.start()], text[exc.end():]
        else:
            exclusion, inclusion = text[exc.end():inc.start()], text[inc.end():]
    elif inc:
        inclusion, exclusion = text[inc.end():], ""
    elif exc:
        inclusion, exclusion = text[:exc.start()], text[exc.end():]
    else:
        inclusion, exclusion = text, ""
    return clean_lines(inclusion), clean_lines(exclusion)


def to_int(text):
    """'120 participants (estimated)' -> 120 ; no number -> None"""
    match = re.search(r"\d[\d,]*", str(text or ""))
    return int(match.group().replace(",", "")) if match else None


# ---------------------------------------------------------------- step 1 + 2
def _remove_noise(soup):
    for tag in soup.find_all(NOISE_TAGS):
        tag.decompose()
    for tag in soup.find_all(class_=True):
        if tag.decomposed:          # a parent was already removed
            continue
        classes = " ".join(tag.get("class", [])).lower()
        if any(word in classes for word in NOISE_CLASS_WORDS):
            tag.decompose()


def _collect_blocks(soup) -> dict:
    """Return {label: {"text": str, "items": [str, ...]}} for every label/value on the page."""
    blocks = {}

    def add(label, text, items):
        if not label:
            return
        entry = blocks.setdefault(label, {"text": "", "items": []})
        entry["text"] = normalize_text(f"{entry['text']} {text}")
        entry["items"].extend(items)

    # a) table rows with a label cell and a value cell
    for tr in soup.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if len(cells) >= 2:
            add(_label(cells[0].get_text()), cells[1].get_text(" "),
                [normalize_text(li.get_text(" ")) for li in cells[1].find_all("li")])

    # b) definition lists
    for dt in soup.find_all("dt"):
        dd = dt.find_next_sibling("dd")
        if dd:
            add(_label(dt.get_text()), dd.get_text(" "),
                [normalize_text(li.get_text(" ")) for li in dd.find_all("li")])

    # c) headings followed by content
    for heading in soup.find_all(HEADINGS):
        parts, items = [], []
        for sib in heading.next_siblings:
            if isinstance(sib, Tag):
                if sib.name in HEADINGS or sib.find(HEADINGS):
                    break
                if sib.name == "table":
                    continue                      # tables are handled in step (a)
                li_tags = [sib] if sib.name == "li" else sib.find_all("li")
                if li_tags:
                    items += [normalize_text(li.get_text(" ")) for li in li_tags]
                else:
                    parts.append(sib.get_text(" "))
            else:
                parts.append(str(sib))
        add(_label(heading.get_text()), " ".join(parts), [i for i in items if i])
    return blocks


# ---------------------------------------------------------------- step 3 helpers
def _find(blocks, canonical):
    """Look up a block by any of its aliases. Returns {'text','items'} (empty if missing)."""
    for alias in ALIASES[canonical]:
        block = blocks.get(alias)
        if block and (block["text"] or block["items"]):
            return block
    return {"text": "", "items": []}


def _text(blocks, canonical) -> str:
    block = _find(blocks, canonical)
    return block["text"] if block["text"] else "\n".join(block["items"])


def _list(blocks, canonical, split_on=r";") -> list:
    block = _find(blocks, canonical)
    if block["items"]:
        return block["items"]
    if block["text"]:
        return [p.strip() for p in re.split(split_on, block["text"]) if p.strip()]
    return []


def _find_nct_id(soup, blocks):
    title = soup.title.get_text() if soup.title else ""
    for source in (title, soup.get_text(" ")):
        match = re.search(r"NCT\d{8}", source)
        if match:
            return match.group()
    return ""


def _find_title(soup, blocks):
    h1 = soup.find("h1")
    if h1 and normalize_text(h1.get_text()):
        return normalize_text(h1.get_text())
    for label in ("official title", "study title", "brief title"):
        if label in blocks and blocks[label]["text"]:
            return blocks[label]["text"]
    if soup.title:
        return normalize_text(soup.title.get_text().split("|")[0])
    return ""


# ---------------------------------------------------------------- the main function
def parse_nct_html(html: str) -> dict:
    """HTML text  ->  normalized dictionary.  Raises ValueError for empty / unusable HTML."""
    if not html or not html.strip():
        raise ValueError("The HTML file is empty.")
    soup = BeautifulSoup(html, "html.parser")
    if not soup.find(True):
        raise ValueError("This does not look like HTML.")

    _remove_noise(soup)
    blocks = _collect_blocks(soup)

    inclusion = _text(blocks, "inclusion")
    exclusion = _text(blocks, "exclusion")
    if not inclusion and not exclusion:
        inclusion, exclusion = split_criteria(_text(blocks, "eligibility_text"))

    return {
        "nct_id": _find_nct_id(soup, blocks),
        "study_title": _find_title(soup, blocks),
        "brief_summary": _text(blocks, "brief_summary"),
        "detailed_description": _text(blocks, "detailed_description"),
        "conditions": _list(blocks, "conditions", r"[;,]"),
        "interventions": _list(blocks, "interventions"),
        "arms": _list(blocks, "arms"),
        "phase": _text(blocks, "phase"),
        "study_design": {
            "study_type": _text(blocks, "study_type"),
            "allocation": _text(blocks, "allocation"),
            "intervention_model": _text(blocks, "intervention_model"),
            "masking": _text(blocks, "masking"),
            "primary_purpose": _text(blocks, "primary_purpose"),
        },
        "eligibility": {
            "inclusion": inclusion,
            "exclusion": exclusion,
            "min_age": _text(blocks, "min_age"),
            "max_age": _text(blocks, "max_age"),
            "sex": _text(blocks, "sex"),
            "healthy_volunteers": _text(blocks, "healthy_volunteers"),
        },
        "participants": _text(blocks, "participants"),
        "primary_outcomes": _list(blocks, "primary_outcomes"),
        "secondary_outcomes": _list(blocks, "secondary_outcomes"),
        "recruitment_status": _text(blocks, "recruitment_status"),
        "enrollment": to_int(_text(blocks, "enrollment")),
        "start_date": _text(blocks, "start_date"),
        "primary_completion_date": _text(blocks, "primary_completion_date"),
        "completion_date": _text(blocks, "completion_date"),
        "last_update_date": _text(blocks, "last_update_date"),
        "locations": _list(blocks, "locations"),
        "sponsor": _text(blocks, "sponsor"),
        "collaborators": _list(blocks, "collaborators", r"[;,]"),
        "investigators": _list(blocks, "investigators"),
    }


def count_filled_fields(data: dict) -> int:
    """How many fields actually contain data? (used to detect pages that are JavaScript-only)"""
    count = 0
    for value in data.values():
        if isinstance(value, dict):
            count += sum(1 for v in value.values() if v)
        elif value:
            count += 1
    return count
