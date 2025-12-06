from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Source
from app.tasks import crawl_source

router = APIRouter(prefix="/api/v1/sources", tags=["Sources"])

# -------------------------------
# Pydantic Schemas
# -------------------------------
class SourceCreate(BaseModel):
    name: str
    type: str          # "darkweb", "osint", "leak_site" 등
    url: str
    use_tor: bool = False   # 기본값 False (일반 웹)


class SourceRead(BaseModel):
    id: int
    name: str
    type: str
    url: str
    use_tor: bool

    class Config:
        from_attributes = True   # pydantic v2 (v1이라면 orm_mode = True)


# -------------------------------
# Create Source
# -------------------------------
@router.post(
    "/", 
    summary="Register new source", 
    response_model=SourceRead
)
def create_source(
    src: SourceCreate,
    db: Session = Depends(get_db),
):
    new_src = Source(
        name=src.name,
        type=src.type,
        url=src.url,
        use_tor=src.use_tor,
    )
    db.add(new_src)
    db.commit()
    db.refresh(new_src)
    return new_src


# -------------------------------
# List Sources
# -------------------------------
@router.get(
    "/", 
    summary="List Sources", 
    response_model=list[SourceRead]
)
def list_sources(
    db: Session = Depends(get_db),
):
    return db.query(Source).all()


# -------------------------------
# Trigger Crawl
# -------------------------------
@router.post("/{source_id}/run_crawl", summary="Start crawling this source (async)")
def run_crawl(
    source_id: int,
    db: Session = Depends(get_db),
):
    src = db.query(Source).filter(Source.id == source_id).first()
    if not src:
        raise HTTPException(404, "Source not found")

    # Celery async task 실행
    task = crawl_source.delay(source_id)

    return {
        "message": "Crawl task accepted",
        "task_id": task.id,
    }
