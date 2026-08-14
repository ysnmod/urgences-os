from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models import Sejour, TriageRecord, Personnel
from app.utils.db_utils import get_db
from app.dependencies import require_roles
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/alertes/")
async def get_alertes(
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "medecin", "infirmier")),
):
    alertes = []

    # Alerte: patients en attente de triage depuis plus de 30min qui n'ont JAMAIS été triés
    il_y_a_30min = datetime.now() - timedelta(minutes=30)

    sejours_en_attente = (
        db.query(Sejour)
        .filter(
            Sejour.statut == "En attente de triage", Sejour.date_arrivee < il_y_a_30min
        )
        .all()
    )

    for s in sejours_en_attente:
        triage_existant = (
            db.query(TriageRecord).filter(TriageRecord.sejour_id == s.sejour_id).first()
        )
        if triage_existant:
            continue

        attente_minutes = (datetime.now() - s.date_arrivee).total_seconds() / 60
        alertes.append(
            {
                "message": f"Patient {s.patient.nom} {s.patient.prenom} en attente de triage depuis {int(attente_minutes)} minutes",
                "type": "attente_triage",
                "sejour_id": s.sejour_id,
            }
        )

    return alertes
