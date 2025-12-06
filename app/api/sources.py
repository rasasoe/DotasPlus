from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Source
from app.tasks import crawl_source

router = APIRouter(prefix="/api/v1/sources", tags=["Sources"])

# -------------------------------
# Pydantic Schema
# -------------------------------
class SourceCreate(BaseModel):
    name: str
    type: str  # darkweb, osint, leak_site 등
    url: str

# -------------------------------
# Create Source
# -------------------------------
@router.post("/", summary="Register new source")
def create_source(src: SourceCreate, db: Session = next(get_db())):
    new_src = Source(
        name=src.name,
        type=src.type,
        url=src.url
    )
    db.add(new_src)
    db.commit()
    db.refresh(new_src)
    return new_src

# -------------------------------
# Trigger Crawl
# -------------------------------
@router.post("/{source_id}/run_crawl", summary="Start crawling this source (async)")
def run_crawl(source_id: int, db: Session = next(get_db())):
    src = db.query(Source).filter(Source.id == source_id).first()
    if not src:
        raise HTTPException(404, "Source not found")

    # Celery async task 실행
    task = crawl_source.delay(source_id)

    return {
        "message": "Crawl task accepted",
        "task_id": task.id
    }
