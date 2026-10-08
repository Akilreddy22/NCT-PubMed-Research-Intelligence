import pytest

from app.services.nct_parser import parse_nct_html, split_criteria, to_int


def test_parser_extracts_main_fields(v1_html):
    data = parse_nct_html(v1_html)
    assert data["nct_id"] == "NCT99000001"
    assert data["study_title"].startswith("A Phase 3 Study of Pembrolizumab")
    assert data["recruitment_status"] == "Not yet recruiting"
    assert data["enrollment"] == 100                       # "100 participants (estimated)" -> 100
    assert data["conditions"] == ["Melanoma", "Skin Cancer"]
    assert data["study_design"]["allocation"] == "Randomized"
    assert data["sponsor"] == "Example Oncology Research Group"
    assert len(data["locations"]) == 2


def test_inclusion_and_exclusion_are_separated(v1_html):
    elig = parse_nct_html(v1_html)["eligibility"]
    assert "Age 18-65 years" in elig["inclusion"]
    assert "Untreated brain metastases" in elig["exclusion"]
    assert elig["max_age"] == "65 Years"


def test_layout_noise_is_ignored(v1_html):
    assert "Maintenance" not in str(parse_nct_html(v1_html))        # banner removed
    assert "tracking" not in str(parse_nct_html(v1_html))           # <script> removed


def test_empty_html_raises():
    with pytest.raises(ValueError):
        parse_nct_html("   ")


def test_split_criteria_text_block():
    inc, exc = split_criteria("Inclusion Criteria:\n* Age 18+\n* ECOG 0\nExclusion Criteria:\n* Pregnant")
    assert inc == "Age 18+\nECOG 0" and exc == "Pregnant"


def test_to_int():
    assert to_int("1,250 participants") == 1250
    assert to_int("n/a") is None
