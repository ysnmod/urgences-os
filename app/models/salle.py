from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class Salle(Base):
    __tablename__ = "salle"
    salle_id = Column(Integer, primary_key=True, autoincrement=True)
    nom_salle = Column(String(50))
    zone = Column(String(30))
    specialite = Column(String(30))
    capacite = Column(Integer)
    lits = relationship("Lit", back_populates="salle")
