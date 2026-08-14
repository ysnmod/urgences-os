from sqlalchemy import Column, Integer, String, Date, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from app.models.base import Base


class Patient(Base):
    __tablename__ = "patient"
    patient_id = Column(Integer, primary_key=True, autoincrement=True)
    nom = Column(String(100), index=True)
    prenom = Column(String(100))
    date_naissance = Column(Date)
    sexe = Column(String(1))
    adresse = Column(String(255))
    telephone = Column(String(20))
    numero_secu = Column(String(20), unique=True, index=True)
    groupe_sanguin = Column(String(5))
    allergies = Column(Text)
    medecin_traitant = Column(String(150))
    sejours = relationship("Sejour", back_populates="patient")
