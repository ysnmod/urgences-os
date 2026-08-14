from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import Sejour, TriageRecord, ConstantesVitales, log_action, Personnel, log_patient_event
from app.schemas import TriageCreate
from app.utils.db_utils import get_db
from app.dependencies import require_roles
from app.websocket import manager

router = APIRouter()


@router.post("/triage/")
async def enregistrer_triage(
    triage_in: TriageCreate,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "infirmier")),
):
    sejour = db.query(Sejour).filter(Sejour.sejour_id == triage_in.sejour_id).first()
    if not sejour:
        raise HTTPException(status_code=404, detail="Sejour introuvable")

    triage = TriageRecord(
        sejour_id=triage_in.sejour_id,
        soignant_id=current_user.personnel_id,
        score_ccmu=triage_in.score_ccmu,
        score_french=triage_in.score_french,
        poids=triage_in.poids,
        temperature=triage_in.temperature,
        fc=triage_in.fc,
        ta_systolique=triage_in.ta_systolique,
        ta_diastolique=triage_in.ta_diastolique,
        spo2=triage_in.spo2,
        glasgow=triage_in.glasgow,
        glasgow_e=triage_in.glasgow_e,
        glasgow_v=triage_in.glasgow_v,
        glasgow_m=triage_in.glasgow_m,
        douleur=triage_in.douleur,
        notes=triage_in.notes,
        zone=triage_in.zone,
    )
    db.add(triage)

    # Automatically initialize monitoring vitals from triage
    init_cv = ConstantesVitales(
        sejour_id=triage_in.sejour_id,
        prise_par_id=current_user.personnel_id,
        temperature=triage_in.temperature,
        fc=triage_in.fc,
        ta_systolique=triage_in.ta_systolique,
        ta_diastolique=triage_in.ta_diastolique,
        spo2=triage_in.spo2,
        douleur=triage_in.douleur,
        glasgow=triage_in.glasgow,
        frequence_respiratoire=16,
        rythme_cardiaque="sinusal",
    )
    db.add(init_cv)

    if sejour.statut == "En attente de triage":
        sejour.statut = "En attente d'installation"

    log_action(
        db,
        "TRIAGE",
        personnel_id=current_user.personnel_id,
        entite="sejour",
        entite_id=sejour.sejour_id,
        detail={"ccmu": triage_in.score_ccmu},
    )

    # Event sourcing
    log_patient_event(
        db,
        sejour_id=sejour.sejour_id,
        event_type="TRIAGE",
        personnel_id=current_user.personnel_id,
        data={"ccmu": triage_in.score_ccmu, "zone": triage_in.zone},
    )

    db.commit()

    # Broadcast to WebSocket clients
    await manager.broadcast_event(
        "TRIAGE",
        sejour.sejour_id,
        {
            "ccmu": triage_in.score_ccmu,
            "patient_nom": sejour.patient.nom,
            "patient_prenom": sejour.patient.prenom,
        },
    )

    return {"message": "Triage enregistre"}


@router.post("/retriage/")
async def retriage_patient(
    triage_in: TriageCreate,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "infirmier")),
):
    sejour = db.query(Sejour).filter(Sejour.sejour_id == triage_in.sejour_id).first()
    if not sejour:
        raise HTTPException(status_code=404, detail="Sejour introuvable")

    triage = TriageRecord(
        sejour_id=triage_in.sejour_id,
        soignant_id=current_user.personnel_id,
        score_ccmu=triage_in.score_ccmu,
        score_french=triage_in.score_french,
        poids=triage_in.poids,
        temperature=triage_in.temperature,
        fc=triage_in.fc,
        ta_systolique=triage_in.ta_systolique,
        ta_diastolique=triage_in.ta_diastolique,
        spo2=triage_in.spo2,
        glasgow=triage_in.glasgow,
        glasgow_e=triage_in.glasgow_e,
        glasgow_v=triage_in.glasgow_v,
        glasgow_m=triage_in.glasgow_m,
        douleur=triage_in.douleur,
        notes=triage_in.notes,
        zone=triage_in.zone,
    )
    db.add(triage)

    # Automatically initialize monitoring vitals from retriage
    retriage_cv = ConstantesVitales(
        sejour_id=triage_in.sejour_id,
        prise_par_id=current_user.personnel_id,
        temperature=triage_in.temperature,
        fc=triage_in.fc,
        ta_systolique=triage_in.ta_systolique,
        ta_diastolique=triage_in.ta_diastolique,
        spo2=triage_in.spo2,
        douleur=triage_in.douleur,
        glasgow=triage_in.glasgow,
        frequence_respiratoire=16,
        rythme_cardiaque="sinusal",
    )
    db.add(retriage_cv)

    log_action(
        db,
        "RETRIAGE",
        personnel_id=current_user.personnel_id,
        entite="sejour",
        entite_id=sejour.sejour_id,
        detail={"ccmu": triage_in.score_ccmu, "zone": triage_in.zone},
    )

    # Event sourcing
    log_patient_event(
        db,
        sejour_id=sejour.sejour_id,
        event_type="RETRIAGE",
        personnel_id=current_user.personnel_id,
        data={"ccmu": triage_in.score_ccmu, "zone": triage_in.zone},
    )

    db.commit()

    # Broadcast to WebSocket clients
    await manager.broadcast_event(
        "RETRIAGE",
        sejour.sejour_id,
        {
            "ccmu": triage_in.score_ccmu,
            "patient_nom": sejour.patient.nom,
            "patient_prenom": sejour.patient.prenom,
        },
    )

    return {"message": "Retriage enregistré avec succès"}
