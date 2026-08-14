# -*- coding: utf-8 -*-
"""
HL7 v2.5.1 Parser & Builder for Medical Monitoring (ORU^R01).

Implements standard HL7 v2 messaging for vital signs observations:
- MSH: Message Header
- PID: Patient Identification
- PV1: Patient Visit (Sejour / Bed location)
- OBR: Observation Request
- OBX: Observation Result Segments (LOINC codes for vitals)
- ACK: Standard Application Acknowledgment (ACK^R01)
"""
from datetime import datetime, timezone
import random
import re
from typing import Dict, Any, Optional


# Standard LOINC & Medical Identifiers mapping
LOINC_MAP = {
    # Heart Rate
    "8867-4": "fc",
    "HR": "fc",
    "FC": "fc",
    "PULSE": "fc",
    # Systolic Blood Pressure
    "8480-6": "ta_systolique",
    "SBP": "ta_systolique",
    "TAS": "ta_systolique",
    "TA_SYS": "ta_systolique",
    # Diastolic Blood Pressure
    "8462-4": "ta_diastolique",
    "DBP": "ta_diastolique",
    "TAD": "ta_diastolique",
    "TA_DIA": "ta_diastolique",
    # Oxygen Saturation (SpO2)
    "2708-6": "spo2",
    "59408-5": "spo2",
    "SPO2": "spo2",
    "SAO2": "spo2",
    # Body Temperature
    "8310-5": "temperature",
    "TEMP": "temperature",
    "TEMPERATURE": "temperature",
    # Respiratory Rate
    "9279-1": "frequence_respiratoire",
    "RR": "frequence_respiratoire",
    "FR": "frequence_respiratoire",
    "RESP": "frequence_respiratoire",
    # Glasgow Coma Scale
    "35088-4": "glasgow",
    "GCS": "glasgow",
    "GLASGOW": "glasgow",
    # Pain EVA Score
    "38208-5": "douleur",
    "EVA": "douleur",
    "PAIN": "douleur",
    "DOULEUR": "douleur",
    # Cardiac Rhythm
    "8884-9": "rythme_cardiaque",
    "RHYTHM": "rythme_cardiaque",
    "RYTHME": "rythme_cardiaque",
}


def format_hl7_timestamp(dt: Optional[datetime] = None) -> str:
    """Format datetime to HL7 timestamp (YYYYMMDDHHMMSS)."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%Y%m%d%H%M%S")


def parse_hl7_timestamp(ts_str: str) -> Optional[datetime]:
    """Parse HL7 timestamp string into UTC datetime."""
    if not ts_str:
        return None
    clean = re.sub(r"[^0-9]", "", ts_str)
    try:
        if len(clean) >= 14:
            return datetime.strptime(clean[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        elif len(clean) >= 12:
            return datetime.strptime(clean[:12], "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
        elif len(clean) >= 8:
            return datetime.strptime(clean[:8], "%Y%m%d").replace(tzinfo=timezone.utc)
    except Exception:
        pass
    return None


def random_suffix() -> str:
    return f"{random.randint(100, 999)}"


def build_oru_r01_message(
    sejour_id: int,
    vitals: Dict[str, Any],
    patient_id: Optional[int] = None,
    nom_patient: str = "PATIENT",
    prenom_patient: str = "URGENCES",
    numero_lit: str = "BOX-1",
    sending_app: str = "MONITOR_PHILIPS_MP50",
    sending_facility: str = "URGENCES_OS",
    msg_control_id: Optional[str] = None,
) -> str:
    """
    Build a standard HL7 v2.5.1 ORU^R01 observation message from vitals dictionary.
    """
    now_str = format_hl7_timestamp()
    if not msg_control_id:
        msg_control_id = f"MSG{now_str}{random_suffix()}"

    # MSH - Message Header
    msh = f"MSH|^~\\&|{sending_app}|{sending_facility}|URGENCES_SERVER|CHU_HOSPITAL|{now_str}||ORU^R01|{msg_control_id}|P|2.5.1"

    # PID - Patient Identification
    pid_id = f"PAT_{patient_id}" if patient_id else f"SEJ_{sejour_id}"
    pid = f"PID|1||{pid_id}^^^URGENCES||{nom_patient}^{prenom_patient}|||U"

    # PV1 - Patient Visit (Contains Sejour ID in PV1-19 and Bed in PV1-3)
    pv1 = f"PV1|1|E|{numero_lit}^URGENCES|||||||||||||||SEJ_{sejour_id}"

    # OBR - Observation Request
    obr = f"OBR|1||MON_{msg_control_id}|VITAL_SIGNS_PANEL^Vital Signs Monitoring^LN|||{now_str}"

    # OBX Segments
    obx_list = []
    idx = 1

    # FC / Heart Rate
    if "fc" in vitals and vitals["fc"] is not None:
        val = vitals["fc"]
        obx_list.append(f"OBX|{idx}|NM|8867-4^Heart rate^LN||{val}|/min|60-100|N|||F")
        idx += 1

    # TA Systolique
    if "ta_systolique" in vitals and vitals["ta_systolique"] is not None:
        val = vitals["ta_systolique"]
        obx_list.append(f"OBX|{idx}|NM|8480-6^Systolic blood pressure^LN||{val}|mm[Hg]|90-140|N|||F")
        idx += 1

    # TA Diastolique
    if "ta_diastolique" in vitals and vitals["ta_diastolique"] is not None:
        val = vitals["ta_diastolique"]
        obx_list.append(f"OBX|{idx}|NM|8462-4^Diastolic blood pressure^LN||{val}|mm[Hg]|60-90|N|||F")
        idx += 1

    # SpO2
    if "spo2" in vitals and vitals["spo2"] is not None:
        val = vitals["spo2"]
        obx_list.append(f"OBX|{idx}|NM|2708-6^Oxygen saturation in Arterial blood^LN||{val}|%|95-100|N|||F")
        idx += 1

    # Temperature
    if "temperature" in vitals and vitals["temperature"] is not None:
        val = vitals["temperature"]
        obx_list.append(f"OBX|{idx}|NM|8310-5^Body temperature^LN||{val}|Cel|36.0-37.5|N|||F")
        idx += 1

    # Fréquence Respiratoire
    if "frequence_respiratoire" in vitals and vitals["frequence_respiratoire"] is not None:
        val = vitals["frequence_respiratoire"]
        obx_list.append(f"OBX|{idx}|NM|9279-1^Respiratory rate^LN||{val}|/min|12-20|N|||F")
        idx += 1

    # Glasgow
    if "glasgow" in vitals and vitals["glasgow"] is not None:
        val = vitals["glasgow"]
        obx_list.append(f"OBX|{idx}|NM|35088-4^Glasgow Coma Scale total score^LN||{val}|score|3-15|N|||F")
        idx += 1

    # Douleur EVA
    if "douleur" in vitals and vitals["douleur"] is not None:
        val = vitals["douleur"]
        obx_list.append(f"OBX|{idx}|NM|38208-5^Pain severity - 0-10 verbal scale^LN||{val}|score|0-10|N|||F")
        idx += 1

    # Rythme Cardiaque
    if "rythme_cardiaque" in vitals and vitals["rythme_cardiaque"] is not None:
        val = vitals["rythme_cardiaque"]
        obx_list.append(f"OBX|{idx}|ST|8884-9^Heart rate rhythm^LN||{val}|||N|||F")
        idx += 1

    segments = [msh, pid, pv1, obr] + obx_list
    return "\r".join(segments)


def parse_oru_r01_message(raw_msg: str) -> Dict[str, Any]:
    """
    Parse a raw HL7 v2.x ORU^R01 message string.
    """
    if not raw_msg or not raw_msg.strip():
        return {"success": False, "error": "Message HL7 vide"}

    # Normalize line breaks
    normalized = raw_msg.replace("\r\n", "\r").replace("\n", "\r")
    raw_segments = [s.strip() for s in normalized.split("\r") if s.strip()]

    if not raw_segments:
        return {"success": False, "error": "Aucun segment HL7 trouvé"}

    msg_control_id = ""
    message_type = "ORU^R01"
    sending_app = ""
    sejour_id = None
    patient_id = None
    numero_lit = None
    heure_prise = None
    vitals: Dict[str, Any] = {
        "fc": None,
        "ta_systolique": None,
        "ta_diastolique": None,
        "spo2": None,
        "temperature": None,
        "frequence_respiratoire": None,
        "glasgow": 15,
        "douleur": 0,
        "rythme_cardiaque": "sinusal",
    }

    for seg in raw_segments:
        fields = seg.split("|")
        seg_type = fields[0].upper()

        if seg_type == "MSH":
            # MSH-3: Sending App, MSH-7: Date/Time, MSH-9: Message Type, MSH-10: Control ID
            if len(fields) > 2:
                sending_app = fields[2]
            if len(fields) > 6:
                heure_prise = parse_hl7_timestamp(fields[6])
            if len(fields) > 8:
                message_type = fields[8]
            if len(fields) > 9:
                msg_control_id = fields[9]

        elif seg_type == "PID":
            # PID-3: Patient Identifier
            if len(fields) > 3 and fields[3]:
                raw_pid = fields[3].split("^")[0]
                patient_id = raw_pid
                if raw_pid.startswith("SEJ_"):
                    try:
                        sejour_id = int(raw_pid.replace("SEJ_", ""))
                    except ValueError:
                        pass

        elif seg_type == "PV1":
            # PV1-3: Assigned Patient Location
            if len(fields) > 3 and fields[3]:
                numero_lit = fields[3].split("^")[0]
            # PV1-19: Visit Number / Sejour ID
            if len(fields) > 19 and fields[19]:
                raw_visit = fields[19].split("^")[0]
                clean_visit = re.sub(r"[^0-9]", "", raw_visit)
                if clean_visit:
                    try:
                        sejour_id = int(clean_visit)
                    except ValueError:
                        pass

        elif seg_type == "OBX":
            # OBX-3: Observation Identifier (Code^Name^CodingSystem)
            # OBX-5: Observation Value
            if len(fields) > 5 and fields[5] != "":
                obs_id_field = fields[3] if len(fields) > 3 else ""
                obs_val_field = fields[5]

                sub_parts = obs_id_field.split("^")
                code_primary = sub_parts[0].upper().strip()
                code_name = sub_parts[1].upper().strip() if len(sub_parts) > 1 else ""

                target_key = None
                if code_primary in LOINC_MAP:
                    target_key = LOINC_MAP[code_primary]
                elif code_name in LOINC_MAP:
                    target_key = LOINC_MAP[code_name]
                else:
                    for alias, mapped in LOINC_MAP.items():
                        if alias in code_primary or alias in code_name:
                            target_key = mapped
                            break

                if target_key:
                    try:
                        if target_key in ["fc", "ta_systolique", "ta_diastolique", "spo2", "frequence_respiratoire", "glasgow", "douleur"]:
                            vitals[target_key] = int(float(obs_val_field))
                        elif target_key == "temperature":
                            vitals[target_key] = round(float(obs_val_field), 1)
                        elif target_key == "rythme_cardiaque":
                            vitals[target_key] = str(obs_val_field).strip().lower()
                    except (ValueError, TypeError):
                        pass

    if vitals["frequence_respiratoire"] is None:
        vitals["frequence_respiratoire"] = 16
    if vitals["glasgow"] is None:
        vitals["glasgow"] = 15
    if vitals["douleur"] is None:
        vitals["douleur"] = 0
    if not vitals["rythme_cardiaque"]:
        vitals["rythme_cardiaque"] = "sinusal"

    return {
        "success": True,
        "msg_control_id": msg_control_id or f"MSG{format_hl7_timestamp()}",
        "message_type": message_type,
        "sending_app": sending_app,
        "sejour_id": sejour_id,
        "patient_id": patient_id,
        "numero_lit": numero_lit,
        "heure_prise": heure_prise or datetime.now(timezone.utc),
        "vitals": vitals,
        "raw_segments_count": len(raw_segments),
    }


def build_ack_message(
    msg_control_id: str,
    ack_code: str = "AA",
    text_message: str = "Message processed successfully",
    receiving_app: str = "URGENCES_SERVER",
    receiving_facility: str = "CHU_HOSPITAL",
) -> str:
    """
    Build a standard HL7 ACK message for ORU^R01.
    """
    now_str = format_hl7_timestamp()
    ack_id = f"ACK{now_str}{random_suffix()}"

    msh = f"MSH|^~\\&|{receiving_app}|{receiving_facility}|MONITOR|URGENCES_OS|{now_str}||ACK^R01|{ack_id}|P|2.5.1"
    msa = f"MSA|{ack_code}|{msg_control_id}|{text_message}"

    return f"{msh}\r{msa}"
