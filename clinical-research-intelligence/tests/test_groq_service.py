import json

import httpx
import pytest

from app.errors import ServiceError
from app.services.groq_service import GroqService


class FakeResponse:
    def __init__(self, status=200, content=None):
        self.status_code = status
        self._content = content if content is not None else {}

    def json(self):
        return {"choices": [{"message": {"content": json.dumps(self._content) if isinstance(self._content, dict) else self._content}}]}


def test_missing_key_gives_friendly_error():
    with pytest.raises(ServiceError) as err:
        GroqService(api_key="").summarize_article("some abstract")
    assert err.value.status_code == 503 and "GROQ_API_KEY" in err.value.message


def test_summarize_fills_missing_keys(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResponse(content={"summary": "S", "key_findings": ["a"]}))
    r = GroqService(api_key="k").summarize_article("abstract")
    assert r["summary"] == "S" and r["study_population"] == "Not stated"


def test_json_inside_code_fence_is_parsed(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResponse(content='```json\n{"summary": "ok"}\n```'))
    assert GroqService(api_key="k").summarize_article("x")["summary"] == "ok"


def test_rate_limit_message(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResponse(status=429))
    with pytest.raises(ServiceError) as err:
        GroqService(api_key="k").analyze_trial("trial")
    assert err.value.status_code == 429


def test_network_error(monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectError("down")
    monkeypatch.setattr(httpx, "post", boom)
    with pytest.raises(ServiceError) as err:
        GroqService(api_key="k").analyze_trial("trial")
    assert err.value.status_code == 503


def test_figure_mode_is_labelled_honestly(monkeypatch):
    sent = {}

    def fake_post(url, json=None, **k):
        sent["body"] = json
        return FakeResponse(content={"description": "d"})
    monkeypatch.setattr(httpx, "post", fake_post)
    svc = GroqService(api_key="k", model="text-model", vision_model="vision-model")

    caption_only = svc.analyze_figure("caption", "context")
    assert caption_only["analysis_type"] == "caption/context-based" and sent["body"]["model"] == "text-model"

    with_image = svc.analyze_figure("caption", "context", image_bytes=b"\xff\xd8fake")
    assert with_image["analysis_type"] == "image+caption" and sent["body"]["model"] == "vision-model"
    assert sent["body"]["messages"][1]["content"][1]["type"] == "image_url"
