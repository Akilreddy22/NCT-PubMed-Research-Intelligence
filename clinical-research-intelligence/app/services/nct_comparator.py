"""
nct_comparator.py - finds exactly what changed between two parsed NCT dictionaries.
Plain Python only. NO AI.

Steps:
  1. flatten()   : {"eligibility": {"inclusion": "x"}}  ->  {"eligibility.inclusion": "x"}
  2. For every field name in either version:
        empty before, has value now   -> "added"
        has value before, empty now   -> "removed"
        both have values but differ   -> "modified"
  3. "differ" is decided on a NORMALIZED copy (lower case, same dash style, single spaces,
     lists compared without caring about order) so tiny formatting changes are ignored.
"""
import re
from datetime import datetime, timezone


def flatten(data: dict, prefix: str = "") -> dict:
    flat = {}
    for key, value in data.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(flatten(value, name))
        else:
            flat[name] = value
    return flat


def is_empty(value) -> bool:
    return value is None or value == "" or value == [] or value == {}


def to_display(value) -> str:
    """Make any value printable. Lists become one item per line."""
    if is_empty(value):
        return ""
    if isinstance(value, list):
        return "\n".join(str(v) for v in value)
    return str(value)


def _norm(text: str) -> str:
    text = str(text).casefold().replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", text).strip()


def comparison_key(value):
    """What we actually compare. Lists/multi-line text -> sorted set of normalized lines."""
    if isinstance(value, list) or "\n" in to_display(value):
        return sorted(_norm(line) for line in to_display(value).splitlines() if line.strip())
    return _norm(to_display(value))


def pretty_name(field: str) -> str:
    return " > ".join(part.replace("_", " ").title() for part in field.split("."))


def compare_nct_versions(previous: dict, current: dict, changed_at=None,
                         previous_version=None, current_version=None) -> list:
    """Return a list of change dictionaries (see README for the exact shape)."""
    changed_at = changed_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    prev_flat, cur_flat = flatten(previous), flatten(current)
    field_names = list(prev_flat) + [k for k in cur_flat if k not in prev_flat]

    changes = []
    for field in field_names:
        old, new = prev_flat.get(field), cur_flat.get(field)
        if is_empty(old) and is_empty(new):
            continue
        if is_empty(old):
            change_type = "added"
        elif is_empty(new):
            change_type = "removed"
        elif comparison_key(old) != comparison_key(new):
            change_type = "modified"
        else:
            continue                                   # same after normalization

        old_lines = to_display(old).splitlines()
        new_lines = to_display(new).splitlines()
        old_keys, new_keys = {_norm(x) for x in old_lines}, {_norm(x) for x in new_lines}
        multi_line = len(old_lines) > 1 or len(new_lines) > 1 or isinstance(old, list) or isinstance(new, list)
        changes.append({
            "field": field,
            "label": pretty_name(field),
            "section": field.split(".")[0],
            "change_type": change_type,
            "previous_value": to_display(old),
            "new_value": to_display(new),
            "added_items": [x for x in new_lines if _norm(x) not in old_keys] if multi_line else [],
            "removed_items": [x for x in old_lines if _norm(x) not in new_keys] if multi_line else [],
            "changed_at": changed_at,
            "previous_version": previous_version,
            "current_version": current_version,
        })
    return changes


def side_by_side(previous: dict, current: dict, changes: list) -> list:
    """One row per field with both values and a status - the UI shows this as two columns."""
    status = {c["field"]: c["change_type"] for c in changes}
    prev_flat, cur_flat = flatten(previous), flatten(current)
    names = list(prev_flat) + [k for k in cur_flat if k not in prev_flat]
    rows = []
    for name in names:
        old, new = to_display(prev_flat.get(name)), to_display(cur_flat.get(name))
        if not old and not new:
            continue
        rows.append({"field": name, "label": pretty_name(name),
                     "previous": old, "current": new,
                     "status": status.get(name, "unchanged")})
    return rows
