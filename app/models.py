from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("asset_type", "identifier", name="uq_asset_identity"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    identifier = Column(String(512), nullable=False, index=True)
    asset_type = Column(String(50), nullable=False)
    criticality = Column(Integer, nullable=False, default=3)
    meta = Column("metadata", JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    incidents = relationship("Incident", back_populates="asset")


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    url = Column(Text, nullable=False)
    source_type = Column(String(50), nullable=False)
    use_tor = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    raw_documents = relationship(
        "RawDocument", back_populates="source", cascade="all, delete-orphan"
    )


class RawDocument(Base):
    __tablename__ = "raw_documents"
    __table_args__ = (
        UniqueConstraint("source_id", "content_hash", name="uq_source_content_hash"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False, index=True)
    url = Column(Text, nullable=False)
    body_raw = Column(Text, nullable=False)
    body_text = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=False)
    status = Column(String(30), nullable=False, default="fetched")
    meta = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    source = relationship("Source", back_populates="raw_documents")
    iocs = relationship("IOC", back_populates="raw_document", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="raw_document")


class IOC(Base):
    __tablename__ = "iocs"
    __table_args__ = (
        UniqueConstraint(
            "raw_document_id",
            "ioc_type",
            "normalized_value",
            name="uq_document_ioc",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    raw_document_id = Column(
        Integer, ForeignKey("raw_documents.id"), nullable=False, index=True
    )
    ioc_type = Column(String(50), nullable=False)
    value = Column(String(2048), nullable=False)
    normalized_value = Column(String(2048), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    raw_document = relationship("RawDocument", back_populates="iocs")
    incidents = relationship("Incident", back_populates="ioc")


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    ioc_id = Column(Integer, ForeignKey("iocs.id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    raw_document_id = Column(
        Integer, ForeignKey("raw_documents.id"), nullable=False, index=True
    )
    dedup_key = Column(String(64), nullable=False, unique=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(Integer, nullable=False)
    source_type = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False, default="open")
    extra = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    ioc = relationship("IOC", back_populates="incidents")
    asset = relationship("Asset", back_populates="incidents")
    raw_document = relationship("RawDocument", back_populates="incidents")
