from sqlalchemy import Column, Integer, String, Text
from app.models.base import Base


class Interaction(Base):
    __tablename__ = "interaction"

    id = Column(Integer, primary_key=True, autoincrement=True)
    drug_a = Column(String(300), index=True, nullable=False)
    drug_b = Column(String(300), index=True, nullable=False)
    niveau = Column(String(20), nullable=False)  # mineur, modéré, sévère, contre-indication
    description = Column(Text, default="")
