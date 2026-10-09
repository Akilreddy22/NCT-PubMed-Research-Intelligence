"""
Module 1 tables.

NCTStudy  1 ---- *  NCTVersion      (one study has many saved versions)
NCTStudy  1 ---- *  NCTChange       (one study has many detected changes)
NCTVersion is referenced twice by NCTChange (previous_version_id, current_version_id).
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class NCTStudy(Base):
    __tablename__ = "nct_studies"
    id: Mapped[int] = mapped_column(primary_key=True)
    nct_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    title: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    versions = relationship("NCTVersion", back_populates="study",
                            order_by="NCTVersion.version_number", cascade="all, delete-orphan")
    changes = relationship("NCTChange", back_populates="study", cascade="all, delete-orphan")


class NCTVersion(Base):
    __tablename__ = "nct_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("nct_studies.id"))
    version_number: Mapped[int] = mapped_column(Integer)
    raw_html_path: Mapped[str] = mapped_column(Text, default="")
    extracted_json: Mapped[str] = mapped_column(Text)          # the normalized dict as JSON text
    content_hash: Mapped[str] = mapped_column(String(64), index=True)  # to avoid saving duplicates
    source: Mapped[str] = mapped_column(String(30), default="upload")  # upload | html_url | api
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    study = relationship("NCTStudy", back_populates="versions")


class NCTChange(Base):
    __tablename__ = "nct_changes"
    id: Mapped[int] = mapped_column(primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("nct_studies.id"))
    previous_version_id: Mapped[int] = mapped_column(ForeignKey("nct_versions.id"))
    current_version_id: Mapped[int] = mapped_column(ForeignKey("nct_versions.id"))
    field_name: Mapped[str] = mapped_column(String(100))
    change_type: Mapped[str] = mapped_column(String(20))       # added | removed | modified
    previous_value: Mapped[str] = mapped_column(Text, default="")
    new_value: Mapped[str] = mapped_column(Text, default="")
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    study = relationship("NCTStudy", back_populates="changes")
