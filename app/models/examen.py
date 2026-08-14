from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from app.models.base import Base


class Examen(Base):
    __tablename__ = "examen"
    examen_id = Column(Integer, primary_key=True, autoincrement=True)
    sejour_id = Column(Integer, ForeignKey("sejour.sejour_id"))
    prescripteur_id = Column(Integer, ForeignKey("personnel.personnel_id"))
    type_examen = Column(String(100))
    heure_prescription = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    heure_resultat = Column(DateTime, nullable=True)
    resultat = Column(Text, nullable=True)
    statut = Column(
        String(20), default="réalisé"
    )  # modifié: "réalisé" par défaut, au lieu de "demande"
    sejour = relationship("Sejour", back_populates="examens")
