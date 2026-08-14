from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class ConstantesVitales(Base):
    __tablename__ = "constantes_vitales"

    constante_id = Column(Integer, primary_key=True, autoincrement=True)
    sejour_id = Column(Integer, ForeignKey("sejour.sejour_id"), nullable=False)
    prise_par_id = Column(Integer, ForeignKey("personnel.personnel_id"), nullable=True)
    heure_prise = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Vitals
    temperature = Column(Float, nullable=True)
    fc = Column(Integer, nullable=True)  # heart rate
    ta_systolique = Column(Integer, nullable=True)
    ta_diastolique = Column(Integer, nullable=True)
    spo2 = Column(Integer, nullable=True)
    douleur = Column(Integer, nullable=True)  # EVA 0-10
    glasgow = Column(Integer, nullable=True)  # 3-15
    frequence_respiratoire = Column(Integer, nullable=True)
    rythme_cardiaque = Column(String(50), nullable=True)
    risk_level = Column(String(20), nullable=True)
    risk_confidence = Column(Float, nullable=True)

    # Relationships
    sejour = relationship("Sejour", back_populates="constantes_vitales")