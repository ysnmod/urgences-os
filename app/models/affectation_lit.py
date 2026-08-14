from datetime import datetime, timezone
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.models.base import Base


class AffectationLit(Base):
    __tablename__ = "affectation_lit"
    affectation_id = Column(Integer, primary_key=True, autoincrement=True)
    sejour_id = Column(Integer, ForeignKey("sejour.sejour_id"))
    lit_id = Column(Integer, ForeignKey("lit.lit_id"))
    heure_debut = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    heure_fin = Column(DateTime, nullable=True)
    sejour = relationship("Sejour", back_populates="affectations_lit")
    lit = relationship("Lit", back_populates="affectations")
