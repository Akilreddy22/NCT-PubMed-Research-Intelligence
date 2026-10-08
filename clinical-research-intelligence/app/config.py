"""
config.py - reads settings from the .env file ONE time, in ONE place.
The rest of the app does:  from app.config import settings
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent   # the project root folder
load_dotenv(BASE_DIR / ".env")                      # loads .env into os.environ


class Settings:
    def __init__(self):
        # Groq
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.groq_vision_model = os.getenv(
            "GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
        # Database + folders
        self.data_dir = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
        self.database_url = os.getenv("DATABASE_URL", f"sqlite:///{self.data_dir / 'app.db'}")
        self.sample_dir = BASE_DIR / "data" / "sample"
        self.frontend_dir = BASE_DIR / "frontend"
        # NCBI (optional)
        self.ncbi_email = os.getenv("NCBI_EMAIL", "")
        self.ncbi_api_key = os.getenv("NCBI_API_KEY", "")

    @property
    def groq_configured(self) -> bool:
        return bool(self.groq_api_key) and self.groq_api_key != "your_api_key_here"


settings = Settings()
