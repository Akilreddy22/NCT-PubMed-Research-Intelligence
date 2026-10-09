from app.services.nct_comparator import compare_nct_versions, flatten
from app.services.nct_parser import parse_nct_html


def _by_field(changes):
    return {c["field"]: c for c in changes}


def test_detects_age_change(v1_html, v2_html):
    changes = _by_field(compare_nct_versions(parse_nct_html(v1_html), parse_nct_html(v2_html)))
    age = changes["eligibility.inclusion"]
    assert age["change_type"] == "modified"
    assert "Age 18-65 years" in age["previous_value"] and "Age 18-70 years" in age["new_value"]
    assert age["added_items"] == ["Age 18-70 years"] and age["removed_items"] == ["Age 18-65 years"]


def test_exactly_the_intended_changes(v1_html, v2_html):
    changes = compare_nct_versions(parse_nct_html(v1_html), parse_nct_html(v2_html), previous_version=1, current_version=2)
    assert {c["field"] for c in changes} == {
        "eligibility.inclusion", "eligibility.exclusion", "eligibility.max_age", "secondary_outcomes",
        "recruitment_status", "enrollment", "start_date", "last_update_date", "locations"}
    assert all(c["previous_version"] == 1 and c["current_version"] == 2 and c["changed_at"] for c in changes)


def test_same_page_has_no_changes(v1_html):
    data = parse_nct_html(v1_html)
    assert compare_nct_versions(data, data) == []


def test_case_and_whitespace_are_not_changes():
    a, b = {"brief_summary": "Hello   World"}, {"brief_summary": "hello world"}
    assert compare_nct_versions(a, b) == []


def test_added_and_removed():
    changes = _by_field(compare_nct_versions({"phase": "Phase 1", "sponsor": ""}, {"phase": "", "sponsor": "ACME"}))
    assert changes["phase"]["change_type"] == "removed"
    assert changes["sponsor"]["change_type"] == "added"


def test_flatten():
    assert flatten({"a": {"b": 1}, "c": 2}) == {"a.b": 1, "c": 2}
