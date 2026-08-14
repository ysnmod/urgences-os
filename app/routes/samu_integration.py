from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import DossierPrehospitalier, Sejour, Patient, log_action, Personnel
from app.schemas import DossierPrehospitalierCreate, DossierPrehospitalierUpdate, DossierPrehospitalierRead
from app.utils.db_utils import get_db
from app.dependencies import require_roles
from app.websocket import manager

router = APIRouter()


def parse_datetime(dt_str: str) -> datetime:
    """Parse datetime string in multiple formats"""
    if not dt_str:
        return None
    
    # Try different formats
    formats = [
        "%Y-%m-%d %H:%M:%S",  # 2026-04-20 22:34:00
        "%Y-%m-%dT%H:%M",     # 2026-04-20T22:34 (HTML datetime-local)
        "%Y-%m-%dT%H:%M:%S",  # 2026-04-20T22:34:00
        "%Y-%m-%d",           # 2026-04-20
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    
    # If all formats fail, try to parse ISO format
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError(f"Unable to parse datetime: {dt_str}")


@router.post("/samu/prealert", response_model=DossierPrehospitalierRead)
async def prealerte_samu(
    dossier_in: DossierPrehospitalierCreate,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "samu")),
):
    """
    Endpoint pour la pré-alerte SAMU/SMUR
    Crée un dossier préhospitalier et éventuellement un séjour préliminaire
    """
    # Vérifier si le numéro SAMU existe déjà
    existing_dossier = (
        db.query(DossierPrehospitalier)
        .filter(DossierPrehospitalier.numero_samu == dossier_in.numero_samu)
        .first()
    )
    if existing_dossier:
        raise HTTPException(
            status_code=409,
            detail=f"Un dossier avec le numéro SAMU {dossier_in.numero_samu} existe déjà"
        )
    
    # Créer le dossier préhospitalier
    dossier = DossierPrehospitalier(
        numero_samu=dossier_in.numero_samu,
        heure_appel_samu=parse_datetime(dossier_in.heure_appel_samu),
        heure_depart_smur=parse_datetime(dossier_in.heure_depart_smur) if dossier_in.heure_depart_smur else None,
        heure_arrivee_site=parse_datetime(dossier_in.heure_arrivee_site) if dossier_in.heure_arrivee_site else None,
        heure_depart_site=parse_datetime(dossier_in.heure_depart_site) if dossier_in.heure_depart_site else None,
        heure_arrivee_hopital=parse_datetime(dossier_in.heure_arrivee_hopital) if dossier_in.heure_arrivee_hopital else None,
        medecin_smur=dossier_in.medecin_smur,
        infirmier_smur=dossier_in.infirmier_smur,
        ambulancier_smur=dossier_in.ambulancier_smur,
        vehicule_smur=dossier_in.vehicule_smur,
        motif_appel=dossier_in.motif_appel,
        contexte=dossier_in.contexte,
        antecedents=dossier_in.antecedents,
        traitement_en_cours=dossier_in.traitement_en_cours,
        allergies=dossier_in.allergies,
        ta_prehospitaliere=dossier_in.ta_prehospitaliere,
        fc_prehospitaliere=dossier_in.fc_prehospitaliere,
        spo2_prehospitaliere=dossier_in.spo2_prehospitaliere,
        temperature_prehospitaliere=dossier_in.temperature_prehospitaliere,
        glycemie_prehospitaliere=dossier_in.glycemie_prehospitaliere,
        glasgow_prehospitaliere=dossier_in.glasgow_prehospitaliere,
        glasgow_e_prehospitaliere=dossier_in.glasgow_e_prehospitaliere,
        glasgow_v_prehospitaliere=dossier_in.glasgow_v_prehospitaliere,
        glasgow_m_prehospitaliere=dossier_in.glasgow_m_prehospitaliere,
        douleur_prehospitaliere=dossier_in.douleur_prehospitaliere,
        rythme_cardiaque=dossier_in.rythme_cardiaque,
        anomalies_ecg=dossier_in.anomalies_ecg,
        monitoring=dossier_in.monitoring,
        traitements_prehospitaliers=dossier_in.traitements_prehospitaliers,
        gestes_techniques=dossier_in.gestes_techniques,
        transmissions_medecin=dossier_in.transmissions_medecin,
        transmissions_infirmier=dossier_in.transmissions_infirmier,
        transmissions_ambulancier=dossier_in.transmissions_ambulancier,
        priorite_samu=dossier_in.priorite_samu,
        statut="PRÉ-ALERTE",
    )
    
    # Si des données patient sont fournies, créer un patient préliminaire
    if dossier_in.patient_nom and dossier_in.patient_prenom:
        patient = Patient(
            nom=dossier_in.patient_nom.upper(),
            prenom=dossier_in.patient_prenom,
            date_naissance=datetime.strptime(dossier_in.patient_date_naissance, "%Y-%m-%d").date() if dossier_in.patient_date_naissance else None,
            sexe=dossier_in.patient_sexe,
        )
        db.add(patient)
        db.flush()  # Pour obtenir l'ID patient
        dossier.patient_id = patient.patient_id
        
        # Créer un séjour préliminaire pour les urgences vitales
        if dossier_in.priorite_samu == "URGENCE_VITALE":
            sejour = Sejour(
                patient_id=patient.patient_id,
                mode_arrivee="SMUR",
                motif_visite=dossier_in.motif_appel[:255] if len(dossier_in.motif_appel) > 255 else dossier_in.motif_appel,
                statut="PRÉ-ALERTE SMUR",
                priorite_initiale="URGENCE_VITALE",
            )
            db.add(sejour)
            db.flush()  # Pour obtenir l'ID séjour
            dossier.sejour_id = sejour.sejour_id
    
    db.add(dossier)
    log_action(
        db,
        "PRÉ-ALERTE SAMU",
        personnel_id=current_user.personnel_id,
        entite="dossier_prehospitalier",
        entite_id=None,
        detail={
            "numero_samu": dossier_in.numero_samu,
            "priorite": dossier_in.priorite_samu,
            "motif": dossier_in.motif_appel[:100],
        },
    )
    db.commit()
    db.refresh(dossier)
    
    # Broadcast WebSocket event
    await manager.broadcast_event(
        "PRÉ-ALERTE_SAMU",
        dossier.dossier_id,
        {
            "numero_samu": dossier.numero_samu,
            "priorite": dossier.priorite_samu,
            "motif": dossier.motif_appel[:100],
            "statut": dossier.statut,
        },
    )
    
    return dossier


@router.put("/samu/update/{dossier_id}", response_model=DossierPrehospitalierRead)
async def mettre_a_jour_dossier_samu(
    dossier_id: int,
    update_data: DossierPrehospitalierUpdate,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "samu")),
):
    """
    Mettre à jour un dossier préhospitalier pendant le transport
    """
    dossier = db.query(DossierPrehospitalier).filter(DossierPrehospitalier.dossier_id == dossier_id).first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier préhospitalier introuvable")
    
    # Mettre à jour les champs fournis
    update_dict = update_data.dict(exclude_unset=True)
    
    # Gérer les dates
    date_fields = ['heure_depart_smur', 'heure_arrivee_site', 'heure_depart_site', 'heure_arrivee_hopital']
    for field in date_fields:
        if field in update_dict and update_dict[field]:
            update_dict[field] = parse_datetime(update_dict[field])
    
    # Mettre à jour le statut si fourni
    if 'statut' in update_dict:
        dossier.statut = update_dict['statut']
    
    # Mettre à jour les autres champs
    for key, value in update_dict.items():
        if key != 'statut' and hasattr(dossier, key):
            setattr(dossier, key, value)
    
    log_action(
        db,
        "MISE À JOUR SAMU",
        personnel_id=current_user.personnel_id,
        entite="dossier_prehospitalier",
        entite_id=dossier_id,
        detail={
            "champs_modifies": list(update_dict.keys()),
            "nouveau_statut": update_dict.get('statut'),
        },
    )
    db.commit()
    db.refresh(dossier)
    
    # Broadcast WebSocket event
    await manager.broadcast_event(
        "MISE_À_JOUR_SAMU",
        dossier.dossier_id,
        {
            "numero_samu": dossier.numero_samu,
            "statut": dossier.statut,
            "priorite": dossier.priorite_samu,
        },
    )
    
    return dossier


@router.post("/samu/arrival/{dossier_id}", response_model=DossierPrehospitalierRead)
async def notifier_arrivee_samu(
    dossier_id: int,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "samu")),
):
    """
    Notifier l'arrivée physique du SMUR à l'hôpital
    Met à jour le statut et crée/active le séjour si nécessaire
    """
    dossier = db.query(DossierPrehospitalier).filter(DossierPrehospitalier.dossier_id == dossier_id).first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier préhospitalier introuvable")
    
    # Marquer l'arrivée
    dossier.heure_arrivee_hopital = datetime.now()
    dossier.statut = "ARRIVÉ"
    
    # Si un séjour préliminaire existe, le mettre à jour
    if dossier.sejour_id:
        sejour = db.query(Sejour).filter(Sejour.sejour_id == dossier.sejour_id).first()
        if sejour:
            sejour.statut = "URGENCE_VITALE - A INSTALLER"
            sejour.date_arrivee = datetime.now()
    
    log_action(
        db,
        "ARRIVÉE SMUR",
        personnel_id=current_user.personnel_id,
        entite="dossier_prehospitalier",
        entite_id=dossier_id,
        detail={
            "numero_samu": dossier.numero_samu,
            "heure_arrivee": dossier.heure_arrivee_hopital.isoformat(),
        },
    )
    db.commit()
    db.refresh(dossier)
    
    # Broadcast WebSocket event
    await manager.broadcast_event(
        "ARRIVÉE_SMUR",
        dossier.dossier_id,
        {
            "numero_samu": dossier.numero_samu,
            "patient_nom": dossier.patient.nom if dossier.patient else "Inconnu",
            "patient_prenom": dossier.patient.prenom if dossier.patient else "Inconnu",
            "priorite": dossier.priorite_samu,
            "heure_arrivee": dossier.heure_arrivee_hopital.isoformat(),
        },
    )
    
    return dossier


@router.get("/samu/dossier/{dossier_id}", response_model=DossierPrehospitalierRead)
async def get_dossier_samu(
    dossier_id: int,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "samu", "medecin", "infirmier")),
):
    """Récupérer un dossier préhospitalier par ID"""
    dossier = db.query(DossierPrehospitalier).filter(DossierPrehospitalier.dossier_id == dossier_id).first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier préhospitalier introuvable")
    return dossier


@router.get("/samu/actifs", response_model=list[DossierPrehospitalierRead])
async def get_dossiers_actifs(
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "samu", "medecin", "infirmier")),
):
    """Récupérer tous les dossiers préhospitaliers actifs (non fusionnés)"""
    dossiers = (
        db.query(DossierPrehospitalier)
        .filter(DossierPrehospitalier.statut != "FUSIONNÉ")
        .order_by(DossierPrehospitalier.created_at.desc())
        .all()
    )
    return dossiers


@router.get("/samu/by-sejour/{sejour_id}", response_model=Optional[DossierPrehospitalierRead])
async def get_dossier_by_sejour(
    sejour_id: int,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "samu", "medecin", "infirmier")),
):
    """Récupérer un dossier préhospitalier par ID de séjour"""
    dossier = (
        db.query(DossierPrehospitalier)
        .filter(DossierPrehospitalier.sejour_id == sejour_id)
        .first()
    )
    return dossier


@router.post("/samu/link-to-sejour/{sejour_id}", response_model=DossierPrehospitalierRead)
async def creer_dossier_pour_sejour(
    sejour_id: int,
    dossier_in: DossierPrehospitalierCreate,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "samu", "medecin")),
):
    """
    Créer un dossier préhospitalier pour un séjour existant
    (Utilisé lors de l'admission d'un patient SMUR avec données préhospitalières)
    """
    # Vérifier que le séjour existe
    sejour = db.query(Sejour).filter(Sejour.sejour_id == sejour_id).first()
    if not sejour:
        raise HTTPException(status_code=404, detail="Séjour introuvable")
    
    # Vérifier si un dossier existe déjà pour ce séjour
    existing_dossier = (
        db.query(DossierPrehospitalier)
        .filter(DossierPrehospitalier.sejour_id == sejour_id)
        .first()
    )
    if existing_dossier:
        raise HTTPException(
            status_code=409,
            detail=f"Un dossier préhospitalier existe déjà pour ce séjour (ID: {existing_dossier.dossier_id})"
        )
    
    # Vérifier si le numéro SAMU existe déjà
    if dossier_in.numero_samu:
        existing_numero = (
            db.query(DossierPrehospitalier)
            .filter(DossierPrehospitalier.numero_samu == dossier_in.numero_samu)
            .first()
        )
        if existing_numero:
            raise HTTPException(
                status_code=409,
                detail=f"Un dossier avec le numéro SAMU {dossier_in.numero_samu} existe déjà"
            )
    
    # Créer le dossier préhospitalier lié au séjour existant
    dossier = DossierPrehospitalier(
        sejour_id=sejour_id,
        patient_id=sejour.patient_id,
        numero_samu=dossier_in.numero_samu,
        heure_appel_samu=parse_datetime(dossier_in.heure_appel_samu),
        heure_depart_smur=parse_datetime(dossier_in.heure_depart_smur) if dossier_in.heure_depart_smur else None,
        heure_arrivee_site=parse_datetime(dossier_in.heure_arrivee_site) if dossier_in.heure_arrivee_site else None,
        heure_depart_site=parse_datetime(dossier_in.heure_depart_site) if dossier_in.heure_depart_site else None,
        heure_arrivee_hopital=parse_datetime(dossier_in.heure_arrivee_hopital) if dossier_in.heure_arrivee_hopital else None,
        medecin_smur=dossier_in.medecin_smur,
        infirmier_smur=dossier_in.infirmier_smur,
        ambulancier_smur=dossier_in.ambulancier_smur,
        vehicule_smur=dossier_in.vehicule_smur,
        motif_appel=dossier_in.motif_appel,
        contexte=dossier_in.contexte,
        antecedents=dossier_in.antecedents,
        traitement_en_cours=dossier_in.traitement_en_cours,
        allergies=dossier_in.allergies,
        ta_prehospitaliere=dossier_in.ta_prehospitaliere,
        fc_prehospitaliere=dossier_in.fc_prehospitaliere,
        spo2_prehospitaliere=dossier_in.spo2_prehospitaliere,
        temperature_prehospitaliere=dossier_in.temperature_prehospitaliere,
        glycemie_prehospitaliere=dossier_in.glycemie_prehospitaliere,
        glasgow_prehospitaliere=dossier_in.glasgow_prehospitaliere,
        glasgow_e_prehospitaliere=dossier_in.glasgow_e_prehospitaliere,
        glasgow_v_prehospitaliere=dossier_in.glasgow_v_prehospitaliere,
        glasgow_m_prehospitaliere=dossier_in.glasgow_m_prehospitaliere,
        douleur_prehospitaliere=dossier_in.douleur_prehospitaliere,
        rythme_cardiaque=dossier_in.rythme_cardiaque,
        anomalies_ecg=dossier_in.anomalies_ecg,
        monitoring=dossier_in.monitoring,
        traitements_prehospitaliers=dossier_in.traitements_prehospitaliers,
        gestes_techniques=dossier_in.gestes_techniques,
        transmissions_medecin=dossier_in.transmissions_medecin,
        transmissions_infirmier=dossier_in.transmissions_infirmier,
        transmissions_ambulancier=dossier_in.transmissions_ambulancier,
        priorite_samu=dossier_in.priorite_samu,
        statut="FUSIONNÉ",  # Directement fusionné puisque lié à un séjour existant
    )
    
    db.add(dossier)
    log_action(
        db,
        "DOSSIER SMUR LIÉ",
        personnel_id=current_user.personnel_id,
        entite="dossier_prehospitalier",
        entite_id=None,
        detail={
            "sejour_id": sejour_id,
            "patient_id": sejour.patient_id,
            "numero_samu": dossier_in.numero_samu,
            "priorite": dossier_in.priorite_samu,
        },
    )
    db.commit()
    db.refresh(dossier)
    
    # Mettre à jour les données du patient avec celles du dossier préhospitalier
    patient = db.query(Patient).filter(Patient.patient_id == sejour.patient_id).first()
    if patient:
        if dossier.allergies and (not patient.allergies or patient.allergies.strip() == ""):
            patient.allergies = dossier.allergies
        if dossier.antecedents and (not patient.antecedents or patient.antecedents.strip() == ""):
            patient.antecedents = dossier.antecedents
        db.commit()
    
    # Broadcast WebSocket event
    await manager.broadcast_event(
        "DOSSIER_SMUR_LIÉ",
        sejour_id,
        {
            "dossier_id": dossier.dossier_id,
            "numero_samu": dossier.numero_samu,
            "patient_nom": patient.nom if patient else "Inconnu",
            "patient_prenom": patient.prenom if patient else "Inconnu",
        },
    )
    
    return dossier


@router.post("/samu/fusionner/{dossier_id}/{sejour_id}")
async def fusionner_dossier_sejour(
    dossier_id: int,
    sejour_id: int,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "medecin")),
):
    """
    Fusionner un dossier préhospitalier avec un séjour existant
    (Lorsque le patient arrive physiquement et est admis)
    """
    dossier = db.query(DossierPrehospitalier).filter(DossierPrehospitalier.dossier_id == dossier_id).first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier préhospitalier introuvable")
    
    sejour = db.query(Sejour).filter(Sejour.sejour_id == sejour_id).first()
    if not sejour:
        raise HTTPException(status_code=404, detail="Séjour introuvable")
    
    # Vérifier que le séjour n'est pas déjà lié à un dossier
    if dossier.sejour_id and dossier.sejour_id != sejour_id:
        raise HTTPException(
            status_code=409,
            detail=f"Ce dossier est déjà lié au séjour {dossier.sejour_id}"
        )
    
    # Lier le dossier au séjour
    dossier.sejour_id = sejour_id
    dossier.patient_id = sejour.patient_id
    dossier.statut = "FUSIONNÉ"
    
    # Mettre à jour les données du patient si nécessaire
    patient = db.query(Patient).filter(Patient.patient_id == sejour.patient_id).first()
    if patient:
        # Mettre à jour les allergies si le dossier en a
        if dossier.allergies and (not patient.allergies or patient.allergies.strip() == ""):
            patient.allergies = dossier.allergies
        
        # Mettre à jour les antécédents si le dossier en a
        if dossier.antecedents and (not patient.antecedents or patient.antecedents.strip() == ""):
            patient.antecedents = dossier.antecedents
    
    log_action(
        db,
        "FUSION DOSSIER SMUR",
        personnel_id=current_user.personnel_id,
        entite="dossier_prehospitalier",
        entite_id=dossier_id,
        detail={
            "dossier_id": dossier_id,
            "sejour_id": sejour_id,
            "patient_id": sejour.patient_id,
        },
    )
    db.commit()
    
    # Broadcast WebSocket event
    await manager.broadcast_event(
        "FUSION_SMUR",
        sejour_id,
        {
            "dossier_id": dossier_id,
            "numero_samu": dossier.numero_samu,
            "patient_nom": patient.nom if patient else "Inconnu",
            "patient_prenom": patient.prenom if patient else "Inconnu",
        },
    )
    
    return {"message": "Dossier fusionné avec succès", "dossier_id": dossier_id, "sejour_id": sejour_id}