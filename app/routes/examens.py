from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import Examen, Sejour, Personnel, log_patient_event
from app.utils.db_utils import get_db
from app.dependencies import require_roles
from datetime import datetime, timezone

router = APIRouter()


@router.post("/examens/")
async def create_examen(
    examen_data: dict,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "medecin")),
):
    new_examen = Examen(
        sejour_id=examen_data["sejour_id"],
        prescripteur_id=examen_data["prescripteur_id"],
        type_examen=examen_data["type_examen"],
        statut=examen_data.get(
            "statut", "réalisé"
        ),  # Use passed status or default to "réalisé"
        heure_prescription=datetime.now(timezone.utc),
    )

    db.add(new_examen)
    from app.models import log_action

    log_action(
        db,
        "EXAMEN",
        personnel_id=current_user.personnel_id,
        entite="examen",
        entite_id=None,
        detail={
            "type": examen_data["type_examen"],
            "sejour_id": examen_data["sejour_id"],
        },
    )
    
    # Event sourcing
    log_patient_event(
        db,
        sejour_id=examen_data["sejour_id"],
        event_type="EXAMEN_PRESCRIT",
        personnel_id=current_user.personnel_id,
        data={"type_examen": examen_data["type_examen"]},
    )
    
    db.commit()
    db.refresh(new_examen)
    
    # Broadcast to WebSocket clients
    from app.websocket import manager
    await manager.broadcast_event(
        "EXAMEN",
        examen_data["sejour_id"],
        {
            "type_examen": examen_data["type_examen"],
            "prescripteur_id": examen_data["prescripteur_id"],
        },
    )

    return {"message": "Examen prescrit avec succès", "examen_id": new_examen.examen_id}
