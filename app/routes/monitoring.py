from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.dependencies import require_roles
from app.utils.db_utils import get_db
from app.models import Sejour, Patient, AffectationLit, Lit, Salle, ConstantesVitales, Personnel, TriageRecord
from app.schemas import ConstanteCreate, ConstanteRead
from datetime import datetime, timezone
from typing import List
from app.websocket import manager
from models.predict_news2 import predict_deterioration_risk

router = APIRouter(tags=["monitoring"])


def _compute_risk_for_constantes(db: Session, sejour_id: int, current: ConstantesVitales):
    prev_cv = (
        db.query(ConstantesVitales)
        .filter(ConstantesVitales.sejour_id == sejour_id)
        .filter(ConstantesVitales.constante_id != current.constante_id)
        .order_by(ConstantesVitales.heure_prise.desc())
        .first()
    )
    prev_fc = prev_cv.fc if prev_cv else None
    prev_spo2 = prev_cv.spo2 if prev_cv else None
    prev_tas = prev_cv.ta_systolique if prev_cv else None
    prev_gcs = prev_cv.glasgow if prev_cv else None
    prev_fr = prev_cv.frequence_respiratoire if prev_cv else None

    try:
        result = predict_deterioration_risk(
            fc=current.fc or 80,
            ta_systolique=current.ta_systolique or 120,
            ta_diastolique=current.ta_diastolique or 80,
            spo2=current.spo2 or 98,
            temperature=current.temperature or 37.0,
            glasgow_total=current.glasgow or 15,
            douleur_eva=current.douleur or 0,
            rythme=current.rythme_cardiaque or "sinusal",
            frequence_respiratoire=current.frequence_respiratoire or 16,
            prev_fc=prev_fc,
            prev_spo2=prev_spo2,
            prev_ta_systolique=prev_tas,
            prev_glasgow_total=prev_gcs,
            prev_frequence_respiratoire=prev_fr,
        )
    except Exception:
        return None

    return result


@router.get("/sejours/installes")
def get_sejours_installes(
    db: Session = Depends(get_db),
    current_user: Personnel = Depends(require_roles("admin", "medecin", "infirmier")),
):
    active_statuses = ["Sorti", "Annulé"]
    subquery = (
        db.query(
            ConstantesVitales.sejour_id,
            func.max(ConstantesVitales.heure_prise).label("latest_time"),
        )
        .group_by(ConstantesVitales.sejour_id)
        .subquery()
    )

    results = (
        db.query(
            Sejour,
            Patient,
            AffectationLit,
            Lit,
            Salle,
            ConstantesVitales,
        )
        .join(Patient, Sejour.patient_id == Patient.patient_id)
        .join(AffectationLit, Sejour.sejour_id == AffectationLit.sejour_id)
        .join(Lit, AffectationLit.lit_id == Lit.lit_id)
        .join(Salle, Lit.salle_id == Salle.salle_id)
        .outerjoin(
            subquery,
            Sejour.sejour_id == subquery.c.sejour_id,
        )
        .outerjoin(
            ConstantesVitales,
            (ConstantesVitales.sejour_id == subquery.c.sejour_id)
            & (ConstantesVitales.heure_prise == subquery.c.latest_time),
        )
        .filter(
            ~Sejour.statut.in_(active_statuses),
            AffectationLit.heure_fin.is_(None),
        )
        .all()
    )

    output = []
    for sejour, patient, affectation, lit, salle, latest_vitals in results:
        vitals_dict = None
        if latest_vitals:
            vitals_dict = {
                "temperature": latest_vitals.temperature,
                "fc": latest_vitals.fc,
                "ta_systolique": latest_vitals.ta_systolique,
                "ta_diastolique": latest_vitals.ta_diastolique,
                "spo2": latest_vitals.spo2,
                "douleur": latest_vitals.douleur,
                "glasgow": latest_vitals.glasgow,
                "frequence_respiratoire": latest_vitals.frequence_respiratoire,
                "rythme_cardiaque": latest_vitals.rythme_cardiaque,
                "risk_level": latest_vitals.risk_level,
                "risk_confidence": latest_vitals.risk_confidence,
                "heure_prise": latest_vitals.heure_prise.isoformat() if latest_vitals.heure_prise else None,
            }
        else:
            t_rec = (
                db.query(TriageRecord)
                .filter(TriageRecord.sejour_id == sejour.sejour_id)
                .order_by(TriageRecord.heure_triage.desc())
                .first()
            )
            if t_rec:
                vitals_dict = {
                    "temperature": t_rec.temperature,
                    "fc": t_rec.fc,
                    "ta_systolique": t_rec.ta_systolique,
                    "ta_diastolique": t_rec.ta_diastolique,
                    "spo2": t_rec.spo2,
                    "douleur": t_rec.douleur,
                    "glasgow": t_rec.glasgow,
                    "frequence_respiratoire": 16,
                    "rythme_cardiaque": "sinusal",
                    "risk_level": "LOW",
                    "risk_confidence": 0.05,
                    "heure_prise": t_rec.heure_triage.isoformat() if t_rec.heure_triage else None,
                }

        output.append({
            "sejour_id": sejour.sejour_id,
            "patient": {
                "patient_id": patient.patient_id,
                "nom": patient.nom,
                "prenom": patient.prenom,
            },
            "lit": {
                "lit_id": lit.lit_id,
                "numero_lit": lit.numero_lit,
            },
            "salle": {
                "salle_id": salle.salle_id,
                "nom": salle.nom_salle,
            },
            "statut": sejour.statut,
            "latest_constantes": vitals_dict,
        })

    return output


@router.post("/sejours/{sejour_id}/constantes", response_model=ConstanteRead)
async def add_constantes_vitales(
    sejour_id: int,
    data: ConstanteCreate,
    db: Session = Depends(get_db),
    current_user: Personnel = Depends(require_roles("admin", "medecin", "infirmier")),
):
    sejour = db.query(Sejour).filter(Sejour.sejour_id == sejour_id).first()
    if not sejour:
        raise HTTPException(status_code=404, detail="Séjour non trouvé")

    nouvelle = ConstantesVitales(
        sejour_id=sejour_id,
        prise_par_id=current_user.personnel_id,
        temperature=data.temperature,
        fc=data.fc,
        ta_systolique=data.ta_systolique,
        ta_diastolique=data.ta_diastolique,
        spo2=data.spo2,
        douleur=data.douleur,
        glasgow=data.glasgow,
        frequence_respiratoire=data.frequence_respiratoire,
        rythme_cardiaque=data.rythme_cardiaque,
        heure_prise=datetime.now(timezone.utc),
    )

    db.add(nouvelle)
    db.commit()
    db.refresh(nouvelle)

    risk = _compute_risk_for_constantes(db, sejour_id, nouvelle)
    if risk:
        nouvelle.risk_level = risk["risk_level"]
        nouvelle.risk_confidence = risk["confidence"]
        db.commit()
        db.refresh(nouvelle)

    await manager.broadcast_event(
        "CONSTANTES_STREAM",
        sejour_id,
        {
            "fc": nouvelle.fc,
            "ta_systolique": nouvelle.ta_systolique,
            "ta_diastolique": nouvelle.ta_diastolique,
            "spo2": nouvelle.spo2,
            "temperature": nouvelle.temperature,
            "frequence_respiratoire": nouvelle.frequence_respiratoire,
            "glasgow": nouvelle.glasgow,
            "douleur": nouvelle.douleur,
            "rythme_cardiaque": nouvelle.rythme_cardiaque,
            "heure_prise": nouvelle.heure_prise.isoformat() if nouvelle.heure_prise else None,
            "risk_level": nouvelle.risk_level,
            "risk_confidence": nouvelle.risk_confidence,
        },
    )

    return ConstanteRead(
        constante_id=nouvelle.constante_id,
        sejour_id=nouvelle.sejour_id,
        prise_par_id=nouvelle.prise_par_id,
        heure_prise=nouvelle.heure_prise,
        temperature=nouvelle.temperature,
        fc=nouvelle.fc,
        ta_systolique=nouvelle.ta_systolique,
        ta_diastolique=nouvelle.ta_diastolique,
        spo2=nouvelle.spo2,
        douleur=nouvelle.douleur,
        glasgow=nouvelle.glasgow,
        frequence_respiratoire=nouvelle.frequence_respiratoire,
        rythme_cardiaque=nouvelle.rythme_cardiaque,
        risk_level=nouvelle.risk_level,
        risk_confidence=nouvelle.risk_confidence,
    )


@router.get("/sejours/{sejour_id}/constantes", response_model=List[ConstanteRead])
def get_constantes_vitales(
    sejour_id: int,
    db: Session = Depends(get_db),
    current_user: Personnel = Depends(require_roles("admin", "medecin", "infirmier")),
):
    from app.models import TriageRecord

    sejour = db.query(Sejour).filter(Sejour.sejour_id == sejour_id).first()
    if not sejour:
        raise HTTPException(status_code=404, detail="Séjour non trouvé")

    # Constant monitoring entries (nurse vitals)
    constantes = (
        db.query(ConstantesVitales)
        .filter(ConstantesVitales.sejour_id == sejour_id)
        .order_by(ConstantesVitales.heure_prise.desc())
        .all()
    )

    # Triage/retriage records as pseudo-vitals entries
    triages = (
        db.query(TriageRecord)
        .filter(TriageRecord.sejour_id == sejour_id)
        .order_by(TriageRecord.heure_triage.desc())
        .all()
    )

    merged = []

    for t in triages:
        merged.append(ConstanteRead(
            constante_id=-t.triage_id,
            sejour_id=t.sejour_id,
            prise_par_id=t.soignant_id,
            heure_prise=t.heure_triage,
            temperature=t.temperature,
            fc=t.fc,
            ta_systolique=t.ta_systolique,
            ta_diastolique=t.ta_diastolique,
            spo2=t.spo2,
            douleur=t.douleur,
            glasgow=t.glasgow,
            frequence_respiratoire=None,
            rythme_cardiaque=None,
            risk_level=None,
            risk_confidence=None,
        ))

    for c in constantes:
        merged.append(ConstanteRead(
            constante_id=c.constante_id,
            sejour_id=c.sejour_id,
            prise_par_id=c.prise_par_id,
            heure_prise=c.heure_prise,
            temperature=c.temperature,
            fc=c.fc,
            ta_systolique=c.ta_systolique,
            ta_diastolique=c.ta_diastolique,
            spo2=c.spo2,
            douleur=c.douleur,
            glasgow=c.glasgow,
            frequence_respiratoire=c.frequence_respiratoire,
            rythme_cardiaque=c.rythme_cardiaque,
            risk_level=c.risk_level,
            risk_confidence=c.risk_confidence,
        ))

    merged.sort(key=lambda x: x.heure_prise or datetime(2000, 1, 1, tzinfo=timezone.utc), reverse=True)
    return merged