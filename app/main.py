from fastapi import FastAPI

from app.api import assets, incidents, sources, tasks
from app.config import settings
from app.database import Base, engine


app = FastAPI(title=settings.PROJECT_NAME, version="0.2.0")
app.include_router(assets.router, prefix=settings.API_V1_PREFIX)
app.include_router(sources.router, prefix=settings.API_V1_PREFIX)
app.include_router(incidents.router, prefix=settings.API_V1_PREFIX)
app.include_router(tasks.router, prefix=settings.API_V1_PREFIX)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check():
    return {"status": "ok"}
