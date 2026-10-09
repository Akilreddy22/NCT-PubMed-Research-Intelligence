"""
clinical_trials_service.py - gets trials from ClinicalTrials.gov and turns them into clean dictionaries.

ClinicalTrials.gov has a free public REST API (version 2):
    GET https://clinicaltrials.gov/api/v2/studies?query.intr=<drug>&query.cond=<disease>
It answers with JSON:  {"studies": [ {"protocolSection": {...}}, ... ]}
Python (this file) does ALL the extraction. The AI is not used here.
"""
import json
import re
from datetime import date, timedelta

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import ServiceError
from app.models.trial import ClinicalTrial
from app.services.nct_parser import normalize_text, split_criteria

API_URL = "https://clinicaltrials.gov/api/v2/studies"
PHASE_NAMES = {"EARLY_PHASE1": "Early Phase 1", "PHASE1": "Phase 1", "PHASE2": "Phase 2",
               "PHASE3": "Phase 3", "PHASE4": "Phase 4", "NA": "Not Applicable"}
DOSE_PATTERN = re.compile(
    r"\d+(?:\.\d+)?\s?(?:mg/kg|mg/m2|mcg|µg|mg|mL|ml|IU)(?:\s+(?!plus\b|for\b|and\b|with\b)\w+){0,5}")


# ------------------------------------------------------------------ fetching
def load_sample_studies() -> list:
    path = settings.sample_dir / "sample_trial.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)["studies"]


def get_trials(drug: str, indication: str, days=None, page_size: int = 10, use_sample: bool = False) -> list:
    """Return a list of RAW study dictionaries (not parsed yet)."""
    drug, indication = (drug or "").strip(), (indication or "").strip()
    if not drug and not indication:
        raise ServiceError("Please enter a drug, an indication, or both.", 400)

    if use_sample:
        studies = load_sample_studies()
        wanted = [w.lower() for w in (drug, indication) if w]
        return [s for s in studies if all(w in json.dumps(s).lower() for w in wanted)]

    params = {"format": "json", "pageSize": page_size}
    if drug:
        params["query.intr"] = drug
    if indication:
        params["query.cond"] = indication
    if days:
        since = (date.today() - timedelta(days=int(days))).isoformat()
        params["filter.advanced"] = f"AREA[LastUpdatePostDate]RANGE[{since},MAX]"
    try:
        response = httpx.get(API_URL, params=params, timeout=25)
    except httpx.HTTPError:
        raise ServiceError("ClinicalTrials.gov is not reachable right now. "
                           "Check your internet connection or tick 'Use sample data'.", 503)
    if response.status_code != 200:
        raise ServiceError(f"ClinicalTrials.gov returned an error (HTTP {response.status_code}).", 502)
    return response.json().get("studies", [])


def get_trial_by_nct_id(nct_id: str) -> dict:
    """Download ONE study (used by the NCT version tracker when the HTML page is JavaScript-only)."""
    nct_id = (nct_id or "").strip().upper()
    if not re.fullmatch(r"NCT\d{8}", nct_id):
        raise ServiceError("An NCT ID looks like NCT01234567.", 400)
    try:
        response = httpx.get(f"{API_URL}/{nct_id}", params={"format": "json"}, timeout=25)
    except httpx.HTTPError:
        raise ServiceError("ClinicalTrials.gov is not reachable right now.", 503)
    if response.status_code == 404:
        raise ServiceError(f"{nct_id} was not found on ClinicalTrials.gov.", 404)
    if response.status_code != 200:
        raise ServiceError(f"ClinicalTrials.gov returned an error (HTTP {response.status_code}).", 502)
    return response.json()


# ------------------------------------------------------------------ parsing
def _date(struct) -> str:
    return (struct or {}).get("date", "")


def _months_between(start: str, end: str):
    """'2025-04' and '2027-03' -> 23"""
    try:
        sy, sm = int(start[:4]), int(start[5:7] or 1)
        ey, em = int(end[:4]), int(end[5:7] or 1)
        return (ey - sy) * 12 + (em - sm)
    except (ValueError, IndexError):
        return None


def _first_sentence(text: str) -> str:
    return re.split(r"(?<=[.!?])\s", normalize_text(text), maxsplit=1)[0]


def _nice(text: str) -> str:
    return (text or "").replace("_", " ").title()


def parse_trial(study: dict) -> dict:
    """RAW API study -> flat, readable dictionary (same shape as parse_nct_html, plus extras)."""
    p = study.get("protocolSection", {})
    ident, status = p.get("identificationModule", {}), p.get("statusModule", {})
    sponsors, desc = p.get("sponsorCollaboratorsModule", {}), p.get("descriptionModule", {})
    design = p.get("designModule", {})
    info = design.get("designInfo", {})
    arms_mod, outcomes = p.get("armsInterventionsModule", {}), p.get("outcomesModule", {})
    elig, contacts = p.get("eligibilityModule", {}), p.get("contactsLocationsModule", {})

    if not ident.get("nctId"):
        raise ValueError("This record has no NCT ID.")

    inclusion, exclusion = split_criteria(elig.get("eligibilityCriteria", ""))
    interventions = arms_mod.get("interventions", [])
    start, completion = _date(status.get("startDateStruct")), _date(status.get("completionDateStruct"))
    primary_completion = _date(status.get("primaryCompletionDateStruct"))
    purpose = _nice(info.get("primaryPurpose", ""))
    summary = normalize_text(desc.get("briefSummary", ""))

    dose_sources = [f"{i.get('name', '')} {i.get('description', '')}" for i in interventions]
    dose_sources += [a.get("description", "") for a in arms_mod.get("armGroups", [])]
    dosages, seen = [], set()
    for text in dose_sources:
        for match in DOSE_PATTERN.findall(text):
            key = match.strip().lower().replace("intravenous", "iv")   # 'IV' == 'intravenous'
            if key not in seen:
                seen.add(key)
                dosages.append(match.strip())

    sex = _nice(elig.get("sex", ""))
    return {
        "nct_id": ident["nctId"],
        "study_title": ident.get("briefTitle", ""),
        "official_title": ident.get("officialTitle", ""),
        "study_purpose": f"{purpose}: {_first_sentence(summary)}" if purpose else _first_sentence(summary),
        "brief_summary": summary,
        "detailed_description": normalize_text(desc.get("detailedDescription", "")),
        "conditions": p.get("conditionsModule", {}).get("conditions", []),
        "keywords": p.get("conditionsModule", {}).get("keywords", []),
        "interventions": [f"{i.get('type', '')}: {i.get('name', '')}".strip(": ") for i in interventions],
        "drugs": [i["name"] for i in interventions if i.get("type") in ("DRUG", "BIOLOGICAL") and i.get("name")],
        "dosages": dosages[:8],
        "arms": [f"{_nice(a.get('type', ''))}: {a.get('label', '')} - {a.get('description', '')}".strip(" -")
                 for a in arms_mod.get("armGroups", [])],
        "phase": " / ".join(PHASE_NAMES.get(x, x) for x in design.get("phases", [])),
        "study_design": {
            "study_type": _nice(design.get("studyType", "")),
            "allocation": "Not Applicable" if info.get("allocation") == "NA" else _nice(info.get("allocation", "")),
            "intervention_model": _nice(info.get("interventionModel", "")),
            "masking": ("None (Open Label)" if info.get("maskingInfo", {}).get("masking") == "NONE"
                        else _nice(info.get("maskingInfo", {}).get("masking", ""))),
            "primary_purpose": purpose,
        },
        "eligibility": {
            "inclusion": inclusion, "exclusion": exclusion,
            "min_age": elig.get("minimumAge", ""), "max_age": elig.get("maximumAge", ""),
            "sex": sex, "healthy_volunteers": "Yes" if elig.get("healthyVolunteers") else "No",
            "age_groups": ", ".join(_nice(a) for a in elig.get("stdAges", [])),
        },
        "participants": f"{sex}, {elig.get('minimumAge', '?')} to {elig.get('maximumAge') or 'no upper limit'}",
        "enrollment": design.get("enrollmentInfo", {}).get("count"),
        "primary_outcomes": [f"{o.get('measure', '')} ({o.get('timeFrame', '')})" for o in outcomes.get("primaryOutcomes", [])],
        "secondary_outcomes": [f"{o.get('measure', '')} ({o.get('timeFrame', '')})" for o in outcomes.get("secondaryOutcomes", [])],
        "recruitment_status": _nice(status.get("overallStatus", "")),
        "start_date": start,
        "primary_completion_date": primary_completion,
        "completion_date": completion,
        "last_update_date": _date(status.get("lastUpdatePostDateStruct")),
        "duration_months": _months_between(start, completion or primary_completion),
        "locations": [", ".join(x for x in (l.get("facility"), l.get("city"), l.get("country")) if x)
                      for l in contacts.get("locations", [])],
        "sponsor": sponsors.get("leadSponsor", {}).get("name", ""),
        "collaborators": [c.get("name", "") for c in sponsors.get("collaborators", [])],
        "investigators": [f"{o.get('name', '')} ({_nice(o.get('role', ''))}), {o.get('affiliation', '')}".strip(", ")
                          for o in contacts.get("overallOfficials", [])],
    }


# ------------------------------------------------------------------ database
def save_trial(db: Session, data: dict, drug: str = "", indication: str = "") -> ClinicalTrial:
    """Insert the trial, or update it if this NCT ID is already stored."""
    trial = db.query(ClinicalTrial).filter_by(nct_id=data["nct_id"]).first()
    if trial is None:
        trial = ClinicalTrial(nct_id=data["nct_id"])
        db.add(trial)
    trial.title = data["study_title"]
    trial.phase = data["phase"]
    trial.recruitment_status = data["recruitment_status"]
    trial.last_update_date = data["last_update_date"]
    trial.search_drug, trial.search_indication = drug, indication
    trial.data_json = json.dumps(data)
    db.commit()
    db.refresh(trial)
    return trial
