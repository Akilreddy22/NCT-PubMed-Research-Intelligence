"""
database.py - connects Python to SQLite using SQLAlchemy.

Engine         = the connection to the database file.
SessionLocal   = a factory that gives us a "session" (a conversation with the DB).
Base           = parent class for all our table classes (models).
get_db()       = FastAPI dependency: opens a session for a request, closes it after.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

settings.data_dir.mkdir(parents=True, exist_ok=True)

def normalize_database_url(url: str) -> str:
    """Supabase/Heroku style 'postgres://...' -> 'postgresql+psycopg2://...' (what SQLAlchemy expects)."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


DATABASE_URL = normalize_database_url(settings.database_url)
IS_SQLITE = DATABASE_URL.startswith("sqlite")

if IS_SQLITE:
    # check_same_thread=False is needed because FastAPI may use several threads with SQLite.
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # PostgreSQL (Supabase): cloud databases require SSL; pool_pre_ping re-opens connections
    # that the server closed while the free Render service was idle.
    connect_args = {} if "sslmode" in DATABASE_URL else {"sslmode": "require"}
    engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True, pool_recycle=300)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables that do not exist yet."""
    from app.models import nct, pubmed, trial  # noqa: F401  (import so tables are registered)
    Base.metadata.create_all(bind=engine)
