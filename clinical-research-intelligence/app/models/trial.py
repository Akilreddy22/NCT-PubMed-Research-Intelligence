"""
Module 3 tables.

ClinicalTrial 1 ---- * TrialAnalysis   (AI interpretation of the trial)
The full structured trial is stored as JSON text in data_json (simple + flexible);
a few important columns are also stored separately so we can search/filter quickly.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.nct import utcnow


class ClinicalTrial(Base):
    __tablename__ = "clinical_trials"
    id: Mapped[int] = mapped_column(primary_key=True)
    nct_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    title: Mapped[str] = mapped_column(Text, default="")
    phase: Mapped[str] = mapped_column(String(50), default="")
    recruitment_status: Mapped[str] = mapped_column(String(50), default="")
    search_drug: Mapped[str] = mapped_column(String(200), default="")
    search_indication: Mapped[str] = mapped_column(String(200), default="")
    last_update_date: Mapped[str] = mapped_column(String(20), default="")
    data_json: Mapped[str] = mapped_column(Text)        # full parsed trial as JSON text
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    analyses = relationship("TrialAnalysis", back_populates="trial",
                            cascade="all, delete-orphan", order_by="TrialAnalysis.id")


class TrialAnalysis(Base):
    __tablename__ = "trial_analyses"
    id: Mapped[int] = mapped_column(primary_key=True)
    trial_id: Mapped[int] = mapped_column(ForeignKey("clinical_trials.id"))
    analysis_json: Mapped[str] = mapped_column(Text)    # the 7 answers from Groq as JSON text
    model_used: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    trial = relationship("ClinicalTrial", back_populates="analyses")
