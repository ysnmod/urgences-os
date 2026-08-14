from sqlalchemy import Column, Integer, String
from app.models.base import Base


class TypeExamen(Base):
    __tablename__ = "type_examen"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nom = Column(String(100), unique=True, index=True)
    categorie = Column(String(50))
