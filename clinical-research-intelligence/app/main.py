"""
main.py - creates the FastAPI app, connects the routers, serves the HTML pages.

FastAPI = receives HTTP requests from the browser and calls our Python functions.
"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api import nct, pubmed, trials
from app.config import settings
from app.database import get_db, init_db
from app.errors import ServiceError
from app.models.nct import NCTStudy
from app.models.pubmed import Publication
from app.models.trial import ClinicalTrial


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()                      # create tables on startup
    yield


app = FastAPI(title="NCT & PubMed Research Intelligence Platform", lifespan=lifespan)


# ---- friendly error messages (the API key is never part of any message) ----
@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, err: ServiceError):
    return JSONResponse(status_code=err.status_code, content={"detail": err.message})


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, err: SQLAlchemyError):
    return JSONResponse(status_code=500, content={"detail": "Database error. Please try again."})


# ---- API ----
app.include_router(nct.router)
app.include_router(pubmed.router)
app.include_router(trials.router)


@app.get("/api/health", tags=["System"])
def health():
    return {"status": "ok", "groq_configured": settings.groq_configured}


@app.get("/api/stats", tags=["System"])
def stats(db: Session = Depends(get_db)):
    return {"nct_studies": db.query(NCTStudy).count(),
            "pubmed_articles": db.query(Publication).count(),
            "clinical_trials": db.query(ClinicalTrial).count()}


# ---- pages ----
(settings.data_dir / "figures").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=settings.frontend_dir), name="static")
app.mount("/figures", StaticFiles(directory=settings.data_dir / "figures"), name="figures")  # only figures, not the DB


def _page(name: str):
    return FileResponse(settings.frontend_dir / name)


@app.get("/", include_in_schema=False)
def page_dashboard():
    return _page("index.html")


@app.get("/nct", include_in_schema=False)
def page_nct():
    return _page("nct.html")


@app.get("/pubmed", include_in_schema=False)
def page_pubmed():
    return _page("pubmed.html")


@app.get("/trials", include_in_schema=False)
def page_trials():
    return _page("trials.html")
