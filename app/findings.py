from __future__ import annotations

from datetime import datetime, timezone

from app.models import Incident


SCHEMA_VERSION = "1.0"
SEVERITY = {1: "info", 2: "low", 3: "medium", 4: "high", 5: "critical"}


def build_findings_export(
    incidents: list[Incident], generated_at: str | None = None
) -> dict:
    timestamp = generated_at or datetime.now(timezone.utc).isoformat()
    findings = []
    for incident in incidents:
        confidence = 0.9 if incident.asset.asset_type != "keyword" else 0.6
        findings.append(
            {
                "source": "DotasPlus",
                "asset": {
                    "type": incident.asset.asset_type,
                    "value": incident.asset.identifier,
                    "name": incident.asset.name,
                },
                "finding_type": "threat_intelligence.asset_indicator_match",
                "title": incident.title,
                "severity": SEVERITY.get(incident.severity, "medium"),
                "score": incident.severity * 20,
                "confidence": confidence,
                "confidence_basis": (
                    "normalized indicator match"
                    if confidence == 0.9
                    else "keyword occurrence"
                ),
                "evidence": {
                    "incident_id": incident.id,
                    "raw_document_id": incident.raw_document_id,
                    **(incident.extra or {}),
                },
                "references": [incident.raw_document.url],
                "detected_at": incident.created_at.isoformat(),
            }
        )
    return {"schema_version": SCHEMA_VERSION, "generated_at": timestamp, "findings": findings}
