from datetime import datetime, timezone
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.models.base import Base


class Observation(Base):
    __tablename__ = "observation"
    obs_id = Column(Integer, primary_key=True, autoincrement=True)
    sejour_id = Column(Integer, ForeignKey("sejour.sejour_id"))
    auteur_id = Column(Integer, ForeignKey("personnel.personnel_id"))
    texte = Column(Text)
    date_obs = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    sejour = relationship("Sejour", back_populates="observations")
