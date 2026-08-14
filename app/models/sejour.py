from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from app.models.base import Base


class Sejour(Base):
    __tablename__ = "sejour"
    sejour_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patient.patient_id"))
    mode_arrivee = Column(String(50))
    date_arrivee = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    date_sortie = Column(DateTime, nullable=True)
    motif_visite = Column(Text)
    diagnostic_sortie = Column(String(255), nullable=True)
    mode_sortie = Column(String(50), nullable=True)
    courrier_sortie = Column(Text, nullable=True)
    statut = Column(String(50), default="En attente de triage")
    priorite_initiale = Column(String(50), nullable=True)
    patient = relationship("Patient", back_populates="sejours")
    triages = relationship("TriageRecord", back_populates="sejour")
    examens = relationship("Examen", back_populates="sejour")
    affectations_lit = relationship("AffectationLit", back_populates="sejour")
    observations = relationship("Observation", back_populates="sejour")
    prescriptions = relationship("Prescription", back_populates="sejour")
    constantes_vitales = relationship("ConstantesVitales", back_populates="sejour", cascade="all, delete-orphan")


# Lazy import to avoid circular dependency
def _init_relationships():
    from app.models.constantes_vitales import ConstantesVitales
    ConstantesVitales.sejour = relationship("Sejour", back_populates="constantes_vitales")


_init_relationships()
