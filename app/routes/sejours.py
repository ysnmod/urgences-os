import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import Sejour, Personnel
from app.utils.db_utils import get_db
from app.dependencies import require_roles
from datetime import datetime, timezone
from models.predict import load_model, predict

logger = logging.getLogger(__name__)

router = APIRouter()

_ml_artifact = None


def _get_ml_artifact():
    global _ml_artifact
    if _ml_artifact is None:
        try:
            _ml_artifact = load_model()
        except (FileNotFoundError, Exception):
            _ml_artifact = None
    return _ml_artifact


def _ccmu_to_urgency(score: int | None) -> str:
    """Map CCMU score to model urgency_level."""
    mapping = {1: "Low", 2: "Low", 3: "Medium", 4: "High", 5: "Critical"}
    if score is None:
        return "Low"
    return mapping.get(score, "Low")


def _hour_to_time_of_day(hour: int) -> str:
    if hour < 6:
        return "Night"
    if hour < 9:
        return "Early Morning"
    if hour < 12:
        return "Late Morning"
    if hour < 17:
        return "Afternoon"
    if hour < 20:
        return "Evening"
    return "Night"


def _month_to_season(month: int) -> str:
    if month in (12, 1, 2):
        return "Winter"
    if month in (3, 4, 5):
        return "Spring"
    if month in (6, 7, 8):
        return "Summer"
    return "Fall"


_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _predict_for_sejour(sejour, triage) -> float | None:
    """Compute predicted wait time for a sejour from triage + arrival data."""
    # Only predict after triage — without CCMU the default "Low" is misleading
    if triage is None or triage.score_ccmu is None:
        return None
    artifact = _get_ml_artifact()
    if artifact is None:
        return None
    try:
        dt = sejour.date_arrivee
        if dt is None:
            return None
        hour = dt.hour
        weekday = dt.weekday()
        month = dt.month
        ccmu = triage.score_ccmu if triage else None
        data = {
            "region": "Urban",
            "urgency_level": _ccmu_to_urgency(ccmu),
            "time_of_day": _hour_to_time_of_day(hour),
            "day_of_week": _DAY_NAMES[weekday],
            "season": _month_to_season(month),
            "nurse_patient_ratio": 3,
            "specialist_availability": 5,
            "facility_beds": 100,
            "hour": hour,
            "weekday": weekday,
            "month": month,
            "weekend": 1 if weekday >= 5 else 0,
        }
        return predict(data, artifact)
    except Exception as exc:
        logger.warning("Prediction failed for sejour %s: %s", sejour.sejour_id, exc)
        return None


@router.get("/sejours/historique")
async def get_historique(
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(
        require_roles("admin", "secretaire", "medecin")
    ),
):
    sejours = (
        db.query(Sejour)
        .filter(Sejour.statut == "Sorti")
        .order_by(Sejour.date_sortie.desc())
        .limit(50)
        .all()
    )

    resultats = []
    for s in sejours:
        base = {
            "sejour_id": s.sejour_id,
            "patient_nom": s.patient.nom,
            "patient_prenom": s.patient.prenom,
            "date_sortie": s.date_sortie,
            "mode_sortie": s.mode_sortie,
        }
        if current_user.role in ("admin", "medecin", "secretaire"):
            base["diagnostic"] = s.diagnostic_sortie
            base["courrier_sortie"] = s.courrier_sortie
        else:
            base["diagnostic"] = "[Confidentiel médical]"
            base["courrier_sortie"] = None
        resultats.append(base)

    return resultats


@router.get("/sejours/attente")
async def file_attente(
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(
        require_roles("admin", "secretaire", "medecin", "infirmier")
    ),
):
    sejours = db.query(Sejour).filter(Sejour.statut.notin_(["Sorti", "Annulé"])).all()
    resultats = []
    for s in sejours:
        triage = s.triages[-1] if s.triages else None

        aff = next((a for a in s.affectations_lit if a.heure_fin is None), None)
        lit_info = None
        if aff:
            lit_info = {
                "id": aff.lit.lit_id,
                "label": aff.lit.numero_lit,
                "salle": aff.lit.salle.nom_salle,
            }

        predicted = _predict_for_sejour(s, triage)

        resultats.append(
            {
                "sejour_id": s.sejour_id,
                "patient_id": s.patient_id,
                "patient_nom": s.patient.nom,
                "patient_prenom": s.patient.prenom,
                "heure_arrivee": s.date_arrivee,
                "motif_visite": s.motif_visite,
                "statut": s.statut,
                "score_ccmu": triage.score_ccmu if triage else None,
                "zone": triage.zone if triage else None,
                "lit": lit_info,
                "priorite_initiale": s.priorite_initiale,
                "mode_arrivee": s.mode_arrivee,
                "predicted_wait_time_min": predicted,
                "triage": {
                    "heure_triage": triage.heure_triage,
                    "score_ccmu": triage.score_ccmu,
                    "temperature": triage.temperature,
                    "fc": triage.fc,
                    "ta_systolique": triage.ta_systolique,
                    "ta_diastolique": triage.ta_diastolique,
                    "spo2": triage.spo2,
                    "glasgow": triage.glasgow,
                    "glasgow_e": triage.glasgow_e,
                    "glasgow_v": triage.glasgow_v,
                    "glasgow_m": triage.glasgow_m,
                    "douleur": triage.douleur,
                    "zone": triage.zone,
                    "notes": triage.notes,
                }
                if triage
                else None,
                "age": (datetime.now(timezone.utc).date() - s.patient.date_naissance).days // 365 if s.patient.date_naissance else None,
                "sexe": s.patient.sexe,
            }
        )
    return sorted(
        resultats, key=lambda x: (x["score_ccmu"] is not None, -(x["score_ccmu"] or 0))
    )


@router.get("/sejours/{sejour_id}")
async def get_sejour(
    sejour_id: int,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(
        require_roles("admin", "secretaire", "medecin", "infirmier")
    ),
):
    s = db.query(Sejour).filter(Sejour.sejour_id == sejour_id).first()
    if not s:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Sejour introuvable")

    triage = s.triages[-1] if s.triages else None
    affectation = next((a for a in s.affectations_lit if a.heure_fin is None), None)
    lit_info = None
    if affectation:
        l = affectation.lit
        lit_info = {
            "lit_id": l.lit_id,
            "numero": l.numero_lit,
            "salle": l.salle.nom_salle,
        }

    return {
        "sejour_id": s.sejour_id,
        "statut": s.statut,
        "heure_arrivee": s.date_arrivee,
        "motif_visite": s.motif_visite,
        "diagnostic_sortie": s.diagnostic_sortie,
        "mode_sortie": s.mode_sortie,
        "priorite_initiale": s.priorite_initiale,
        "mode_arrivee": s.mode_arrivee,
        "patient": {
            "patient_id": s.patient.patient_id,
            "nom": s.patient.nom,
            "prenom": s.patient.prenom,
            "date_naissance": str(s.patient.date_naissance)
            if s.patient.date_naissance
            else None,
            "sexe": s.patient.sexe,
            "telephone": s.patient.telephone,
            "groupe_sanguin": s.patient.groupe_sanguin,
            "allergies": s.patient.allergies,
        },
        "triage": {
            "heure_triage": triage.heure_triage,
            "score_ccmu": triage.score_ccmu,
            "temperature": triage.temperature,
            "fc": triage.fc,
            "ta_systolique": triage.ta_systolique,
            "ta_diastolique": triage.ta_diastolique,
            "spo2": triage.spo2,
            "glasgow": triage.glasgow,
            "glasgow_e": triage.glasgow_e,
            "glasgow_v": triage.glasgow_v,
            "glasgow_m": triage.glasgow_m,
            "douleur": triage.douleur,
            "zone": triage.zone,
            "notes": triage.notes,
        }
        if triage
        else None,
        "lit": lit_info,
        "examens": [
            {
                "examen_id": e.examen_id,
                "type_examen": e.type_examen,
                "statut": e.statut,
                "heure_prescription": e.heure_prescription,
                "resultat": e.resultat,
            }
            for e in s.examens
        ],
        "observations": [
            {
                "obs_id": o.obs_id,
                "texte": o.texte,
                "date": o.date_obs,
                "auteur_id": o.auteur_id,
            }
            for o in s.observations
        ],
        "prescriptions": [
            {
                "presc_id": p.presc_id,
                "medicament": p.medicament,
                "dose": p.dose,
                "annule": p.annule,
                "heure_prescription": p.heure_prescription,
            }
            for p in s.prescriptions
        ],
    }


@router.get("/sejours/{sejour_id}/courrier")
async def get_courrier(
    sejour_id: int,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "medecin")),
):
    from app.models import Observation, Prescription, Examen

    sejour = db.query(Sejour).filter(Sejour.sejour_id == sejour_id).first()
    if not sejour:
        raise HTTPException(status_code=404, detail="Sejour introuvable")

    nb_observations = (
        db.query(Observation).filter(Observation.sejour_id == sejour_id).count()
    )
    nb_prescriptions = (
        db.query(Prescription)
        .filter(Prescription.sejour_id == sejour_id, Prescription.annule == False)
        .count()
    )
    nb_examens = db.query(Examen).filter(Examen.sejour_id == sejour_id).count()

    patient = sejour.patient
    triage = sejour.triages[-1] if sejour.triages else None

    courrier = f"""COURRIER DE SORTIE - URGENCES

Patient: {patient.nom} {patient.prenom}
Né le: {patient.date_naissance}
Sexe: {patient.sexe}
Adresse: {patient.adresse or "Non renseignée"}
Téléphone: {patient.telephone or "Non renseigné"}
N° Sécurité Sociale: {patient.numero_secu or "Non renseigné"}

Date d'arrivée: {sejour.date_arrivee.strftime("%d/%m/%Y %H:%M")}
Motif de visite: {sejour.motif_visite}

{"=" * 50}
EVALUATION INITIALE (TRIAGE)
{"=" * 50}
"""

    if triage:
        courrier += f"""Score CCMU: {triage.score_ccmu}
Score French: {triage.score_french}
"""
        if triage.temperature:
            courrier += f"Température: {triage.temperature}°C\n"
        if triage.fc:
            courrier += f"Fréquence cardiaque: {triage.fc} bpm\n"
        if triage.ta_systolique and triage.ta_diastolique:
            courrier += f"Tension artérielle: {triage.ta_systolique}/{triage.ta_diastolique} mmHg\n"
        if triage.spo2:
            courrier += f"SpO2: {triage.spo2}%\n"
        if triage.glasgow:
            courrier += f"Glasgow: {triage.glasgow}/15\n"
        if triage.douleur is not None:
            courrier += f"Douleur (EVA): {triage.douleur}/10\n"
        if triage.notes:
            courrier += f"Notes: {triage.notes}\n"

    courrier += f"""
{"=" * 50}
OBSERVATIONS ({nb_observations})
{"=" * 50}
"""

    observations = (
        db.query(Observation)
        .filter(Observation.sejour_id == sejour_id)
        .order_by(Observation.date_obs)
        .all()
    )
    for obs in observations:
        courrier += f"- {obs.date_obs.strftime('%d/%m/%Y %H:%M')}: {obs.texte}\n"

    courrier += f"""
{"=" * 50}
PRESCRIPTIONS ({nb_prescriptions})
{"=" * 50}
"""

    prescriptions = (
        db.query(Prescription)
        .filter(Prescription.sejour_id == sejour_id, Prescription.annule == False)
        .all()
    )
    for presc in prescriptions:
        courrier += f"- {presc.medicament} ({presc.dose})\n"

    courrier += f"""
{"=" * 50}
EXAMENS ({nb_examens})
{"=" * 50}
"""

    examens = db.query(Examen).filter(Examen.sejour_id == sejour_id).all()
    for exam in examens:
        if exam.resultat:
            status = f"Résultat: {exam.resultat}"
        elif exam.statut == "réalisé" or exam.statut == "demande":
            status = "Effectué"
        elif exam.statut == "en attente":
            status = "En attente"
        else:
            status = exam.statut
        courrier += f"- {exam.type_examen}: {status}\n"

    return {
        "courrier": courrier,
        "genere_le": datetime.now(timezone.utc).isoformat(),
        "nb_observations": nb_observations,
        "nb_prescriptions": nb_prescriptions,
        "nb_examens": nb_examens,
    }


@router.put("/sejours/{sejour_id}/sortie")
async def enregistrer_sortie(
    sejour_id: int,
    sortie_in: "SortieCreate",
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "medecin")),
):
    from datetime import datetime, timezone
    from app.models import Lit, AffectationLit

    sejour = db.query(Sejour).filter(Sejour.sejour_id == sejour_id).first()
    if not sejour:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Sejour introuvable")

    if sejour.statut == "Sorti":
        raise HTTPException(status_code=400, detail="Patient déjà sorti")

    sejour.diagnostic_sortie = sortie_in.diagnostic_sortie
    sejour.mode_sortie = sortie_in.mode_sortie
    sejour.courrier_sortie = sortie_in.courrier_sortie
    sejour.date_sortie = datetime.now(timezone.utc)
    sejour.statut = "Sorti"

    active_aff = (
        db.query(AffectationLit)
        .filter(AffectationLit.sejour_id == sejour_id, AffectationLit.heure_fin == None)
        .first()
    )

    if active_aff:
        active_aff.heure_fin = datetime.now(timezone.utc)
        lit = db.query(Lit).filter(Lit.lit_id == active_aff.lit_id).first()
        if lit:
            lit.statut = "en_nettoyage"

    from app.models import log_action, log_patient_event

    log_action(
        db,
        "SORTIE",
        personnel_id=current_user.personnel_id,
        entite="sejour",
        entite_id=sejour_id,
        detail={"mode_sortie": sortie_in.mode_sortie},
    )

    # Event sourcing
    log_patient_event(
        db,
        sejour_id=sejour_id,
        event_type="SORTIE",
        personnel_id=current_user.personnel_id,
        data={
            "mode_sortie": sortie_in.mode_sortie,
            "diagnostic": sortie_in.diagnostic_sortie,
        },
    )

    db.commit()

    # Broadcast
    from app.websocket import manager

    await manager.broadcast_event(
        "SORTIE",
        sejour_id,
        {
            "mode_sortie": sortie_in.mode_sortie,
        },
    )

    return {"message": "Sortie enregistrée avec succès"}


@router.put("/sejours/{sejour_id}/annuler")
async def annuler_sejour(
    sejour_id: int,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin", "medecin", "infirmier", "secretaire")),
):
    from datetime import datetime, timezone
    from app.models import log_action, log_patient_event, AffectationLit, Lit

    sejour = db.query(Sejour).filter(Sejour.sejour_id == sejour_id).first()
    if not sejour:
        raise HTTPException(status_code=404, detail="Séjour introuvable")

    if sejour.statut in ("Sorti", "Annulé"):
        raise HTTPException(status_code=400, detail=f"Patient déjà {sejour.statut.lower()}")

    sejour.statut = "Annulé"
    sejour.date_sortie = datetime.now(timezone.utc)

    # Libérer le lit si affecté
    active_aff = (
        db.query(AffectationLit)
        .filter(AffectationLit.sejour_id == sejour_id, AffectationLit.heure_fin == None)
        .first()
    )
    if active_aff:
        active_aff.heure_fin = datetime.now(timezone.utc)
        lit = db.query(Lit).filter(Lit.lit_id == active_aff.lit_id).first()
        if lit:
            lit.statut = "en_nettoyage"

    log_action(
        db,
        "ANNULATION",
        personnel_id=current_user.personnel_id,
        entite="sejour",
        entite_id=sejour_id,
        detail={"motif": "Retiré du triage"},
    )
    log_patient_event(
        db,
        sejour_id=sejour_id,
        event_type="ANNULATION",
        personnel_id=current_user.personnel_id,
        data={"motif": "Retiré du triage"},
    )
    db.commit()

    from app.websocket import manager
    await manager.broadcast_event("ANNULATION", sejour_id, {})
    return {"message": "Séjour annulé"}


from app.schemas import SortieCreate
