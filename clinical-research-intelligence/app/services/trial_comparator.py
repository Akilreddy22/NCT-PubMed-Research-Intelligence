"""
trial_comparator.py - builds the side-by-side comparison table. Plain Python, no AI needed.
(If AI analysis exists, it is used to fill 'purpose' and 'population' with better text.)
A row is marked  differs=True  when the trials do not all have the same value.
"""
import re

ROW_ORDER = ["NCT ID", "Trial Purpose", "Drug / Intervention", "Indication", "Phase", "Study Design",
             "Population", "Enrollment", "Inclusion Criteria", "Exclusion Criteria", "Primary Outcome",
             "Secondary Outcomes", "Treatment Arms", "Duration", "Recruitment Status", "Locations", "Sponsor"]


def _join(items) -> str:
    return "\n".join(items) if items else "-"


def _locations(locations) -> str:
    if not locations:
        return "-"
    shown = "; ".join(locations[:3]) + ("; ..." if len(locations) > 3 else "")
    return f"{len(locations)} site(s): {shown}"


def trial_cells(data: dict, analysis: dict = None) -> dict:
    """Turn ONE trial into {row name: text}."""
    analysis = analysis or {}
    design, elig = data.get("study_design", {}), data.get("eligibility", {})
    design_text = ", ".join(x for x in (design.get("allocation"), design.get("intervention_model"),
                                        f"Masking: {design.get('masking')}" if design.get("masking") else "") if x)
    population = analysis.get("population") or (
        data.get("participants", "") + (f" ({elig['age_groups']})" if elig.get("age_groups") else ""))
    drugs = data.get("drugs") or data.get("interventions")
    drug_text = ", ".join(drugs) if drugs else "-"
    if data.get("dosages"):
        drug_text += "\nDose: " + "; ".join(data["dosages"])
    months = data.get("duration_months")
    cells = {
        "NCT ID": data.get("nct_id", ""),
        "Trial Purpose": analysis.get("primary_objective") or data.get("study_purpose") or "-",
        "Drug / Intervention": drug_text,
        "Indication": ", ".join(data.get("conditions", [])) or "-",
        "Phase": data.get("phase") or "-",
        "Study Design": design_text or "-",
        "Population": population or "-",
        "Enrollment": str(data.get("enrollment") or "-"),
        "Inclusion Criteria": elig.get("inclusion") or "-",
        "Exclusion Criteria": elig.get("exclusion") or "-",
        "Primary Outcome": _join(data.get("primary_outcomes")),
        "Secondary Outcomes": _join(data.get("secondary_outcomes")),
        "Treatment Arms": _join(data.get("arms")),
        "Duration": f"{months} months ({data.get('start_date', '?')} to {data.get('completion_date') or data.get('primary_completion_date') or '?'})" if months is not None else "-",
        "Recruitment Status": data.get("recruitment_status") or "-",
        "Locations": _locations(data.get("locations")),
        "Sponsor": data.get("sponsor") or "-",
    }
    if analysis.get("differentiator"):
        cells["What Makes It Different (AI)"] = analysis["differentiator"]
    if analysis.get("development_stage"):
        cells["Development Stage (AI)"] = analysis["development_stage"]
    return cells


def _same_key(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def build_comparison(trials: list) -> list:
    """trials = [{'data': {...}, 'analysis': {...} or None}, ...]  ->  list of rows."""
    all_cells = [trial_cells(t["data"], t.get("analysis")) for t in trials]
    categories = ROW_ORDER + [k for k in all_cells[0] if k not in ROW_ORDER] if all_cells else []
    rows = []
    for category in categories:
        values = [cells.get(category, "-") for cells in all_cells]
        rows.append({"category": category, "values": values,
                     "differs": category != "NCT ID" and len({_same_key(v) for v in values}) > 1,
                     "ai": category.endswith("(AI)")})
    return rows


def build_trial_text(data: dict) -> str:
    """Compact text version of one trial that we give to Groq."""
    design, elig = data.get("study_design", {}), data.get("eligibility", {})
    return "\n".join([
        f"Title: {data.get('study_title', '')}", f"Official title: {data.get('official_title', '')}",
        f"Summary: {data.get('brief_summary', '')}", f"Conditions: {', '.join(data.get('conditions', []))}",
        f"Interventions: {'; '.join(data.get('interventions', []))}", f"Doses: {'; '.join(data.get('dosages', []))}",
        f"Phase: {data.get('phase', '')}", f"Design: {design}", f"Arms: {' | '.join(data.get('arms', []))}",
        f"Age/sex: {elig.get('min_age', '')} to {elig.get('max_age', '')}, {elig.get('sex', '')}",
        f"Inclusion: {elig.get('inclusion', '')[:1500]}", f"Exclusion: {elig.get('exclusion', '')[:1500]}",
        f"Primary outcomes: {'; '.join(data.get('primary_outcomes', []))}",
        f"Secondary outcomes: {'; '.join(data.get('secondary_outcomes', []))}",
        f"Sponsor: {data.get('sponsor', '')}", f"Enrollment: {data.get('enrollment', '')}"])
