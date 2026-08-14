from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class Lit(Base):
    __tablename__ = "lit"
    lit_id = Column(Integer, primary_key=True, autoincrement=True)
    numero_lit = Column(String(10))
    salle_id = Column(Integer, ForeignKey("salle.salle_id"))
    type_lit = Column(String(30))
    statut = Column(String(20), default="libre")
    salle = relationship("Salle", back_populates="lits")
    affectations = relationship("AffectationLit", back_populates="lit")
