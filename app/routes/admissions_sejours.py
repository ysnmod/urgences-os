from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import Sejour, Patient, log_action, Personnel, log_patient_event, DossierPrehospitalier, Lit, AffectationLit, Salle
from app.schemas import SejourCreate, PatientCreate
from app.utils.db_utils import get_db
from app.dependencies import require_roles
from app.websocket import manager

router = APIRouter()


@router.post("/admissions/")
async def admettre_patient(
    sejour_in: SejourCreate,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "secretaire")),
):
    if sejour_in.patient_id:
        patient = (
            db.query(Patient).filter(Patient.patient_id == sejour_in.patient_id).first()
        )
        if not patient:
            raise HTTPException(status_code=404, detail="Patient introuvable")
    else:
        pd = sejour_in.patient_data
        if not pd:
            raise HTTPException(status_code=400, detail="Données patient requises")

        # Check if patient already exists by numero_secu
        existing_patient = None
        if pd.numero_secu:
            existing_patient = (
                db.query(Patient).filter(Patient.numero_secu == pd.numero_secu).first()
            )
        
        if existing_patient:
            # Use existing patient
            patient = existing_patient
            
            # Check if they have an active sejour
            sejour_actif = (
                db.query(Sejour)
                .filter(Sejour.patient_id == patient.patient_id, Sejour.statut != "Sorti")
                .first()
            )
            if sejour_actif:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "Ce patient a déjà un séjour actif en cours.",
                        "sejour_id_existant": sejour_actif.sejour_id,
                        "statut_actuel": sejour_actif.statut,
                    },
                )
        else:
            # Create new patient
            patient = Patient(
                nom=pd.nom.upper(),
                prenom=pd.prenom,
                date_naissance=datetime.strptime(pd.date_naissance, "%Y-%m-%d").date()
                if pd.date_naissance
                else None,
                sexe=pd.sexe,
                telephone=pd.telephone,
                numero_secu=pd.numero_secu if pd.numero_secu else None,
            )
            db.add(patient)
            db.commit()
            db.refresh(patient)

    if sejour_in.patient_id:
        sejour_actif = (
            db.query(Sejour)
            .filter(Sejour.patient_id == sejour_in.patient_id, Sejour.statut != "Sorti")
            .first()
        )
        if sejour_actif:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Ce patient a déjà un séjour actif en cours.",
                    "sejour_id_existant": sejour_actif.sejour_id,
                    "statut_actuel": sejour_actif.statut,
                },
            )

    # Vérifier s'il existe un dossier préhospitalier pour ce patient
    dossier_prehospitalier = None
    if sejour_in.mode_arrivee == 'SMUR':
        # Chercher un dossier préhospitalier actif pour ce patient
        dossier_prehospitalier = (
            db.query(DossierPrehospitalier)
            .filter(
                DossierPrehospitalier.patient_id == patient.patient_id,
                DossierPrehospitalier.statut.in_(["PRÉ-ALERTE", "EN ROUTE", "ARRIVÉ"])
            )
            .first()
        )
    
    # Déterminer priorité initiale et statut selon mode d'arrivée
    if sejour_in.mode_arrivee in ['SMUR', 'pompiers']:
        priorite_initiale = 'URGENCE_VITALE'
        statut = 'URGENCE_VITALE - A INSTALLER'
    else:
        priorite_initiale = None
        statut = 'En attente de triage'
    
    sejour = Sejour(
        patient_id=patient.patient_id,
        mode_arrivee=sejour_in.mode_arrivee,
        motif_visite=sejour_in.motif_visite,
        statut=statut,
        priorite_initiale=priorite_initiale,
    )
    db.add(sejour)
    log_action(
        db,
        "ADMISSION",
        personnel_id=current_user.personnel_id,
        entite="sejour",
        entite_id=None,
        detail={
            "patient_id": patient.patient_id,
            "mode_arrivee": sejour_in.mode_arrivee,
        },
    )
    
    # Use flush to get the sejour_id without committing
    db.flush()
    # Now sejour should have its ID
    sejour_id = sejour.sejour_id
    
    # Si un dossier préhospitalier existe, le lier au séjour
    if dossier_prehospitalier:
        dossier_prehospitalier.sejour_id = sejour_id
        dossier_prehospitalier.statut = "FUSIONNÉ"
        # Mettre à jour les données du patient avec celles du dossier préhospitalier
        if dossier_prehospitalier.allergies and (not patient.allergies or patient.allergies.strip() == ""):
            patient.allergies = dossier_prehospitalier.allergies
        if dossier_prehospitalier.antecedents and (not patient.antecedents or patient.antecedents.strip() == ""):
            patient.antecedents = dossier_prehospitalier.antecedents
    
    # Event sourcing
    log_patient_event(
        db,
        sejour_id=sejour_id,
        event_type="ARRIVEE",
        personnel_id=current_user.personnel_id,
        data={"mode_arrivee": sejour_in.mode_arrivee},
    )
    
    # Auto-assign bed for URGENCE_VITALE patients (SMUR/pompiers)
    assigned_lit = None
    if sejour_in.mode_arrivee in ['SMUR', 'pompiers']:
        decho_lit = (
            db.query(Lit)
            .join(Salle, Salle.salle_id == Lit.salle_id)
            .filter(
                and_(
                    Lit.statut == 'libre',
                    Salle.specialite == 'dechocage',
                    Lit.type_lit == 'reanimation'
                )
            )
            .first()
        )

        if decho_lit:
            decho_lit.statut = 'occupe'
            affectation = AffectationLit(lit_id=decho_lit.lit_id, sejour_id=sejour_id)
            db.add(affectation)
            assigned_lit = decho_lit
            sejour.statut = 'URGENCE_VITALE - INSTALLÉ DÉCHOCAGE'
            log_action(db, "AUTO-AFFECTATION DECHO", personnel_id=current_user.personnel_id, entite="sejour", entite_id=sejour_id, detail={"lit_id": decho_lit.lit_id, "numero_lit": decho_lit.numero_lit, "zone": decho_lit.salle.zone})
            log_patient_event(db, sejour_id=sejour_id, event_type="LIT_AFFECTE", personnel_id=current_user.personnel_id, data={"lit_id": decho_lit.lit_id, "numero_lit": decho_lit.numero_lit, "zone": decho_lit.salle.zone, "specialite": "dechocage", "auto_assign": True})
        else:
            cc_lit = (
                db.query(Lit)
                .join(Salle, Salle.salle_id == Lit.salle_id)
                .filter(
                    and_(
                        Lit.statut == 'libre',
                        Salle.specialite == 'hospitalisation',
                        Lit.type_lit == 'observation'
                    )
                )
                .first()
            )

            if cc_lit:
                cc_lit.statut = 'occupe'
                affectation = AffectationLit(lit_id=cc_lit.lit_id, sejour_id=sejour_id)
                db.add(affectation)
                assigned_lit = cc_lit
                sejour.statut = 'URGENCE_VITALE - INSTALLÉ CC'
                log_action(db, "AUTO-AFFECTATION CC", personnel_id=current_user.personnel_id, entite="sejour", entite_id=sejour_id, detail={"lit_id": cc_lit.lit_id, "numero_lit": cc_lit.numero_lit, "zone": cc_lit.salle.zone})
                log_patient_event(db, sejour_id=sejour_id, event_type="LIT_AFFECTE", personnel_id=current_user.personnel_id, data={"lit_id": cc_lit.lit_id, "numero_lit": cc_lit.numero_lit, "zone": cc_lit.salle.zone, "specialite": "hospitalisation", "auto_assign": True})
    
    # Commit everything at once
    db.commit()
    
    # Broadcast to WebSocket clients
    broadcast_data = {
        "patient_nom": patient.nom,
        "patient_prenom": patient.prenom,
        "mode_arrivee": sejour_in.mode_arrivee,
        "statut": sejour.statut,  # Use updated statut from sejour object
        "priorite_initiale": priorite_initiale,
    }
    
    # Add bed assignment info if auto-assigned
    if assigned_lit:
        broadcast_data["lit_auto_assign"] = True
        broadcast_data["lit_id"] = assigned_lit.lit_id
        broadcast_data["lit_numero"] = assigned_lit.numero_lit
        broadcast_data["lit_zone"] = assigned_lit.salle.zone
    
    # Ajouter les informations du dossier préhospitalier si disponible
    if dossier_prehospitalier:
        broadcast_data["dossier_prehospitalier"] = True
        broadcast_data["numero_samu"] = dossier_prehospitalier.numero_samu
        broadcast_data["priorite_samu"] = dossier_prehospitalier.priorite_samu
    
    await manager.broadcast_event("ADMISSION", sejour_id, broadcast_data)
    
    return {"message": "Admission reussie", "sejour_id": sejour.sejour_id}
