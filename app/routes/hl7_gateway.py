# -*- coding: utf-8 -*-
"""
HL7 v2.5.1 Gateway Router for Hospital Emergency Interoperability.

Ingests ORU^R01 vital signs observation messages from medical monitors
and bridges them into the Urgences OS clinical workflow & real-time WebSockets.
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.models.base import SessionLocal
from app.utils.db_utils import get_db
from app.models import Sejour, ConstantesVitales, Personnel, Lit, AffectationLit
from app.utils.hl7 import (
    parse_oru_r01_message,
    build_ack_message,
    build_oru_r01_message,
)
from app.routes.monitoring import _compute_risk_for_constantes
from app.routes.websocket import manager


router = APIRouter(prefix="/api/hl7", tags=["HL7 Interoperability"])


class HL7JsonRequest(BaseModel):
    raw_hl7: Optional[str] = None
    sejour_id: Optional[int] = None


class HL7GenerateRequest(BaseModel):
    sejour_id: int
    fc: Optional[int] = None
    ta_systolique: Optional[int] = None
    ta_diastolique: Optional[int] = None
    spo2: Optional[int] = None
    temperature: Optional[float] = None
    frequence_respiratoire: Optional[int] = 16
    glasgow: Optional[int] = 15
    douleur: Optional[int] = 0
    rythme_cardiaque: Optional[str] = "sinusal"
    numero_lit: Optional[str] = "BOX-1"


@router.post("/oru-r01", summary="Ingest HL7 v2.5.1 ORU^R01 vital signs observation frame")
async def ingest_hl7_oru_r01(
    request: Request,
    db: Session = Depends(get_db),
    sejour_id_query: Optional[int] = None,
):
    """
    Ingest standard HL7 v2.5.1 ORU^R01 message.
    Accepts raw HL7 text/plain or JSON payload.
    Extracts MSH, PID, PV1, OBR and OBX segments, records vitals,
    computes clinical risk, broadcasts WebSocket event, and returns standard HL7 ACK^R01.
    """
    raw_content = ""
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        try:
            body = await request.json()
            if isinstance(body, dict):
                raw_content = body.get("raw_hl7", "")
                if not sejour_id_query and "sejour_id" in body:
                    sejour_id_query = body["sejour_id"]
            elif isinstance(body, str):
                raw_content = body
        except Exception:
            raw_content = ""
    else:
        body_bytes = await request.body()
        raw_content = body_bytes.decode("utf-8", errors="ignore")

    if not raw_content or not raw_content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contenu HL7 vide ou format invalide",
        )

    parsed = parse_oru_r01_message(raw_content)
    if not parsed.get("success"):
        err_msg = parsed.get("error", "Erreur de parsing HL7")
        ack_err = build_ack_message("UNKNOWN", ack_code="AE", text_message=err_msg)
        return Response(content=ack_err, media_type="text/plain", status_code=400)

    msg_id = parsed["msg_control_id"]
    target_sejour_id = sejour_id_query or parsed.get("sejour_id")

    # If sejour_id is not in message, try locating active patient from bed number (PV1-3)
    if not target_sejour_id and parsed.get("numero_lit"):
        bed_num = parsed["numero_lit"]
        lit_match = (
            db.query(AffectationLit)
            .join(Lit, Lit.lit_id == AffectationLit.lit_id)
            .filter(Lit.numero_lit == bed_num, AffectationLit.heure_fin.is_(None))
            .first()
        )
        if lit_match:
            target_sejour_id = lit_match.sejour_id

    if not target_sejour_id:
        ack_err = build_ack_message(
            msg_id,
            ack_code="AR",
            text_message="Sejour introuvable ou patient non identifie dans le segment PV1/PID",
        )
        return Response(content=ack_err, media_type="text/plain", status_code=404)

    sejour = db.query(Sejour).filter(Sejour.sejour_id == target_sejour_id).first()
    if not sejour:
        ack_err = build_ack_message(
            msg_id,
            ack_code="AR",
            text_message=f"Sejour id={target_sejour_id} inexistant",
        )
        return Response(content=ack_err, media_type="text/plain", status_code=404)

    # Device bridge user or system user
    bridge_user = db.query(Personnel).filter(Personnel.login == "device_bridge").first()
    user_id = bridge_user.personnel_id if bridge_user else None
    if not user_id:
        first_admin = db.query(Personnel).filter(Personnel.role == "admin").first()
        user_id = first_admin.personnel_id if first_admin else None

    v = parsed["vitals"]
    heure_prise = parsed["heure_prise"] or datetime.now(timezone.utc)

    nouvelle = ConstantesVitales(
        sejour_id=target_sejour_id,
        prise_par_id=user_id,
        temperature=v.get("temperature"),
        fc=v.get("fc"),
        ta_systolique=v.get("ta_systolique"),
        ta_diastolique=v.get("ta_diastolique"),
        spo2=v.get("spo2"),
        douleur=v.get("douleur") or 0,
        glasgow=v.get("glasgow") or 15,
        frequence_respiratoire=v.get("frequence_respiratoire") or 16,
        rythme_cardiaque=v.get("rythme_cardiaque") or "sinusal",
        heure_prise=heure_prise,
    )

    db.add(nouvelle)
    db.commit()
    db.refresh(nouvelle)

    # Compute risk with ML models
    risk = _compute_risk_for_constantes(db, target_sejour_id, nouvelle)
    if risk:
        nouvelle.risk_level = risk.get("risk_level")
        nouvelle.risk_confidence = risk.get("confidence")
        db.commit()
        db.refresh(nouvelle)

    # Broadcast event via WebSocket
    await manager.broadcast_event(
        "CONSTANTES_STREAM",
        target_sejour_id,
        {
            "source": "HL7_ORU_R01",
            "sending_app": parsed.get("sending_app", "MONITOR"),
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

    # Build standard HL7 ACK^R01
    ack_response = build_ack_message(
        msg_control_id=msg_id,
        ack_code="AA",
        text_message=f"Constantes vitales enregistrees avec succes pour sejour {target_sejour_id}",
    )

    accept_header = request.headers.get("accept", "")
    if "application/json" in accept_header and "text/plain" not in accept_header:
        return {
            "status": "success",
            "ack_code": "AA",
            "msg_control_id": msg_id,
            "sejour_id": target_sejour_id,
            "vitals_saved": {
                "constante_id": nouvelle.constante_id,
                "fc": nouvelle.fc,
                "spo2": nouvelle.spo2,
                "ta_systolique": nouvelle.ta_systolique,
                "ta_diastolique": nouvelle.ta_diastolique,
                "temperature": nouvelle.temperature,
                "risk_level": nouvelle.risk_level,
            },
            "raw_ack": ack_response,
        }

    return Response(content=ack_response, media_type="text/plain; charset=utf-8")


@router.post("/generate-sample", summary="Helper to build sample HL7 ORU^R01 frame")
def generate_sample_hl7(data: HL7GenerateRequest, db: Session = Depends(get_db)):
    """Utility endpoint to generate a standard compliant HL7 ORU^R01 frame from vitals values."""
    sejour = db.query(Sejour).filter(Sejour.sejour_id == data.sejour_id).first()
    nom = sejour.patient.nom if sejour and sejour.patient else "PATIENT"
    prenom = sejour.patient.prenom if sejour and sejour.patient else "URGENCES"
    patient_id = sejour.patient_id if sejour else 1

    vitals = {
        "fc": data.fc,
        "ta_systolique": data.ta_systolique,
        "ta_diastolique": data.ta_diastolique,
        "spo2": data.spo2,
        "temperature": data.temperature,
        "frequence_respiratoire": data.frequence_respiratoire,
        "glasgow": data.glasgow,
        "douleur": data.douleur,
        "rythme_cardiaque": data.rythme_cardiaque,
    }

    hl7_msg = build_oru_r01_message(
        sejour_id=data.sejour_id,
        vitals=vitals,
        patient_id=patient_id,
        nom_patient=nom,
        prenom_patient=prenom,
        numero_lit=data.numero_lit or "BOX-1",
    )

    return {
        "sejour_id": data.sejour_id,
        "raw_hl7": hl7_msg,
        "formatted_segments": hl7_msg.split("\r"),
    }
