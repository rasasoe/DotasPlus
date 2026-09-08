from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Asset


router = APIRouter(prefix="/assets", tags=["assets"])


class AssetCreate(BaseModel):
    name: str
    identifier: str
    asset_type: str
    criticality: int = Field(default=3, ge=1, le=5)


class AssetRead(AssetCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate, db: Session = Depends(get_db)):
    asset = Asset(
        name=payload.name.strip(),
        identifier=payload.identifier.strip().lower(),
        asset_type=payload.asset_type.strip().lower(),
        criticality=payload.criticality,
    )
    db.add(asset)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Asset already registered")
    db.refresh(asset)
    return asset


@router.get("", response_model=list[AssetRead])
def list_assets(db: Session = Depends(get_db)):
    return db.query(Asset).order_by(Asset.id).all()
