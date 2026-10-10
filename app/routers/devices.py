"""Device registration and catch-up feed."""
from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Device, Version

router = APIRouter(prefix="/devices", tags=["devices"])


class DeviceRegisterIn(BaseModel):
    device_id: str


class DeviceRegisterOut(BaseModel):
    device_id: str
    registered_at: datetime


class DeviceChange(BaseModel):
    document_id: int
    version: int
    outcome: str
    created_at: datetime


@router.post("/register", response_model=DeviceRegisterOut)
def register_device(body: DeviceRegisterIn, db: Session = Depends(get_db)):
    dev = db.query(Device).filter_by(device_id=body.device_id).first()
    if not dev:
        dev = Device(device_id=body.device_id)
        db.add(dev)
        db.commit()
        db.refresh(dev)
    return DeviceRegisterOut(device_id=dev.device_id, registered_at=dev.registered_at)


@router.get("", response_model=list[DeviceRegisterOut])
def list_devices(db: Session = Depends(get_db)):
    devs = db.query(Device).order_by(Device.registered_at.desc()).all()
    return [DeviceRegisterOut(device_id=d.device_id, registered_at=d.registered_at) for d in devs]


@router.get("/{device_id}/changes", response_model=list[DeviceChange])
def get_device_changes(device_id: str, since_version: int = 0, db: Session = Depends(get_db)):
    versions = (
        db.query(Version)
        .filter(Version.version > since_version)
        .order_by(Version.version.asc())
        .limit(100)
        .all()
    )
    return [
        DeviceChange(
            document_id=v.document_id,
            version=v.version,
            outcome=v.outcome,
            created_at=v.created_at,
        )
        for v in versions
    ]
