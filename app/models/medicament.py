from sqlalchemy import Column, Integer, String
from app.models.base import Base


class Medicament(Base):
    __tablename__ = "medicament"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cis_code = Column(String(20), unique=True, index=True)
    nom = Column(String(300), index=True)
    forme = Column(String(100))
    voie_administration = Column(String(100))
    statut_amm = Column(String(50))
    etat_commercialisation = Column(String(50))
    titulaire = Column(String(200))
    surveillance_renforcee = Column(String(10))
    substance = Column(String(300), index=True)
