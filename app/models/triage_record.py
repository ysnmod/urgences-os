from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class TriageRecord(Base):
    __tablename__ = "triage"
    triage_id = Column(Integer, primary_key=True, autoincrement=True)
    sejour_id = Column(Integer, ForeignKey("sejour.sejour_id"))
    soignant_id = Column(Integer, ForeignKey("personnel.personnel_id"))
    heure_triage = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    score_ccmu = Column(Integer)
    score_french = Column(Integer)
    poids = Column(Float)
    temperature = Column(Float)
    fc = Column(Integer)
    ta_systolique = Column(Integer)
    ta_diastolique = Column(Integer)
    spo2 = Column(Float)
    glasgow = Column(Integer)
    glasgow_e = Column(Integer, nullable=True)  # Yeux
    glasgow_v = Column(Integer, nullable=True)  # Verbal
    glasgow_m = Column(Integer, nullable=True)  # Moteur
    douleur = Column(Integer)
    notes = Column(Text)
    zone = Column(String(50), nullable=True)
    sejour = relationship("Sejour", back_populates="triages")
