from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import Prescription, Sejour, Personnel, log_action, log_patient_event
from app.schemas import PrescriptionCreate
from app.utils.db_utils import get_db
from app.dependencies import require_roles
from app.websocket import manager
from datetime import datetime, timezone

router = APIRouter()


@router.post("/prescriptions/")
async def create_prescription(
    prescription_in: PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "medecin")),
):
    sejour = (
        db.query(Sejour).filter(Sejour.sejour_id == prescription_in.sejour_id).first()
    )
    if not sejour:
        raise HTTPException(status_code=404, detail="Sejour introuvable")

    prescription = Prescription(
        sejour_id=prescription_in.sejour_id,
        prescripteur_id=current_user.personnel_id,
        medicament=prescription_in.medicament,
        dose=prescription_in.dose,
    )
    db.add(prescription)

    log_action(
        db,
        "PRESCRIPTION",
        personnel_id=current_user.personnel_id,
        entite="prescription",
        entite_id=None,
        detail={"medicament": prescription_in.medicament, "dose": prescription_in.dose},
    )

    # Event sourcing
    log_patient_event(
        db,
        sejour_id=sejour.sejour_id,
        event_type="PRESCRIPTION",
        personnel_id=current_user.personnel_id,
        data={"medicament": prescription_in.medicament, "dose": prescription_in.dose},
    )

    db.commit()

    # Broadcast
    await manager.broadcast_event(
        "PRESCRIPTION",
        sejour.sejour_id,
        {
            "medicament": prescription_in.medicament,
            "dose": prescription_in.dose,
        },
    )

    return {"message": "Prescription créée avec succès"}


@router.delete("/prescriptions/{presc_id}")
async def supprimer_prescription(
    presc_id: int,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "medecin")),
):
    prescription = (
        db.query(Prescription).filter(Prescription.presc_id == presc_id).first()
    )
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription introuvable")

    log_action(
        db,
        "SUPPRESSION_PRESCRIPTION",
        personnel_id=current_user.personnel_id,
        entite="prescription",
        entite_id=presc_id,
        detail={"medicament": prescription.medicament},
    )

    db.delete(prescription)
    db.commit()

    await manager.broadcast_event(
        "PRESCRIPTION",
        prescription.sejour_id,
        {"medicament": prescription.medicament, "action": "supprimee"},
    )

    return {"message": "Prescription supprimée"}


@router.put("/prescriptions/{presc_id}/annuler")
async def annuler_prescription(
    presc_id: int,
    motif: str = "Non specifie",
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "medecin")),
):
    prescription = (
        db.query(Prescription).filter(Prescription.presc_id == presc_id).first()
    )
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription introuvable")

    if prescription.annule:
        return {"message": "Déjà annulée"}

    prescription.annule = True
    prescription.heure_annulation = datetime.now(timezone.utc)
    prescription.annulant_id = current_user.personnel_id
    prescription.motif_annulation = motif

    from app.models import log_action

    log_action(
        db,
        "ANNULATION_PRESCRIPTION",
        personnel_id=current_user.personnel_id,
        entite="prescription",
        entite_id=presc_id,
        detail={"motif": motif},
    )
    db.commit()
    return {"message": "Prescription annulée"}
