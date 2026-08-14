from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class SessionToken(Base):
    __tablename__ = "session_token"
    token_id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(128), unique=True, index=True, nullable=False)
    personnel_id = Column(Integer, ForeignKey("personnel.personnel_id"), nullable=False)
    cree_le = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expire_le = Column(DateTime, nullable=False)
    actif = Column(Boolean, default=True)
    personnel = relationship("Personnel", overlaps="session_tokens")
