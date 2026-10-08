"""Module 3 endpoints:  /api/trials/..."""
import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import ServiceError
from app.models.trial import ClinicalTrial, TrialAnalysis
from app.schemas.trial import TrialAnalyzeRequest, TrialCompareRequest
from app.services import clinical_trials_service as cts
from app.services.groq_service import GroqService
from app.services.trial_comparator import build_comparison, build_trial_text

router = APIRouter(prefix="/api/trials", tags=["Clinical trials"])


def _trial_out(trial: ClinicalTrial) -> dict:
    analysis = json.loads(trial.analyses[-1].analysis_json) if trial.analyses else None
    return {"nct_id": trial.nct_id, "data": json.loads(trial.data_json), "analysis": analysis}


def _get_trial(db: Session, nct_id: str) -> ClinicalTrial:
    trial = db.query(ClinicalTrial).filter_by(nct_id=nct_id.strip().upper()).first()
    if trial is None:
        raise ServiceError(f"{nct_id} is not stored yet. Search for it first.", 404)
    return trial


@router.get("/search")
def search_trials(drug: str = "", indication: str = "", days: int = Query(None, ge=1, le=3650),
                  use_sample: bool = False, db: Session = Depends(get_db)):
    """Search ClinicalTrials.gov, parse each study with Python, store in SQLite."""
    studies = cts.get_trials(drug, indication, days=days, use_sample=use_sample)
    out = []
    for study in studies:
        try:
            data = cts.parse_trial(study)
        except ValueError:
            continue                                   # skip broken records
        out.append(_trial_out(cts.save_trial(db, data, drug.strip(), indication.strip())))
    return {"source": "sample" if use_sample else "clinicaltrials.gov", "count": len(out), "trials": out}


@router.post("/analyze")
def analyze_trials(body: TrialAnalyzeRequest, db: Session = Depends(get_db)):
    """Groq explains each trial (7 standard questions). Results are cached in SQLite."""
    groq, results, errors = GroqService(), [], []
    for nct_id in body.nct_ids:
        trial = _get_trial(db, nct_id)
        if trial.analyses and not body.force:
            results.append({"nct_id": trial.nct_id, "analysis": json.loads(trial.analyses[-1].analysis_json),
                            "cached": True})
            continue
        try:
            analysis = groq.analyze_trial(build_trial_text(json.loads(trial.data_json)))
        except ServiceError as err:
            errors.append({"nct_id": trial.nct_id, "error": err.message})
            if err.status_code in (401, 429, 503):      # no point trying the others
                break
            continue
        db.add(TrialAnalysis(trial_id=trial.id, analysis_json=json.dumps(analysis), model_used=groq.model))
        db.commit()
        results.append({"nct_id": trial.nct_id, "analysis": analysis, "cached": False})
    if errors and not results:
        raise ServiceError(errors[0]["error"], 502)
    return {"results": results, "errors": errors}


@router.post("/compare")
def compare_trials(body: TrialCompareRequest, db: Session = Depends(get_db)):
    """Build the side-by-side table for 2-4 stored trials."""
    trials = [_trial_out(_get_trial(db, n)) for n in body.nct_ids]
    return {"trials": [{"nct_id": t["data"]["nct_id"], "title": t["data"]["study_title"]} for t in trials],
            "rows": build_comparison(trials)}


@router.get("/{nct_id}")
def get_trial(nct_id: str, db: Session = Depends(get_db)):
    trial = db.query(ClinicalTrial).filter_by(nct_id=nct_id.strip().upper()).first()
    if trial is None:                                  # not stored -> download it
        trial = cts.save_trial(db, cts.parse_trial(cts.get_trial_by_nct_id(nct_id)))
    return _trial_out(trial)
