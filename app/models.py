"""SQLAlchemy models for SyncLab."""
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from .db import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    collection = Column(String(64), default="default", index=True)
    title = Column(String(255), default="")
    body = Column(Text, default="")
    tags_json = Column(Text, default="[]")
    meta_json = Column(Text, default="{}")
    version = Column(Integer, default=1, index=True)
    deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Version(Base):
    __tablename__ = "versions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, index=True)
    version = Column(Integer, index=True)
    title = Column(String(255), default="")
    body = Column(Text, default="")
    tags_json = Column(Text, default="[]")
    meta_json = Column(Text, default="{}")
    deleted = Column(Boolean, default=False)
    device_id = Column(String(128), default="")
    strategy = Column(String(64), default="")
    outcome = Column(String(64), default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class AppliedOp(Base):
    __tablename__ = "applied_ops"

    id = Column(Integer, primary_key=True, index=True)
    op_id = Column(String(128), unique=True, index=True)
    result_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(128), unique=True, index=True)
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_seen_seq = Column(Integer, default=0)
