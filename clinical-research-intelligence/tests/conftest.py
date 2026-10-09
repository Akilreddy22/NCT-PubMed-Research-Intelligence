"""Runs before every test: use a temporary data folder + temporary database (never touches your real data)."""
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["GROQ_API_KEY"] = ""          # tests must never call the real Groq

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:           # 'with' runs startup -> creates tables
        yield c


@pytest.fixture
def v1_html():
    return (settings.sample_dir / "nct_v1.html").read_text(encoding="utf-8")


@pytest.fixture
def v2_html():
    return (settings.sample_dir / "nct_v2.html").read_text(encoding="utf-8")
