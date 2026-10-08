import pytest

from app.errors import ServiceError
from app.services.clinical_trials_service import get_trials, parse_trial
from app.services.trial_comparator import build_comparison


def _sample_trials():
    return [{"data": parse_trial(s), "analysis": None} for s in get_trials("pembrolizumab", "melanoma", use_sample=True)]


def test_parse_trial_fields():
    t = _sample_trials()[0]["data"]
    assert t["nct_id"] == "NCT99000001" and t["phase"] == "Phase 3"
    assert t["study_design"]["allocation"] == "Randomized"
    assert t["drugs"] == ["Pembrolizumab", "Chemotherapy"]
    assert "200 mg intravenous every 3 weeks" in t["dosages"]
    assert t["duration_months"] == 32 and t["enrollment"] == 120
    assert t["eligibility"]["age_groups"] == "Adult, Older Adult"
    assert "Prior anti-PD-1 therapy" in t["eligibility"]["exclusion"]


def test_comparison_marks_differences():
    rows = {r["category"]: r for r in build_comparison(_sample_trials())}
    assert len(rows["NCT ID"]["values"]) == 3
    assert rows["Phase"]["differs"] is True
    assert rows["Indication"]["differs"] is True


def test_comparison_same_value_not_flagged():
    t = _sample_trials()
    rows = {r["category"]: r for r in build_comparison([t[0], t[0]])}
    assert rows["Phase"]["differs"] is False


def test_empty_search_is_rejected():
    with pytest.raises(ServiceError):
        get_trials("", "", use_sample=True)


def test_parse_trial_without_nct_id():
    with pytest.raises(ValueError):
        parse_trial({"protocolSection": {}})


def test_population_text_and_nct_id_row():
    rows = {r["category"]: r for r in build_comparison(_sample_trials())}
    assert rows["Population"]["values"][0].endswith("(Adult, Older Adult)")
    assert rows["NCT ID"]["differs"] is False          # ids always differ, so we do not highlight them
