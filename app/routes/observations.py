from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import Observation, Sejour, Personnel, log_patient_event
from app.utils.db_utils import get_db
from app.dependencies import require_roles
from datetime import datetime, timezone

router = APIRouter()


@router.post("/observations/")
async def create_observation(
    observation_data: dict,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "medecin", "infirmier")),
):
    new_observation = Observation(
        sejour_id=observation_data["sejour_id"],
        auteur_id=observation_data["auteur_id"],
        texte=observation_data["texte"],
        date_obs=datetime.now(timezone.utc),
    )

    db.add(new_observation)
    from app.models import log_action

    log_action(
        db,
        "OBSERVATION",
        personnel_id=current_user.personnel_id,
        entite="observation",
        entite_id=None,
        detail={"sejour_id": observation_data["sejour_id"]},
    )
    
    # Event sourcing
    log_patient_event(
        db,
        sejour_id=observation_data["sejour_id"],
        event_type="OBSERVATION",
        personnel_id=current_user.personnel_id,
        data={"texte": observation_data["texte"][:100]},
    )
    
    db.commit()
    db.refresh(new_observation)
    
    # Broadcast to WebSocket clients
    from app.websocket import manager
    await manager.broadcast_event(
        "OBSERVATION",
        observation_data["sejour_id"],
        {
            "auteur_id": observation_data["auteur_id"],
            "texte": observation_data["texte"][:50],  # Extrait
        },
    )

    return {
        "message": "Observation ajoutée avec succès",
        "obs_id": new_observation.obs_id,
    }
