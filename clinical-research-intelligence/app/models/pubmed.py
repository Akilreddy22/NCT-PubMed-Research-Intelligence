"""
Module 2 tables.

Publication 1 ---- * Author
Publication 1 ---- * Figure
Publication 1 ---- * AIAnalysis
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.nct import utcnow


class Publication(Base):
    __tablename__ = "publications"
    id: Mapped[int] = mapped_column(primary_key=True)
    pmid: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    title: Mapped[str] = mapped_column(Text, default="")
    abstract: Mapped[str] = mapped_column(Text, default="")
    journal: Mapped[str] = mapped_column(Text, default="")
    publication_date: Mapped[str] = mapped_column(String(30), default="")
    doi: Mapped[str] = mapped_column(String(100), default="")
    pmcid: Mapped[str] = mapped_column(String(20), default="")
    study_type: Mapped[str] = mapped_column(String(100), default="")
    research_topic: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[str] = mapped_column(Text, default="[]")       # JSON list as text
    references_json: Mapped[str] = mapped_column(Text, default="[]")  # JSON list as text
    full_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    authors = relationship("Author", back_populates="publication", cascade="all, delete-orphan")
    figures = relationship("Figure", back_populates="publication", cascade="all, delete-orphan")
    analyses = relationship("AIAnalysis", back_populates="publication",
                            cascade="all, delete-orphan", order_by="AIAnalysis.id")


class Author(Base):
    __tablename__ = "authors"
    id: Mapped[int] = mapped_column(primary_key=True)
    publication_id: Mapped[int] = mapped_column(ForeignKey("publications.id"))
    name: Mapped[str] = mapped_column(String(200))
    publication = relationship("Publication", back_populates="authors")


class Figure(Base):
    __tablename__ = "figures"
    id: Mapped[int] = mapped_column(primary_key=True)
    publication_id: Mapped[int] = mapped_column(ForeignKey("publications.id"))
    label: Mapped[str] = mapped_column(String(100), default="")
    image_url: Mapped[str] = mapped_column(Text, default="")
    caption: Mapped[str] = mapped_column(Text, default="")
    local_path: Mapped[str] = mapped_column(Text, default="")     # where the file is saved
    ai_analysis: Mapped[str] = mapped_column(Text, default="")    # JSON text from Groq
    analysis_type: Mapped[str] = mapped_column(String(40), default="")  # "image+caption" or "caption/context-based"
    publication = relationship("Publication", back_populates="figures")


class AIAnalysis(Base):
    __tablename__ = "ai_analyses"
    id: Mapped[int] = mapped_column(primary_key=True)
    publication_id: Mapped[int] = mapped_column(ForeignKey("publications.id"))
    summary: Mapped[str] = mapped_column(Text, default="")
    key_findings: Mapped[str] = mapped_column(Text, default="[]")  # JSON list as text
    study_population: Mapped[str] = mapped_column(Text, default="")
    methodology: Mapped[str] = mapped_column(Text, default="")
    study_type: Mapped[str] = mapped_column(String(100), default="")
    model_used: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    publication = relationship("Publication", back_populates="analyses")
