"""
pubmed_service.py - talks to PubMed through NCBI "E-utilities" (free official API).

  1) SEARCH   esearch.fcgi  : text query  -> list of PMIDs (article ids)
  2) DETAILS  efetch.fcgi   : PMIDs       -> XML with title, abstract, authors, journal, DOI ...
  3) PARSE    xml.etree     : XML text    -> Python dictionary
  4) FULL TEXT + FIGURES    : if the article has a PMC id (free full text), efetch from db=pmc gives
                              JATS XML that contains <fig> tags (label, caption, image file name).
  5) STORE    save_publication() writes everything to SQLite; image FILES go to storage.py.
No AI is used in this file.
"""
import json
import time
from pathlib import Path
import xml.etree.ElementTree as ET

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import ServiceError
from app.models.pubmed import Author, Figure, Publication
from app.services.nct_parser import normalize_text

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
EPMC_BIN = "https://europepmc.org/articles/"          # Europe PMC serves figure files reliably
NCBI_BIN = "https://pmc.ncbi.nlm.nih.gov/articles/"   # NCBI sometimes blocks automated downloads
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp")
STUDY_TYPE_PRIORITY = ["Randomized Controlled Trial", "Meta-Analysis", "Systematic Review", "Clinical Trial",
                       "Review", "Case Reports", "Observational Study", "Comparative Study"]
_last_call = [0.0]


def _get(path: str, params: dict) -> httpx.Response:
    """GET with the polite NCBI rules: max ~3 requests/second, identify ourselves."""
    wait = 0.4 - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    params = {**params, "tool": "clinical-research-intelligence"}
    if settings.ncbi_email:
        params["email"] = settings.ncbi_email
    if settings.ncbi_api_key:
        params["api_key"] = settings.ncbi_api_key
    try:
        response = httpx.get(f"{EUTILS}/{path}", params=params, timeout=30)
    except httpx.HTTPError:
        raise ServiceError("PubMed is not reachable right now. Check your internet or tick 'Use sample data'.", 503)
    finally:
        _last_call[0] = time.time()
    if response.status_code != 200:
        raise ServiceError(f"PubMed returned an error (HTTP {response.status_code}).", 502)
    return response


# ------------------------------------------------------------------ 1. search
def search_pubmed(query: str, max_results: int = 10) -> list:
    """Return a list of PMIDs (strings) for the query."""
    if not query or not query.strip():
        raise ServiceError("Please type a search topic.", 400)
    response = _get("esearch.fcgi", {"db": "pubmed", "term": query.strip(), "retmax": max_results,
                                     "retmode": "json", "sort": "relevance"})
    try:
        return response.json()["esearchresult"]["idlist"]
    except (KeyError, ValueError):
        raise ServiceError("PubMed sent an unexpected reply.", 502)


# ------------------------------------------------------------------ 2. details
def get_pubmed_article(pmid: str) -> str:
    """Return the raw XML text for one (or several comma-separated) PMIDs."""
    return _get("efetch.fcgi", {"db": "pubmed", "id": pmid, "retmode": "xml"}).text


# ------------------------------------------------------------------ 3. parse
def _text(element) -> str:
    """All text inside an element (also text inside inner tags such as <i>)."""
    return normalize_text("".join(element.itertext())) if element is not None else ""


def parse_pubmed_article(article) -> dict:
    """One <PubmedArticle> XML element -> dictionary."""
    citation = article.find("MedlineCitation")
    art = citation.find("Article") if citation is not None else None
    if art is None:
        raise ValueError("Unexpected PubMed XML.")

    abstract_parts = []
    for part in art.findall("Abstract/AbstractText"):
        label = part.get("Label")
        abstract_parts.append(f"{label}: {_text(part)}" if label else _text(part))

    authors = []
    for a in art.findall("AuthorList/Author"):
        name = f"{_text(a.find('ForeName'))} {_text(a.find('LastName'))}".strip() or _text(a.find("CollectiveName"))
        if name:
            authors.append(name)

    pub_date = art.find("Journal/JournalIssue/PubDate")
    date_text = ""
    if pub_date is not None:
        date_text = (_text(pub_date.find("MedlineDate")) or
                     " ".join(_text(pub_date.find(t)) for t in ("Year", "Month", "Day") if pub_date.find(t) is not None))

    doi = next((_text(e) for e in art.findall("ELocationID") if e.get("EIdType") == "doi"), "")
    pmcid = ""
    for aid in article.findall("PubmedData/ArticleIdList/ArticleId"):
        if aid.get("IdType") == "doi" and not doi:
            doi = _text(aid)
        if aid.get("IdType") == "pmc":
            pmcid = _text(aid)

    pub_types = [_text(t) for t in art.findall("PublicationTypeList/PublicationType")]
    study_type = next((t for t in STUDY_TYPE_PRIORITY if t in pub_types), pub_types[0] if pub_types else "")
    mesh = [_text(m) for m in citation.findall("MeshHeadingList/MeshHeading/DescriptorName")]

    return {
        "pmid": _text(citation.find("PMID")),
        "title": _text(art.find("ArticleTitle")),
        "authors": authors,
        "abstract": "\n".join(abstract_parts),
        "journal": _text(art.find("Journal/Title")),
        "publication_date": date_text,
        "doi": doi,
        "pmcid": pmcid,
        "keywords": [_text(k) for k in citation.findall("KeywordList/Keyword")],
        "study_type": study_type,
        "research_topic": ", ".join(mesh[:3]),
        "references": [_text(r.find("Citation")) for r in article.findall("PubmedData/ReferenceList/Reference")][:30],
        "full_text": "",
        "figures": [],
    }


def parse_pubmed_xml(xml_text: str) -> list:
    """Whole efetch XML -> list of article dictionaries."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        raise ServiceError("PubMed sent XML that could not be read.", 502)
    articles = []
    for node in root.findall("PubmedArticle"):
        try:
            articles.append(parse_pubmed_article(node))
        except ValueError:
            continue
    return articles


def fetch_articles(query: str, max_results: int = 10) -> list:
    """search -> fetch -> parse in one call."""
    pmids = search_pubmed(query, max_results)
    if not pmids:
        return []
    return parse_pubmed_xml(get_pubmed_article(",".join(pmids)))


def load_sample_articles() -> list:
    with open(settings.sample_dir / "sample_pubmed.json", encoding="utf-8") as f:
        return json.load(f)["articles"]


# ------------------------------------------------------------------ 4. full text + figures
def parse_pmc_xml(xml_text: str, pmcid: str) -> dict:
    """PMC 'JATS' XML -> {'full_text': str, 'figures': [{label, caption, image_url}]}"""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return {"full_text": "", "figures": []}
    paragraphs = [_text(p) for p in root.findall(".//body//p")]
    figures = []
    for fig in root.iter("fig"):
        graphic = fig.find("graphic")
        href = graphic.get(XLINK_HREF, "") if graphic is not None else ""
        file_name = href if href.lower().endswith(IMAGE_EXT) else f"{href}.jpg"
        url = href if href.startswith("http") else (f"{EPMC_BIN}{pmcid}/bin/{file_name}" if href else "")
        figures.append({"label": _text(fig.find("label")), "caption": _text(fig.find("caption")), "image_url": url})
    return {"full_text": "\n\n".join(p for p in paragraphs if p)[:60000], "figures": figures}


def get_pmc_content(pmcid: str) -> dict:
    """Download full text + figure list for open-access PMC articles. Empty result if not available."""
    if not pmcid:
        return {"full_text": "", "figures": []}
    xml_text = _get("efetch.fcgi", {"db": "pmc", "id": pmcid, "retmode": "xml"}).text
    return parse_pmc_xml(xml_text, pmcid)


def image_url_alternatives(url: str) -> list:
    """Same figure on the other PMC mirror, so we can try both."""
    if url.startswith(EPMC_BIN):
        return [url, NCBI_BIN + url[len(EPMC_BIN):]]
    if url.startswith(NCBI_BIN):
        return [EPMC_BIN + url[len(NCBI_BIN):], url]
    return [url]


def download_image(url: str):
    """Try each mirror. Return (bytes, mime_type) or (None, '') if none works."""
    if not url:
        return None, ""
    for candidate in image_url_alternatives(url):
        try:
            response = httpx.get(candidate, timeout=30, follow_redirects=True,
                                 headers={"User-Agent": "Mozilla/5.0 (research-demo)"})
        except httpx.HTTPError:
            continue
        mime = response.headers.get("content-type", "").split(";")[0]
        if response.status_code == 200 and mime.startswith("image/"):
            return response.content, mime
    return None, ""


# ------------------------------------------------------------------ 5. database
def save_publication(db: Session, article: dict) -> Publication:
    """Insert or update a publication (matched by PMID), with its authors and figures."""
    pub = db.query(Publication).filter_by(pmid=article["pmid"]).first()
    if pub is None:
        pub = Publication(pmid=article["pmid"])
        db.add(pub)
    pub.title, pub.abstract = article.get("title", ""), article.get("abstract", "")
    pub.journal, pub.publication_date = article.get("journal", ""), article.get("publication_date", "")
    pub.doi, pub.pmcid = article.get("doi", ""), article.get("pmcid", "")
    pub.study_type, pub.research_topic = article.get("study_type", ""), article.get("research_topic", "")
    pub.keywords = json.dumps(article.get("keywords", []))
    pub.references_json = json.dumps(article.get("references", []))
    if article.get("full_text"):
        pub.full_text = article["full_text"]
    pub.authors = [Author(name=n) for n in article.get("authors", [])]
    existing = {f.label for f in pub.figures}
    for fig in article.get("figures", []):
        if fig.get("label") not in existing:
            pub.figures.append(Figure(label=fig.get("label", ""), caption=fig.get("caption", ""),
                                      image_url=fig.get("image_url", "")))
    db.commit()
    db.refresh(pub)
    return pub


def figure_web_url(local_path: str) -> str:
    """data/figures/<pmid>/<file>  ->  /figures/<pmid>/<file>  (served by main.py)"""
    if not local_path or not Path(local_path).exists():   # e.g. Render wiped its disk
        return ""
    parts = Path(local_path).parts
    return "/figures/" + "/".join(parts[-2:])


def publication_to_dict(pub: Publication) -> dict:
    latest = pub.analyses[-1] if pub.analyses else None
    return {
        "pmid": pub.pmid, "title": pub.title, "abstract": pub.abstract, "journal": pub.journal,
        "publication_date": pub.publication_date, "doi": pub.doi, "pmcid": pub.pmcid,
        "study_type": pub.study_type, "research_topic": pub.research_topic,
        "keywords": json.loads(pub.keywords or "[]"), "references": json.loads(pub.references_json or "[]"),
        "has_full_text": bool(pub.full_text), "authors": [a.name for a in pub.authors],
        "figures": [{"id": f.id, "label": f.label, "caption": f.caption, "image_url": f.image_url,
                     "web_url": figure_web_url(f.local_path), "analysis_type": f.analysis_type,
                     "ai_analysis": json.loads(f.ai_analysis) if f.ai_analysis else None} for f in pub.figures],
        "analysis": ({"summary": latest.summary, "key_findings": json.loads(latest.key_findings or "[]"),
                      "study_population": latest.study_population, "methodology": latest.methodology,
                      "study_type": latest.study_type, "model_used": latest.model_used} if latest else None),
    }