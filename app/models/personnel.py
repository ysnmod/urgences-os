from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.models.base import Base


class Personnel(Base):
    __tablename__ = "personnel"
    personnel_id = Column(Integer, primary_key=True, autoincrement=True)
    nom = Column(String(100))
    prenom = Column(String(100))
    login = Column(String(50), unique=True)
    mot_de_passe = Column(String(255))
    mot_de_passe_plain = Column(String(255))
    role = Column(String(50))
    actif = Column(Boolean, default=True)
    session_tokens = relationship("SessionToken")
