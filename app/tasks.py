import re
import requests
from celery import shared_task
from sqlalchemy.orm import Session

from app.celery_app import celery_app  # noqa: F401
from app.database import SessionLocal
from app.models import Source, RawDocument, Asset, Incident
from app.config import settings


URL_REGEX = re.compile(r"https?://[^\s\"']+")
IP_REGEX = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _get_db() -> Session:
    return SessionLocal()


@shared_task(name="app.tasks.crawl_source")
def crawl_source(source_id: int) -> str:
    db = _get_db()
    try:
        src: Source | None = db.query(Source).filter(Source.id == source_id).first()
        if not src:
            return f"Source {source_id} not found"

        resp = requests.get(src.url, timeout=10)
        resp.raise_for_status()

        raw = RawDocument(
            source_id=src.id,
            url=src.url,
            body_raw=resp.text,
            status="fetched",
            metadata={"http_status": resp.status_code},
        )
        db.add(raw)
        db.commit()
        db.refresh(raw)

        normalize_document.delay(raw.id)
        return f"Fetched {src.url} → raw_document_id={raw.id}"
    except Exception as e:
        db.rollback()
        return f"Error in crawl_source({source_id}): {e}"
    finally:
        db.close()


@shared_task(name="app.tasks.normalize_document")
def normalize_document(raw_document_id: int) -> str:
    db = _get_db()
    try:
        doc: RawDocument | None = (
            db.query(RawDocument).filter(RawDocument.id == raw_document_id).first()
        )
        if not doc:
            return f"RawDocument {raw_document_id} not found"

        html = doc.body_raw or ""
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()

        urls = URL_REGEX.findall(text)
        ips = IP_REGEX.findall(text)
        emails = EMAIL_REGEX.findall(text)

        doc.body_text = text
        doc.status = "normalized"
        meta = doc.metadata or {}
        meta["ioc_candidates"] = {
            "urls": urls,
            "ips": ips,
            "emails": emails,
        }
        doc.metadata = meta

        db.commit()

        match_incident.delay(raw_document_id)
        return (
            f"Normalized raw_document_id={raw_document_id} "
            f"(urls={len(urls)}, ips={len(ips)}, emails={len(emails)})"
        )
    except Exception as e:
        db.rollback()
        return f"Error in normalize_document({raw_document_id}): {e}"
    finally:
        db.close()


def _find_matching_assets(db: Session, doc: RawDocument):
    text = (doc.body_text or "").lower()
    meta = doc.metadata or {}
    candidates = meta.get("ioc_candidates", {}) or {}
    urls = [u.lower() for u in candidates.get("urls", [])]
    emails = [e.lower() for e in candidates.get("emails", [])]
    ips = [ip.lower() for ip in candidates.get("ips", [])]

    all_strings = [text] + urls + emails + ips

    assets = db.query(Asset).all()
    matches: list[dict] = []

    for asset in assets:
        ident = (asset.identifier or "").lower()
        if not ident:
            continue
        if any(ident in s for s in all_strings):
            matches.append(
                {
                    "asset_id": asset.id,
                    "name": asset.name,
                    "type": asset.type,
                    "identifier": asset.identifier,
                    "criticality": asset.criticality,
                }
            )

    return matches


@shared_task(name="app.tasks.match_incident")
def match_incident(raw_document_id: int) -> str:
    db = _get_db()
    try:
        doc: RawDocument | None = (
            db.query(RawDocument).filter(RawDocument.id == raw_document_id).first()
        )
        if not doc:
            return f"RawDocument {raw_document_id} not found"

        matches = _find_matching_assets(db, doc)
        if not matches:
            return f"No matching assets for raw_document_id={raw_document_id}"

        max_crit = max(m["criticality"] for m in matches)
        asset_names = ", ".join({m["name"] for m in matches})

        title = f"[AUTO] Possible leak related to: {asset_names}"
        description = (
            f"Raw document (id={doc.id}) from source_id={doc.source_id} "
            f"contains indicators mentioning registered assets."
        )

        incident = Incident(
            title=title,
            description=description,
            severity=max_crit,
            source_type="osint",
            extra={
                "raw_document_id": doc.id,
                "matched_assets": matches,
                "url": doc.url,
            },
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)

        send_alert.delay(incident.id)
        return f"Incident {incident.id} created from raw_document_id={raw_document_id}"
    except Exception as e:
        db.rollback()
        return f"Error in match_incident({raw_document_id}): {e}"
    finally:
        db.close()


@shared_task(name="app.tasks.send_alert")
def send_alert(incident_id: int) -> str:
    db = _get_db()
    try:
        incident: Incident | None = (
            db.query(Incident).filter(Incident.id == incident_id).first()
        )
        if not incident:
            return f"Incident {incident_id} not found"

        title = incident.title
        sev = incident.severity
        src_type = incident.source_type
        extra = incident.extra or {}

        msg_lines = [
            "🚨 [DOTAS++ Lite] New Incident Detected",
            "",
            f"ID: {incident.id}",
            f"Title: {title}",
            f"Severity: {sev}",
            f"Source: {src_type}",
        ]
        if "url" in extra:
            msg_lines.append(f"Source URL: {extra['url']}")
        if "matched_assets" in extra:
            assets_str = ", ".join(
                f"{a['name']}({a['identifier']})"
                for a in extra["matched_assets"]
            )
            msg_lines.append(f"Assets: {assets_str}")

        message = "\n".join(msg_lines)

        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            try:
                api_url = (
                    f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
                )
                payload = {
                    "chat_id": settings.TELEGRAM_CHAT_ID,
                    "text": message,
                }
                resp = requests.post(api_url, json=payload, timeout=10)
                resp.raise_for_status()
                return f"Alert sent to Telegram for incident_id={incident_id}"
            except Exception as e:
                print(f"[ALERT][FALLBACK] {message}")
                return f"Telegram error for incident_id={incident_id}: {e}"
        else:
            print(f"[ALERT] {message}")
            return f"Alert logged to console for incident_id={incident_id}"
    finally:
        db.close()
