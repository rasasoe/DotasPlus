# app/models.py

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Asset(Base):
    """
    회사/조직이 등록하는 보호 대상 자산
    - 예: 도메인, 이메일, 브랜드 키워드 등
    """

    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)          # 자산 이름 (설명용)
    asset_type = Column(String(50), nullable=False)     # domain / email / keyword 등

    # ⚠️ SQLAlchemy 예약어(metadata) 충돌을 피하기 위해
    #  - Python 속성 이름: meta
    #  - DB 컬럼 이름   : metadata
    meta = Column("metadata", JSON, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    incidents = relationship("Incident", back_populates="asset")

    def __repr__(self) -> str:
        return f"<Asset id={self.id} type={self.asset_type} name={self.name!r}>"


class Source(Base):
    """
    크롤링 대상 외부 소스
    - 예: 다크웹 포럼, 유출 데이터 사이트, 랜섬웨어 블로그, OSINT 피드 등
    """

    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)          # 소스 이름
    url = Column(Text, nullable=False)                  # base URL 또는 feed URL
    source_type = Column(String(50), nullable=False)    # darkweb / surface / api 등
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    raw_documents = relationship("RawDocument", back_populates="source")

    def __repr__(self) -> str:
        return f"<Source id={self.id} type={self.source_type} name={self.name!r}>"


class RawDocument(Base):
    """
    크롤러가 가져온 '원본 문서'
    - HTML / 텍스트 / JSON 등 전체를 그대로 저장
    """

    __tablename__ = "raw_documents"

    row_id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)

    # 크롤링한 원본 (HTML, 텍스트 등)
    html_raw = Column(Text, nullable=False)

    # 크롤링 시각
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    source = relationship("Source", back_populates="raw_documents")
    incidents = relationship("Incident", back_populates="raw_document")

    def __repr__(self) -> str:
        return f"<RawDocument row_id={self.row_id} source_id={self.source_id}>"


class IOC(Base):
    """
    LLM/정규화 단계에서 추출된 Indicator of Compromise
    - type: email / domain / ip / btc_address / etc
    - value: 실제 값
    """

    __tablename__ = "iocs"

    ioc_id = Column(Integer, primary_key=True, index=True)

    ioc_type = Column(String(50), nullable=False)   # email / domain / ip / ...
    value = Column(String(512), nullable=False, index=True)

    # 어떤 RawDocument에서 뽑힌 IOC인지 추적하고 싶다면 FK 추가 가능
    raw_document_id = Column(
        Integer,
        ForeignKey("raw_documents.row_id"),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    raw_document = relationship("RawDocument")
    incidents = relationship("Incident", back_populates="ioc")

    def __repr__(self) -> str:
        return f"<IOC id={self.ioc_id} type={self.ioc_type} value={self.value!r}>"


class Incident(Base):
    """
    IOC + Asset 매칭 결과로 생성되는 Incident
    - "이 IOC가 우리 회사 자산과 연결된다"는 탐지 결과
    """

    __tablename__ = "incidents"

    incident_id = Column(Integer, primary_key=True, index=True)

    ioc_id = Column(Integer, ForeignKey("iocs.ioc_id"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    raw_document_id = Column(
        Integer,
        ForeignKey("raw_documents.row_id"),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # 관계 설정
    ioc = relationship("IOC", back_populates="incidents")
    asset = relationship("Asset", back_populates="incidents")
    raw_document = relationship("RawDocument", back_populates="incidents")

    def __repr__(self) -> str:
        return (
            f"<Incident id={self.incident_id} "
            f"ioc_id={self.ioc_id} asset_id={self.asset_id} "
            f"raw_document_id={self.raw_document_id}>"
        )
