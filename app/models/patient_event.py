from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class PatientEvent(Base):
    """Event sourcing - historique des événements patient"""

    __tablename__ = "patient_event"
    event_id = Column(Integer, primary_key=True, autoincrement=True)
    sejour_id = Column(Integer, ForeignKey("sejour.sejour_id"), nullable=False)
    event_type = Column(
        String(50), nullable=False
    )  # ARRIVEE, TRIAGE, RETRIAGE, EXAMEN_PRESCRIT, EXAMEN_RESULTAT, PRESCRIPTION, LIT_AFFECTE, SORTIE, etc.
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    personnel_id = Column(Integer, ForeignKey("personnel.personnel_id"), nullable=True)
    data_json = Column(Text, nullable=True)
    description = Column(String(255), nullable=True)


# Event types constants
EVENT_TYPES = {
    "ARRIVEE": "Patient arrivé aux urgences",
    "TRIAGE": "Triage effectué",
    "RETRIAGE": "Re-triage effectué",
    "EXAMEN_PRESCRIT": "Examen prescrit",
    "EXAMEN_RESULTAT": "Résultat examen reçu",
    "PRESCRIPTION": "Prescription créée",
    "LIT_AFFECTE": "Lit affecté",
    "LIT_TRANSFERE": "Transfert de lit",
    "SORTIE": "Patient sorti",
    "OBSERVATION": "Observation ajoutée",
    "ALERTE": "Alerte déclenchée",
}


def log_patient_event(
    db,
    sejour_id: int,
    event_type: str,
    personnel_id: int = None,
    data: dict = None,
    description: str = None,
):
    """Log un événement patient"""
    import json

    event = PatientEvent(
        sejour_id=sejour_id,
        event_type=event_type,
        personnel_id=personnel_id,
        data_json=json.dumps(data, default=str) if data else None,
        description=description or EVENT_TYPES.get(event_type, event_type),
    )
    db.add(event)
    return event
