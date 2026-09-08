from __future__ import annotations

import hashlib
from urllib.parse import urlsplit

import requests
from celery import shared_task
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.intelligence import extract_indicators
from app.models import Incident, RawDocument, Source
from app.pipeline import create_incidents, persist_iocs


def _get_db() -> Session:
    return SessionLocal()


def _request_options(source: Source) -> dict:
    parsed = urlsplit(source.url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError("Source URL must use http or https and include a host.")

    is_onion = parsed.hostname.lower().endswith(".onion")
    if is_onion and not source.use_tor:
        raise RuntimeError("Onion source requires use_tor=true; refusing direct request.")

    hostname = parsed.hostname.lower()
    allowed = any(
        hostname == item or hostname.endswith(f".{item}")
        for item in settings.SOURCE_HOST_ALLOWLIST
    )
    if not allowed:
        raise RuntimeError(
            f"Source host {hostname!r} is not present in SOURCE_HOST_ALLOWLIST."
        )

    options = {
        "timeout": 15,
        "allow_redirects": False,
        "headers": {"User-Agent": "DotasPlus/0.2 defensive-cti"},
    }
    if source.use_tor:
        proxy = (settings.TOR_PROXY_URL or "").strip()
        if not proxy:
            raise RuntimeError(
                "Source requires Tor, but TOR_PROXY_URL is not configured; refusing direct request."
            )
        if not proxy.lower().startswith("socks5h://"):
            raise RuntimeError("TOR_PROXY_URL must use the socks5h:// scheme.")
        options["proxies"] = {"http": proxy, "https": proxy}
    return options


@shared_task(name="app.tasks.crawl_source")
def crawl_source(source_id: int) -> str:
    db = _get_db()
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            return f"Source {source_id} not found"
        if not source.is_active:
            return f"Source {source_id} is inactive"

        response = requests.get(source.url, **_request_options(source))
        if response.is_redirect:
            raise RuntimeError(
                "Source redirect refused; review and allowlist the destination explicitly."
            )
        response.raise_for_status()
        content_hash = hashlib.sha256(response.content).hexdigest()
        existing = (
            db.query(RawDocument)
            .filter(
                RawDocument.source_id == source.id,
                RawDocument.content_hash == content_hash,
            )
            .first()
        )
        if existing:
            return f"Duplicate content skipped: raw_document_id={existing.id}"

        document = RawDocument(
            source_id=source.id,
            url=source.url,
            body_raw=response.text,
            content_hash=content_hash,
            status="fetched",
            meta={"http_status": response.status_code},
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        normalize_document.delay(document.id)
        return f"Fetched source_id={source.id} -> raw_document_id={document.id}"
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(name="app.tasks.normalize_document")
def normalize_document(raw_document_id: int) -> str:
    db = _get_db()
    try:
        document = db.query(RawDocument).filter(RawDocument.id == raw_document_id).first()
        if not document:
            return f"RawDocument {raw_document_id} not found"

        body_text, indicators = extract_indicators(document.body_raw)
        document.body_text = body_text
        document.status = "normalized"
        document.meta = {
            **(document.meta or {}),
            "indicator_count": len(indicators),
        }
        created = persist_iocs(db, document, indicators)
        db.commit()
        match_incident.delay(document.id)
        return f"Normalized raw_document_id={document.id}; new_iocs={len(created)}"
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(name="app.tasks.match_incident")
def match_incident(raw_document_id: int) -> str:
    db = _get_db()
    try:
        document = db.query(RawDocument).filter(RawDocument.id == raw_document_id).first()
        if not document:
            return f"RawDocument {raw_document_id} not found"
        incidents = create_incidents(db, document)
        document.status = "matched"
        db.commit()
        for incident in incidents:
            send_alert.delay(incident.id)
        return f"Matched raw_document_id={document.id}; new_incidents={len(incidents)}"
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(name="app.tasks.send_alert")
def send_alert(incident_id: int) -> str:
    db = _get_db()
    try:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return f"Incident {incident_id} not found"

        message = "\n".join(
            [
                "[DotasPlus] New CTI incident",
                f"ID: {incident.id}",
                f"Title: {incident.title}",
                f"Severity: {incident.severity}/5",
                f"Source: {incident.source_type}",
            ]
        )
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            response = requests.post(
                url,
                json={"chat_id": settings.TELEGRAM_CHAT_ID, "text": message},
                timeout=10,
            )
            response.raise_for_status()
            return f"Alert sent for incident_id={incident.id}"

        print(message)
        return f"Alert logged for incident_id={incident.id}"
    finally:
        db.close()
