"""End-to-end tests of the HTTP endpoints, using sample data and a fake Groq."""
import pytest

from app.services.groq_service import GroqService


@pytest.fixture
def fake_groq(monkeypatch):
    def fake_chat(self, messages, model=None):
        return {"summary": "S", "key_findings": ["f1"], "study_type": "RCT", "study_population": "P",
                "methodology": "M", "investigating": "I", "intervention": "D", "indication": "X",
                "population": "Adults", "primary_objective": "Improve survival", "differentiator": "Neoadjuvant",
                "development_stage": "Phase 3", "figure_type": "graph", "description": "d"}
    monkeypatch.setattr(GroqService, "_chat", fake_chat)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    assert "api_key" not in r.text.lower()


def test_pages_are_served(client):
    for path in ("/", "/nct", "/pubmed", "/trials"):
        assert client.get(path).status_code == 200


def test_nct_demo_comparison(client):
    r = client.post("/api/nct/demo")
    assert r.status_code == 200
    body = r.json()
    assert body["change_count"] == 9 and body["previous_version"] == 1 and body["current_version"] == 2
    history = client.get("/api/nct/NCT99000001").json()
    assert len(history["versions"]) == 2 and history["history"][0]["changes"]


def test_nct_upload_and_compare_files(client, v1_html, v2_html):
    files = {"previous": ("a.html", v1_html, "text/html"), "current": ("b.html", v2_html, "text/html")}
    r = client.post("/api/nct/compare", files=files)
    assert r.status_code == 200 and r.json()["summary"]["modified"] == 9


def test_nct_invalid_inputs(client):
    assert client.post("/api/nct/fetch", json={"url": "https://example.com/NCT01234567"}).status_code == 400
    assert client.post("/api/nct/fetch", json={"url": "not a url"}).status_code == 400
    r = client.post("/api/nct/upload", files={"file": ("x.html", "   ", "text/html")})
    assert r.status_code == 400
    r = client.post("/api/nct/upload", files={"file": ("x.html", "<html><body><p>no id</p></body></html>", "text/html")})
    assert r.status_code == 400 and "NCT ID" in r.json()["detail"]
    assert client.get("/api/nct/NCT00000000").status_code == 404


def test_pubmed_sample_search_and_empty_search(client):
    r = client.get("/api/pubmed/search?use_sample=true")
    assert r.status_code == 200 and r.json()["count"] == 3
    assert client.get("/api/pubmed/search?query=").status_code == 400
    assert client.get("/api/pubmed/article/99000001").json()["authors"][0] == "Anna Rossi"


def test_pubmed_analyze_without_key(client):
    client.get("/api/pubmed/search?use_sample=true")
    r = client.post("/api/pubmed/analyze", json={"pmid": "99000001"})
    assert r.status_code == 503 and "GROQ_API_KEY" in r.json()["detail"]


def test_pubmed_analyze_and_figure(client, fake_groq):
    client.get("/api/pubmed/search?use_sample=true")
    r = client.post("/api/pubmed/analyze", json={"pmid": "99000001"})
    assert r.status_code == 200 and r.json()["summary"] == "S"
    assert client.get("/api/pubmed/article/99000001").json()["analysis"]["summary"] == "S"
    assert client.post("/api/pubmed/analyze", json={}).status_code == 400

    fig = client.get("/api/pubmed/article/99000001").json()["figures"][0]
    r = client.post("/api/pubmed/analyze-figure", json={"figure_id": fig["id"]})
    assert r.status_code == 200 and r.json()["analysis_type"] == "caption/context-based"


def test_trials_flow(client, fake_groq):
    r = client.get("/api/trials/search?drug=pembrolizumab&indication=melanoma&use_sample=true")
    assert r.status_code == 200 and r.json()["count"] == 3
    ids = [t["nct_id"] for t in r.json()["trials"]]

    r = client.post("/api/trials/analyze", json={"nct_ids": ids[:2]})
    assert r.status_code == 200 and r.json()["results"][0]["analysis"]["primary_objective"] == "Improve survival"
    assert client.post("/api/trials/analyze", json={"nct_ids": ids[:1]}).json()["results"][0]["cached"] is True

    r = client.post("/api/trials/compare", json={"nct_ids": ids})
    assert r.status_code == 200
    rows = {x["category"]: x for x in r.json()["rows"]}
    assert rows["Phase"]["differs"] and "Development Stage (AI)" in rows


def test_trials_validation(client):
    assert client.get("/api/trials/search?use_sample=true").status_code == 400
    assert client.post("/api/trials/compare", json={"nct_ids": ["NCT99000001"]}).status_code == 422
    assert client.post("/api/trials/compare", json={"nct_ids": ["NCT11111111", "NCT22222222"]}).status_code == 404


def test_postgres_url_is_normalized():
    from app.database import normalize_database_url
    assert normalize_database_url("postgres://u:p@h:5432/db") == "postgresql+psycopg2://u:p@h:5432/db"
    assert normalize_database_url("postgresql://u:p@h:5432/db") == "postgresql+psycopg2://u:p@h:5432/db"
    assert normalize_database_url("sqlite:///./x.db") == "sqlite:///./x.db"
