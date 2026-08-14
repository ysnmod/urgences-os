from datetime import datetime, timezone
from sqlalchemy import Column, Integer, DateTime, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Session
from app.models.base import Base
import json
from typing import Optional


class AuditLog(Base):
    __tablename__ = "audit_log"
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    personnel_id = Column(Integer, ForeignKey("personnel.personnel_id"), nullable=True)
    action = Column(String(100), nullable=False)
    entite = Column(String(50), nullable=True)
    entite_id = Column(Integer, nullable=True)
    detail = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)


def log_action(
    db: Session,
    action: str,
    personnel_id: Optional[int] = None,
    entite: Optional[str] = None,
    entite_id: Optional[int] = None,
    detail: Optional[dict] = None,
    ip_address: Optional[str] = None,
):
    log = AuditLog(
        personnel_id=personnel_id,
        action=action,
        entite=entite,
        entite_id=entite_id,
        detail=json.dumps(detail, default=str) if detail else None,
        ip_address=ip_address,
    )
    db.add(log)
