from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import (
    Lit,
    AffectationLit,
    Sejour,
    log_action,
    Personnel,
    log_patient_event,
)
from app.schemas import AffectationCreate, TransfertCreate
from app.utils.db_utils import get_db
from app.dependencies import require_roles
from app.websocket import manager
from app.routes.sejours import _predict_for_sejour

router = APIRouter()


@router.post("/lits/affectation")
async def affecter_patient_lit(
    aff_in: AffectationCreate,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "infirmier")),
):
    sejour = db.query(Sejour).filter(Sejour.sejour_id == aff_in.sejour_id).first()
    if not sejour:
        raise HTTPException(status_code=404, detail="Séjour introuvable")

    nouveau_lit = db.query(Lit).filter(Lit.lit_id == aff_in.lit_id).first()
    if not nouveau_lit:
        raise HTTPException(status_code=404, detail="Lit introuvable")

    if nouveau_lit.statut != "libre":
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Ce lit vient d'être assigné à un autre patient.",
                "statut_actuel": nouveau_lit.statut,
            },
        )

    nouveau_lit.statut = "occupe"
    db.flush()

    ancienne_aff = (
        db.query(AffectationLit)
        .filter(
            AffectationLit.sejour_id == sejour.sejour_id,
            AffectationLit.heure_fin == None,
        )
        .first()
    )

    if ancienne_aff:
        ancienne_aff.heure_fin = datetime.now(timezone.utc)
        ancien_lit = db.query(Lit).filter(Lit.lit_id == ancienne_aff.lit_id).first()
        if ancien_lit:
            ancien_lit.statut = "en_nettoyage"

    nouvelle_aff = AffectationLit(sejour_id=sejour.sejour_id, lit_id=nouveau_lit.lit_id)
    db.add(nouvelle_aff)

    if sejour.statut in ("En attente de triage", "En attente d'installation", "URGENCE_VITALE - A INSTALLER"):
        if sejour.statut == "URGENCE_VITALE - A INSTALLER":
            sejour.statut = "URGENCE_VITALE - INSTALLÉ"
        else:
            sejour.statut = "Installé"

    log_action(
        db,
        "AFFECTATION_LIT",
        personnel_id=current_user.personnel_id,
        entite="sejour",
        entite_id=sejour.sejour_id,
        detail={"lit_id": nouveau_lit.lit_id},
    )

    # Event sourcing
    log_patient_event(
        db,
        sejour_id=sejour.sejour_id,
        event_type="LIT_AFFECTE",
        personnel_id=current_user.personnel_id,
        data={"lit_id": nouveau_lit.lit_id, "numero_lit": nouveau_lit.numero_lit},
    )

    db.commit()

    # Broadcast
    await manager.broadcast_event(
        "LIT_AFFECTE",
        sejour.sejour_id,
        {
            "lit_id": nouveau_lit.lit_id,
            "numero_lit": nouveau_lit.numero_lit,
            "patient_nom": sejour.patient.nom,
            "patient_prenom": sejour.patient.prenom,
        },
    )

    return {"message": f"Patient affecté au lit {nouveau_lit.numero_lit}"}


@router.post("/lits/transfert")
async def transferer_patient(
    trans_in: TransfertCreate,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "infirmier")),
):
    sejour = db.query(Sejour).filter(Sejour.sejour_id == trans_in.sejour_id).first()
    if not sejour:
        raise HTTPException(status_code=404, detail="Séjour introuvable")

    nouveau_lit = db.query(Lit).filter(Lit.lit_id == trans_in.nouveau_lit_id).first()
    if not nouveau_lit or nouveau_lit.statut != "libre":
        raise HTTPException(status_code=400, detail="Nouveau lit indisponible")

    nouveau_lit.statut = "occupe"
    db.flush()

    ancienne_aff = (
        db.query(AffectationLit)
        .filter(
            AffectationLit.sejour_id == sejour.sejour_id,
            AffectationLit.heure_fin == None,
        )
        .first()
    )

    if ancienne_aff:
        ancienne_aff.heure_fin = datetime.now(timezone.utc)
        ancien_lit = db.query(Lit).filter(Lit.lit_id == ancienne_aff.lit_id).first()
        if ancien_lit:
            ancien_lit.statut = "en_nettoyage"

    nouvelle_aff = AffectationLit(sejour_id=sejour.sejour_id, lit_id=nouveau_lit.lit_id)
    db.add(nouvelle_aff)

    log_action(
        db,
        "TRANSFERT_LIT",
        personnel_id=current_user.personnel_id,
        entite="sejour",
        entite_id=sejour.sejour_id,
        detail={
            "nouveau_lit_id": nouveau_lit.lit_id,
            "numero_lit": nouveau_lit.numero_lit,
        },
    )

    # Event sourcing
    log_patient_event(
        db,
        sejour_id=sejour.sejour_id,
        event_type="LIT_TRANSFERE",
        personnel_id=current_user.personnel_id,
        data={
            "from_lit": ancienne_aff.lit_id if ancienne_aff else None,
            "to_lit": nouveau_lit.lit_id,
        },
    )

    db.commit()

    # Broadcast
    await manager.broadcast_event(
        "LIT_TRANSFERE",
        sejour.sejour_id,
        {
            "from_lit": ancienne_aff.lit_id if ancienne_aff else None,
            "to_lit": nouveau_lit.lit_id,
            "numero_lit": nouveau_lit.numero_lit,
            "patient_nom": sejour.patient.nom,
        },
    )

    return {"message": "Transfert effectué"}

    nouvelle_aff = AffectationLit(sejour_id=sejour.sejour_id, lit_id=nouveau_lit.lit_id)
    db.add(nouvelle_aff)

    log_action(
        db,
        "TRANSFERT_LIT",
        personnel_id=current_user.personnel_id,
        entite="sejour",
        entite_id=sejour.sejour_id,
        detail={"nouveau_lit_id": nouveau_lit.lit_id},
    )
    db.commit()

    return {"message": "Transfert effectuer"}


@router.get("/lits/")
async def get_lits(
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "infirmier", "medecin")),
):
    lits = db.query(Lit).all()
    resultats = []
    for l in lits:
        active_aff = (
            db.query(AffectationLit)
            .filter(
                AffectationLit.lit_id == l.lit_id,
                AffectationLit.heure_fin == None,
            )
            .first()
        )
        patient_info = None
        if active_aff:
            s = (
                db.query(Sejour)
                .filter(Sejour.sejour_id == active_aff.sejour_id)
                .first()
            )
            if s:
                triage = s.triages[-1] if s.triages else None
                patient_info = {
                    "sejour_id": s.sejour_id,
                    "patient_nom": s.patient.nom,
                    "patient_prenom": s.patient.prenom,
                    "statut": s.statut,
                    "predicted_wait_time_min": _predict_for_sejour(s, triage),
                }
        resultats.append(
            {
                "lit_id": l.lit_id,
                "numero_lit": l.numero_lit,
                "type_lit": l.type_lit,
                "statut": l.statut,
                "salle": l.salle.nom_salle,
                "zone": l.salle.zone,
                "patient": patient_info,
            }
        )
    return resultats


@router.put("/lits/{lit_id}/statut")
async def update_lit_statut(
    lit_id: int,
    statut_data: dict,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "infirmier", "medecin")),
):
    from fastapi import HTTPException
    from app.models import AffectationLit

    lit = db.query(Lit).filter(Lit.lit_id == lit_id).first()
    if not lit:
        raise HTTPException(status_code=404, detail="Lit non trouvé")

    old_statut = lit.statut
    lit.statut = statut_data["statut"]

    if statut_data["statut"] == "libre":
        active_aff = (
            db.query(AffectationLit)
            .filter(AffectationLit.lit_id == lit_id, AffectationLit.heure_fin == None)
            .first()
        )
        if active_aff:
            active_aff.heure_fin = datetime.now(timezone.utc)

    from app.models import log_action

    log_action(
        db,
        "LIT_STATUT",
        personnel_id=current_user.personnel_id,
        entite="lit",
        entite_id=lit_id,
        detail={"ancien_statut": old_statut, "nouveau_statut": statut_data["statut"]},
    )
    db.commit()

    return {"message": f"Statut du lit mis à jour: {statut_data['statut']}"}


@router.delete("/lits/{lit_id}")
async def delete_lit(
    lit_id: int,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin")),
):
    lit = db.query(Lit).filter(Lit.lit_id == lit_id).first()
    if not lit:
        raise HTTPException(status_code=404, detail="Lit non trouvé")

    if lit.statut == "occupe":
        raise HTTPException(status_code=400, detail="Impossible de supprimer un lit occupé")

    db.query(AffectationLit).filter(AffectationLit.lit_id == lit_id).delete()
    db.delete(lit)

    log_action(
        db,
        "LIT_DELETE",
        personnel_id=current_user.personnel_id,
        entite="lit",
        entite_id=lit_id,
        detail={"numero_lit": lit.numero_lit},
    )
    db.commit()
    return {"message": f"Lit {lit.numero_lit} supprimé"}
