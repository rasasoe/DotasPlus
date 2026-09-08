from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Source
from app.tasks import crawl_source


router = APIRouter(prefix="/sources", tags=["sources"])


class SourceCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    source_type: str = Field(alias="type")
    url: str
    use_tor: bool = False

class SourceRead(SourceCreate):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    is_active: bool


@router.post("", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_source(src: SourceCreate, db: Session = Depends(get_db)):
    source = Source(
        name=src.name.strip(),
        source_type=src.source_type.strip().lower(),
        url=src.url.strip(),
        use_tor=src.use_tor,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.get("", response_model=list[SourceRead])
def list_sources(db: Session = Depends(get_db)):
    return db.query(Source).order_by(Source.id).all()


@router.post("/{source_id}/crawl", status_code=status.HTTP_202_ACCEPTED)
def run_crawl(source_id: int, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if not source.is_active:
        raise HTTPException(status_code=409, detail="Source is inactive")
    task = crawl_source.delay(source_id)
    return {"source_id": source_id, "task_id": task.id, "status": "scheduled"}
