from sqlalchemy import (
    Column,
    BigInteger,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.sql import func
from app.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    identifier = Column(String, nullable=False)
    criticality = Column(Integer, default=3)
    metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Source(Base):
    __tablename__ = "sources"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    url = Column(String, nullable=False)
    use_tor = Column(Boolean, default=False)
    parser_type = Column(String, nullable=True)
    config = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class RawDocument(Base):
    __tablename__ = "raw_documents"

    id = Column(BigInteger, primary_key=True, index=True)
    source_id = Column(BigInteger, ForeignKey("sources.id"), nullable=False)
    url = Column(String, nullable=False)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="fetched")

    body_raw = Column(Text, nullable=True)
    body_text = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(BigInteger, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(Integer, default=1)
    source_type = Column(String, nullable=False)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    extra = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
