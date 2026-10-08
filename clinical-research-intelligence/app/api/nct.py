"""
Module 1 endpoints:  /api/nct/...
Flow for every comparison:  HTML -> parse_nct_html -> save version -> compare_nct_versions -> save changes
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.errors import ServiceError
from app.models.nct import NCTChange, NCTStudy, NCTVersion
from app.schemas.nct import NCTCompareVersionsRequest, NCTFetchRequest
from app.services.clinical_trials_service import get_trial_by_nct_id, parse_trial
from app.services.nct_comparator import compare_nct_versions, side_by_side
from app.services.nct_parser import count_filled_fields, parse_nct_html

router = APIRouter(prefix="/api/nct", tags=["NCT change tracking"])
MAX_UPLOAD = 5_000_000


# ------------------------------------------------------------------ helpers
def _read_upload(file: UploadFile) -> str:
    content = file.file.read()
    if not content:
        raise ServiceError(f"'{file.filename}' is empty.", 400)
    if len(content) > MAX_UPLOAD:
        raise ServiceError(f"'{file.filename}' is larger than 5 MB.", 400)
    return content.decode("utf-8", errors="replace")


def _parse_or_400(html: str) -> dict:
    try:
        return parse_nct_html(html)
    except ValueError as err:
        raise ServiceError(f"Invalid HTML: {err}", 400)


def _clean_id(nct_id: str) -> str:
    nct_id = (nct_id or "").strip().upper()
    if not re.fullmatch(r"NCT\d{8}", nct_id):
        raise ServiceError("Could not find a valid NCT ID (format NCT01234567). Type it in the NCT ID box.", 400)
    return nct_id


def save_version(db: Session, data: dict, raw_text: str, source: str, url: str = ""):
    """Store a parsed page as a new version - unless an identical version already exists."""
    nct_id = _clean_id(data.get("nct_id"))
    study = db.query(NCTStudy).filter_by(nct_id=nct_id).first()
    if study is None:
        study = NCTStudy(nct_id=nct_id)
        db.add(study)
    study.title = data.get("study_title") or study.title
    study.url = url or study.url or f"https://clinicaltrials.gov/study/{nct_id}"
    db.flush()

    content_hash = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    for version in study.versions:
        if version.content_hash == content_hash:
            db.commit()
            return study, version, False

    number = max((v.version_number for v in study.versions), default=0) + 1
    folder = settings.data_dir / "nct"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{nct_id}_v{number}.{'json' if source == 'api' else 'html'}"
    path.write_text(raw_text, encoding="utf-8")

    version = NCTVersion(study_id=study.id, version_number=number, raw_html_path=str(path),
                         extracted_json=json.dumps(data), content_hash=content_hash, source=source)
    db.add(version)
    db.commit()
    db.refresh(study)
    db.refresh(version)
    return study, version, True


def compare_and_store(db: Session, study: NCTStudy, prev: NCTVersion, cur: NCTVersion) -> dict:
    """Compare two stored versions, save the changes, return everything the UI needs."""
    prev_data, cur_data = json.loads(prev.extracted_json), json.loads(cur.extracted_json)
    now = datetime.now(timezone.utc)
    changes = compare_nct_versions(prev_data, cur_data, changed_at=now.isoformat(timespec="seconds"),
                                   previous_version=prev.version_number, current_version=cur.version_number)

    db.query(NCTChange).filter_by(study_id=study.id, previous_version_id=prev.id,
                                  current_version_id=cur.id).delete()          # no duplicates on re-run
    for c in changes:
        db.add(NCTChange(study_id=study.id, previous_version_id=prev.id, current_version_id=cur.id,
                         field_name=c["field"], change_type=c["change_type"],
                         previous_value=c["previous_value"], new_value=c["new_value"], changed_at=now))
    db.commit()

    counts = {kind: sum(1 for c in changes if c["change_type"] == kind) for kind in ("added", "removed", "modified")}
    return {"nct_id": study.nct_id, "title": study.title,
            "previous_version": prev.version_number, "current_version": cur.version_number,
            "previous_source": prev.source, "current_source": cur.source,
            "change_count": len(changes), "summary": counts, "changes": changes,
            "side_by_side": side_by_side(prev_data, cur_data, changes)}


def _two_versions(db, previous_html: str, current_html: str, nct_id: str = "", source="upload"):
    prev_data, cur_data = _parse_or_400(previous_html), _parse_or_400(current_html)
    if nct_id:                                   # the user typed the ID: use it for pages without one
        prev_data["nct_id"] = prev_data["nct_id"] or nct_id
        cur_data["nct_id"] = cur_data["nct_id"] or nct_id
    if _clean_id(prev_data["nct_id"]) != _clean_id(cur_data["nct_id"]):
        raise ServiceError(f"These pages are different studies ({prev_data['nct_id']} vs {cur_data['nct_id']}).", 400)
    study, prev, _ = save_version(db, prev_data, previous_html, source)
    study, cur, _ = save_version(db, cur_data, current_html, source)
    if prev.id == cur.id:
        raise ServiceError("The two files have identical content after normalization - no changes to show.", 400)
    return compare_and_store(db, study, prev, cur)


# ------------------------------------------------------------------ endpoints
@router.post("/upload")
def upload_version(file: UploadFile = File(...), nct_id: str = Form(""), db: Session = Depends(get_db)):
    """Upload ONE html page and store it as a new version of its study."""
    html = _read_upload(file)
    data = _parse_or_400(html)
    if nct_id:
        data["nct_id"] = data["nct_id"] or nct_id
    study, version, is_new = save_version(db, data, html, "upload")
    return {"nct_id": study.nct_id, "version_number": version.version_number, "is_new_version": is_new,
            "fields_found": count_filled_fields(data), "title": study.title}


@router.post("/compare")
def compare_two_files(previous: UploadFile = File(...), current: UploadFile = File(...),
                      nct_id: str = Form(""), db: Session = Depends(get_db)):
    """Option A: upload the previous + current HTML, get the change log."""
    return _two_versions(db, _read_upload(previous), _read_upload(current), nct_id)


@router.post("/compare-versions")
def compare_stored_versions(body: NCTCompareVersionsRequest, db: Session = Depends(get_db)):
    """Compare any two versions we already stored (chosen in the UI drop-downs)."""
    study = db.query(NCTStudy).filter_by(nct_id=_clean_id(body.nct_id)).first()
    if study is None:
        raise ServiceError("Study not found. Upload or fetch it first.", 404)
    by_number = {v.version_number: v for v in study.versions}
    if body.from_version not in by_number or body.to_version not in by_number:
        raise ServiceError("One of the selected versions does not exist.", 404)
    if body.from_version == body.to_version:
        raise ServiceError("Pick two different versions.", 400)
    return compare_and_store(db, study, by_number[body.from_version], by_number[body.to_version])


@router.post("/fetch")
def fetch_from_url(body: NCTFetchRequest, db: Session = Depends(get_db)):
    """Option B: download the CURRENT page, store it, and compare with the previous stored version."""
    url = body.url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not (parsed.hostname or "").endswith("clinicaltrials.gov"):
        raise ServiceError("Invalid URL. Use a clinicaltrials.gov link such as "
                           "https://clinicaltrials.gov/study/NCT01234567", 400)
    nct_id = _clean_id((re.search(r"NCT\d{8}", url, re.I) or [""])[0])

    # Try the real HTML page first.
    data, raw, source = None, "", "html_url"
    try:
        response = httpx.get(url, timeout=25, follow_redirects=True, headers={"User-Agent": "research-demo/1.0"})
        if response.status_code == 200:
            data, raw = parse_nct_html(response.text), response.text
    except (httpx.HTTPError, ValueError):
        pass
    # ClinicalTrials.gov pages are built by JavaScript, so the HTML is often an empty shell.
    # If the parser found almost nothing, use the official API for the same study instead.
    if data is None or count_filled_fields(data) < 8 or not data.get("nct_id"):
        study_json = get_trial_by_nct_id(nct_id)
        data, raw, source = parse_trial(study_json), json.dumps(study_json, indent=1), "api"

    study, current, is_new = save_version(db, data, raw, source, url)
    previous = [v for v in study.versions if v.version_number < current.version_number]
    result = {"nct_id": study.nct_id, "fetched_via": source, "is_new_version": is_new,
              "version_number": current.version_number, "comparison": None}
    if previous:
        result["comparison"] = compare_and_store(db, study, previous[-1], current)
    else:
        result["message"] = "First version stored. Fetch again later to see what changed."
    return result


@router.post("/demo")
def compare_sample_pages(db: Session = Depends(get_db)):
    """One-click demo: compares data/sample/nct_v1.html with nct_v2.html."""
    v1 = (settings.sample_dir / "nct_v1.html").read_text(encoding="utf-8")
    v2 = (settings.sample_dir / "nct_v2.html").read_text(encoding="utf-8")
    return _two_versions(db, v1, v2)


@router.get("")
def list_studies(db: Session = Depends(get_db)):
    studies = db.query(NCTStudy).order_by(NCTStudy.id.desc()).all()
    return [{"nct_id": s.nct_id, "title": s.title, "versions": len(s.versions)} for s in studies]


@router.get("/{nct_id}")
def get_study(nct_id: str, db: Session = Depends(get_db)):
    """Study + all versions + the full change history."""
    study = db.query(NCTStudy).filter_by(nct_id=_clean_id(nct_id)).first()
    if study is None:
        raise ServiceError("Study not found.", 404)
    numbers = {v.id: v.version_number for v in study.versions}
    history = {}
    for c in study.changes:
        key = (numbers.get(c.previous_version_id), numbers.get(c.current_version_id))
        group = history.setdefault(key, {"previous_version": key[0], "current_version": key[1],
                                         "changed_at": c.changed_at.isoformat(timespec="seconds"), "changes": []})
        group["changes"].append({"field": c.field_name, "change_type": c.change_type,
                                 "previous_value": c.previous_value, "new_value": c.new_value})
    return {"nct_id": study.nct_id, "title": study.title, "url": study.url,
            "versions": [{"version_number": v.version_number, "source": v.source,
                          "created_at": v.created_at.isoformat(timespec="seconds")} for v in study.versions],
            "history": sorted(history.values(), key=lambda g: (g["current_version"] or 0), reverse=True)}
