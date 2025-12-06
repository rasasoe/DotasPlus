from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.config import settings
from app.database import Base, engine, get_db
from app.models import Source
from app.tasks import crawl_source
from pydantic import BaseModel

app = FastAPI(title=settings.PROJECT_NAME)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check():
    return {"status": "ok"}


class SourceCreate(BaseModel):
    name: str
    type: str
    url: str
    use_tor: bool = False


class SourceRead(SourceCreate):
    id: int

    class Config:
        orm_mode = True


@app.post(f"{settings.API_V1_PREFIX}/sources", response_model=SourceRead)
def create_source(src: SourceCreate, db: Session = Depends(get_db)):
    obj = Source(
        name=src.name,
        type=src.type,
        url=src.url,
        use_tor=src.use_tor,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.get(f"{settings.API_V1_PREFIX}/sources", response_model=List[SourceRead])
def list_sources(db: Session = Depends(get_db)):
    return db.query(Source).all()


@app.post(f"{settings.API_V1_PREFIX}/sources/{{source_id}}/run_crawl", status_code=202)
def run_crawl(source_id: int, db: Session = Depends(get_db)):
    src = db.query(Source).filter(Source.id == source_id).first()
    if not src:
        raise HTTPException(status_code=404, detail="Source not found")

    async_result = crawl_source.delay(source_id)
    return {
        "data": {
            "message": "Crawl task scheduled",
            "source_id": source_id,
            "task_id": async_result.id,
        }
    }
