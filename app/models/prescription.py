from datetime import datetime, timezone
from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, Boolean, Text
from sqlalchemy.orm import relationship
from app.models.base import Base


class Prescription(Base):
    __tablename__ = "prescription"
    presc_id = Column(Integer, primary_key=True, autoincrement=True)
    sejour_id = Column(Integer, ForeignKey("sejour.sejour_id"))
    prescripteur_id = Column(Integer, ForeignKey("personnel.personnel_id"))
    medicament = Column(String(100))
    dose = Column(String(50))
    heure_prescription = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    annule = Column(Boolean, default=False)
    annulant_id = Column(Integer, ForeignKey("personnel.personnel_id"), nullable=True)
    heure_annulation = Column(DateTime, nullable=True)
    motif_annulation = Column(Text, nullable=True)
    sejour = relationship("Sejour", back_populates="prescriptions")
