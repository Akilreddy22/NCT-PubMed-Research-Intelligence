"""Module 2 endpoints:  /api/pubmed/..."""
import json
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import ServiceError
from app.models.pubmed import AIAnalysis, Figure, Publication
from app.schemas.pubmed import AnalyzeRequest, FigureAnalyzeRequest, FiguresRequest
from app.services import pubmed_service as ps
from app.services.groq_service import GroqService
from app.services.storage import save_figure

router = APIRouter(prefix="/api/pubmed", tags=["PubMed"])


def _get_pub(db: Session, pmid: str) -> Publication:
    pub = db.query(Publication).filter_by(pmid=pmid.strip()).first()
    if pub is None:
        raise ServiceError("Article not found. Search for it first so it is saved.", 404)
    return pub


@router.get("/search")
def search(query: str = Query(""), max_results: int = Query(10, ge=1, le=25), use_sample: bool = False,
           db: Session = Depends(get_db)):
    """Search PubMed, save every article to SQLite, return them."""
    if use_sample:
        articles, source = ps.load_sample_articles(), "sample"
    else:
        articles, source = ps.fetch_articles(query, max_results), "pubmed"
    saved = [ps.publication_to_dict(ps.save_publication(db, a)) for a in articles]
    return {"source": source, "count": len(saved), "articles": saved}


@router.get("/article/{pmid}")
def get_article(pmid: str, db: Session = Depends(get_db)):
    pub = db.query(Publication).filter_by(pmid=pmid.strip()).first()
    if pub is None:                                   # not stored yet -> try PubMed itself
        articles = ps.parse_pubmed_xml(ps.get_pubmed_article(pmid.strip()))
        if not articles:
            raise ServiceError("No article with this PMID.", 404)
        pub = ps.save_publication(db, articles[0])
    return ps.publication_to_dict(pub)


@router.post("/analyze")
def analyze(body: AnalyzeRequest, db: Session = Depends(get_db)):
    """Send an abstract to Groq -> summary, key findings, study type, population."""
    pub = None
    if body.pmid:
        pub = _get_pub(db, body.pmid)
        text = f"Title: {pub.title}\n\nAbstract:\n{pub.abstract}"
        if pub.full_text:
            text += f"\n\nFull text (start):\n{pub.full_text[:6000]}"
    elif body.abstract:
        text = body.abstract
    else:
        raise ServiceError("Send either a pmid or an abstract.", 400)

    groq = GroqService()
    result = groq.summarize_article(text)
    if pub is not None:
        db.add(AIAnalysis(publication_id=pub.id, summary=result["summary"],
                          key_findings=json.dumps(result["key_findings"]),
                          study_population=result["study_population"], methodology=result["methodology"],
                          study_type=result["study_type"], model_used=groq.model))
        db.commit()
    return {"pmid": body.pmid, "model": groq.model, **result}


@router.post("/figures")
def get_figures(body: FiguresRequest, db: Session = Depends(get_db)):
    """Get full text + figures from PubMed Central (open-access only) and download the image files."""
    pub = _get_pub(db, body.pmid)
    notes = []
    if pub.pmcid:
        content = ps.get_pmc_content(pub.pmcid)
        if content["full_text"]:
            pub.full_text = content["full_text"]
        existing = {f.label for f in pub.figures}
        for fig in content["figures"]:
            if fig["label"] not in existing:
                pub.figures.append(Figure(label=fig["label"], caption=fig["caption"], image_url=fig["image_url"]))
        db.commit()
        if not content["figures"]:
            notes.append("This article has no open-access figures in PubMed Central.")
    else:
        notes.append("This article has no PubMed Central ID, so no open full text is available. "
                     "Only captions already saved (if any) can be analyzed.")

    downloaded = 0
    for fig in pub.figures:
        if fig.image_url and not fig.local_path:
            content_bytes, mime = ps.download_image(fig.image_url)
            if content_bytes:
                ext = mime.split("/")[-1] or "jpg"
                fig.local_path = save_figure(pub.pmid, f"{fig.id}_{fig.label or 'figure'}.{ext}", content_bytes)
                downloaded += 1
    db.commit()
    if pub.figures and downloaded == 0 and not any(f.local_path for f in pub.figures):
        notes.append("Image files could not be downloaded; analysis will use captions only.")
    db.refresh(pub)
    return {"pmid": pub.pmid, "figures_found": len(pub.figures), "images_downloaded": downloaded,
            "notes": notes, "article": ps.publication_to_dict(pub)}


@router.post("/analyze-figure")
def analyze_figure(body: FigureAnalyzeRequest, db: Session = Depends(get_db)):
    """Groq reads the figure image (if we have it) + caption + article context."""
    fig = db.get(Figure, body.figure_id)
    if fig is None:
        raise ServiceError("Figure not found.", 404)
    pub = fig.publication
    context = f"Title: {pub.title}\nAbstract: {pub.abstract}"

    image_bytes, mime = None, "image/jpeg"
    if fig.local_path and Path(fig.local_path).exists():
        image_bytes = Path(fig.local_path).read_bytes()
        mime = {"png": "image/png", "gif": "image/gif", "webp": "image/webp"}.get(
            Path(fig.local_path).suffix.lstrip(".").lower(), "image/jpeg")

    groq, note = GroqService(), ""
    try:
        result = groq.analyze_figure(fig.caption, context, image_bytes, mime)
    except ServiceError:
        if image_bytes is None:
            raise
        result = groq.analyze_figure(fig.caption, context, None)      # fall back to caption only
        note = "The image could not be analyzed, so only the caption and article context were used."
    fig.ai_analysis = json.dumps(result)
    fig.analysis_type = result.get("analysis_type", "")
    db.commit()
    return {"figure_id": fig.id, "label": fig.label, "analysis_type": fig.analysis_type, "note": note,
            "analysis": result}
