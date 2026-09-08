from __future__ import annotations

import hashlib

from sqlalchemy.orm import Session

from app.intelligence import ioc_matches_asset
from app.models import Asset, IOC, Incident, RawDocument


def persist_iocs(
    db: Session, document: RawDocument, indicators: list[dict[str, str]]
) -> list[IOC]:
    existing = {
        (ioc.ioc_type, ioc.normalized_value)
        for ioc in db.query(IOC).filter(IOC.raw_document_id == document.id).all()
    }
    created: list[IOC] = []
    for item in indicators:
        key = (item["ioc_type"], item["normalized_value"])
        if key in existing:
            continue
        ioc = IOC(raw_document_id=document.id, **item)
        db.add(ioc)
        created.append(ioc)
        existing.add(key)
    db.flush()
    return created


def create_incidents(db: Session, document: RawDocument) -> list[Incident]:
    assets = db.query(Asset).filter(Asset.is_active.is_(True)).all()
    iocs = db.query(IOC).filter(IOC.raw_document_id == document.id).all()
    created: list[Incident] = []

    for asset in assets:
        for ioc in iocs:
            if not ioc_matches_asset(
                ioc.ioc_type,
                ioc.normalized_value,
                asset.asset_type,
                asset.identifier,
                document.body_text or "",
            ):
                continue

            identity = f"v1:{asset.id}:{ioc.ioc_type}:{ioc.normalized_value}"
            dedup_key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
            exists = db.query(Incident).filter(Incident.dedup_key == dedup_key).first()
            if exists:
                continue

            source_type = document.source.source_type if document.source else "osint"
            incident = Incident(
                ioc_id=ioc.id,
                asset_id=asset.id,
                raw_document_id=document.id,
                dedup_key=dedup_key,
                title=f"Indicator matched protected asset: {asset.name}",
                description=(
                    f"{ioc.ioc_type} indicator {ioc.normalized_value!r} from "
                    f"source {source_type!r} matched asset {asset.identifier!r}."
                ),
                severity=max(1, min(5, int(asset.criticality))),
                source_type=source_type,
                extra={
                    "source_url": document.url,
                    "ioc_type": ioc.ioc_type,
                    "ioc_value": ioc.normalized_value,
                    "asset_type": asset.asset_type,
                    "asset_identifier": asset.identifier,
                },
            )
            db.add(incident)
            db.flush()
            created.append(incident)

    return created
