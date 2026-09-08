from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.findings import build_findings_export
from app.models import Incident


router = APIRouter(prefix="/incidents", tags=["incidents"])


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    ioc_id: int
    raw_document_id: int
    title: str
    description: str
    severity: int
    source_type: str
    status: str
    extra: dict | None

@router.get("", response_model=list[IncidentRead])
def list_incidents(db: Session = Depends(get_db)):
    return db.query(Incident).order_by(Incident.id.desc()).limit(100).all()


@router.get("/findings")
def export_findings(db: Session = Depends(get_db)):
    incidents = db.query(Incident).order_by(Incident.id).all()
    return build_findings_export(incidents)
