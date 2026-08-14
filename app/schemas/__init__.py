from datetime import datetime
from pydantic import BaseModel, field_validator
from typing import Optional


class LoginRequest(BaseModel):
    login: str
    mot_de_passe: str


class PatientCreate(BaseModel):
    nom: str
    prenom: str
    date_naissance: Optional[str] = None
    sexe: Optional[str] = None
    telephone: Optional[str] = None
    numero_secu: Optional[str] = None


class SejourCreate(BaseModel):
    mode_arrivee: str
    motif_visite: str
    patient_id: Optional[int] = None
    patient_data: Optional[PatientCreate] = None


class TriageCreate(BaseModel):
    sejour_id: int
    soignant_id: int
    score_ccmu: int
    score_french: Optional[int] = 1
    poids: Optional[float] = None
    temperature: Optional[float] = None
    fc: Optional[int] = None
    ta_systolique: Optional[int] = None
    ta_diastolique: Optional[int] = None
    spo2: Optional[float] = None
    glasgow: Optional[int] = None
    glasgow_e: Optional[int] = None
    glasgow_v: Optional[int] = None
    glasgow_m: Optional[int] = None
    douleur: Optional[int] = None
    notes: Optional[str] = None
    zone: Optional[str] = None

    @field_validator("score_ccmu")
    @classmethod
    def validate_ccmu(cls, v):
        if v not in [1, 2, 3, 4, 5]:
            raise ValueError("score_ccmu doit être entre 1 et 5")
        return v

    @field_validator("douleur")
    @classmethod
    def validate_douleur(cls, v):
        if v is not None and not (0 <= v <= 10):
            raise ValueError("douleur doit être entre 0 et 10")
        return v

    @field_validator("spo2")
    @classmethod
    def validate_spo2(cls, v):
        if v is not None and not (0 <= v <= 100):
            raise ValueError("spo2 doit être entre 0 et 100")
        return v


class SortieCreate(BaseModel):
    diagnostic_sortie: str
    mode_sortie: str
    courrier_sortie: str
    sortie_administrative: Optional[bool] = False


class ExamenCreate(BaseModel):
    sejour_id: int
    prescripteur_id: int
    type_examen: str


class ExamenUpdate(BaseModel):
    resultat: str
    statut: str


class LitStatutUpdate(BaseModel):
    statut: str


class AffectationCreate(BaseModel):
    lit_id: int
    sejour_id: int


class TransfertCreate(BaseModel):
    sejour_id: int
    nouveau_lit_id: int


class ObservationCreate(BaseModel):
    sejour_id: int
    auteur_id: int
    texte: str


class PrescriptionCreate(BaseModel):
    sejour_id: int
    prescripteur_id: int
    medicament: str
    dose: str


class PersonnelCreate(BaseModel):
    nom: str
    prenom: str
    login: str
    mot_de_passe: str
    role: str


# ============================================================================
# Dossier Préhospitalier - SAMU/SMUR Integration
# ============================================================================

class DossierPrehospitalierCreate(BaseModel):
    numero_samu: str
    heure_appel_samu: str  # Format: "YYYY-MM-DD HH:MM:SS"
    heure_depart_smur: Optional[str] = None
    heure_arrivee_site: Optional[str] = None
    heure_depart_site: Optional[str] = None
    heure_arrivee_hopital: Optional[str] = None
    
    # Équipe SMUR
    medecin_smur: Optional[str] = None
    infirmier_smur: Optional[str] = None
    ambulancier_smur: Optional[str] = None
    vehicule_smur: Optional[str] = None
    
    # Données préhospitalières
    motif_appel: str
    contexte: Optional[str] = None
    antecedents: Optional[str] = None
    traitement_en_cours: Optional[str] = None
    allergies: Optional[str] = None
    
    # Constantes préhospitalières
    ta_prehospitaliere: Optional[str] = None
    fc_prehospitaliere: Optional[int] = None
    spo2_prehospitaliere: Optional[float] = None
    temperature_prehospitaliere: Optional[float] = None
    glycemie_prehospitaliere: Optional[float] = None
    glasgow_prehospitaliere: Optional[int] = None
    glasgow_e_prehospitaliere: Optional[int] = None
    glasgow_v_prehospitaliere: Optional[int] = None
    glasgow_m_prehospitaliere: Optional[int] = None
    douleur_prehospitaliere: Optional[int] = None
    
    # ECG et monitoring
    rythme_cardiaque: Optional[str] = None
    anomalies_ecg: Optional[str] = None
    monitoring: Optional[dict] = None
    
    # Traitements préhospitaliers
    traitements_prehospitaliers: Optional[dict] = None
    gestes_techniques: Optional[dict] = None
    
    # Transmissions
    transmissions_medecin: Optional[str] = None
    transmissions_infirmier: Optional[str] = None
    transmissions_ambulancier: Optional[str] = None
    
    # Statut et métadonnées
    priorite_samu: str  # URGENCE_VITALE, URGENCE_ABSOLUE, URGENCE_RELATIVE
    patient_nom: Optional[str] = None
    patient_prenom: Optional[str] = None
    patient_date_naissance: Optional[str] = None
    patient_sexe: Optional[str] = None


class DossierPrehospitalierUpdate(BaseModel):
    heure_depart_smur: Optional[str] = None
    heure_arrivee_site: Optional[str] = None
    heure_depart_site: Optional[str] = None
    heure_arrivee_hopital: Optional[str] = None
    
    # Constantes mises à jour
    ta_prehospitaliere: Optional[str] = None
    fc_prehospitaliere: Optional[int] = None
    spo2_prehospitaliere: Optional[float] = None
    temperature_prehospitaliere: Optional[float] = None
    glycemie_prehospitaliere: Optional[float] = None
    glasgow_prehospitaliere: Optional[int] = None
    douleur_prehospitaliere: Optional[int] = None
    
    # Traitements supplémentaires
    traitements_prehospitaliers: Optional[dict] = None
    gestes_techniques: Optional[dict] = None
    
    # Transmissions
    transmissions_medecin: Optional[str] = None
    transmissions_infirmier: Optional[str] = None
    transmissions_ambulancier: Optional[str] = None
    
    # Statut
    statut: Optional[str] = None  # PRÉ-ALERTE, EN ROUTE, ARRIVÉ, FUSIONNÉ


class DossierPrehospitalierRead(BaseModel):
    dossier_id: int
    sejour_id: Optional[int]
    patient_id: Optional[int]
    numero_samu: str
    heure_appel_samu: datetime
    heure_depart_smur: Optional[datetime]
    heure_arrivee_site: Optional[datetime]
    heure_depart_site: Optional[datetime]
    heure_arrivee_hopital: Optional[datetime]
    medecin_smur: Optional[str]
    infirmier_smur: Optional[str]
    ambulancier_smur: Optional[str]
    vehicule_smur: Optional[str]
    motif_appel: str
    contexte: Optional[str]
    antecedents: Optional[str]
    traitement_en_cours: Optional[str]
    allergies: Optional[str]
    ta_prehospitaliere: Optional[str]
    fc_prehospitaliere: Optional[int]
    spo2_prehospitaliere: Optional[float]
    temperature_prehospitaliere: Optional[float]
    glycemie_prehospitaliere: Optional[float]
    glasgow_prehospitaliere: Optional[int]
    glasgow_e_prehospitaliere: Optional[int]
    glasgow_v_prehospitaliere: Optional[int]
    glasgow_m_prehospitaliere: Optional[int]
    douleur_prehospitaliere: Optional[int]
    rythme_cardiaque: Optional[str]
    anomalies_ecg: Optional[str]
    monitoring: Optional[dict]
    traitements_prehospitaliers: Optional[dict]
    gestes_techniques: Optional[dict]
    transmissions_medecin: Optional[str]
    transmissions_infirmier: Optional[str]
    transmissions_ambulancier: Optional[str]
    statut: str
    priorite_samu: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Constantes Vitales - Monitoring
# ============================================================================


class ConstanteCreate(BaseModel):
    sejour_id: Optional[int] = None
    temperature: Optional[float] = None
    fc: Optional[int] = None
    ta_systolique: Optional[int] = None
    ta_diastolique: Optional[int] = None
    spo2: Optional[int] = None
    douleur: Optional[int] = None
    glasgow: Optional[int] = None
    frequence_respiratoire: Optional[int] = None
    rythme_cardiaque: Optional[str] = None

    @field_validator("douleur")
    @classmethod
    def validate_douleur(cls, v):
        if v is not None and not (0 <= v <= 10):
            raise ValueError("douleur doit être entre 0 et 10")
        return v

    @field_validator("glasgow")
    @classmethod
    def validate_glasgow(cls, v):
        if v is not None and not (3 <= v <= 15):
            raise ValueError("glasgow doit être entre 3 et 15")
        return v


class ConstanteRead(BaseModel):
    constante_id: int
    sejour_id: int
    prise_par_id: Optional[int] = None
    heure_prise: datetime
    temperature: Optional[float] = None
    fc: Optional[int] = None
    ta_systolique: Optional[int] = None
    ta_diastolique: Optional[int] = None
    spo2: Optional[int] = None
    douleur: Optional[int] = None
    glasgow: Optional[int] = None
    frequence_respiratoire: Optional[int] = None
    rythme_cardiaque: Optional[str] = None
    risk_level: Optional[str] = None
    risk_confidence: Optional[float] = None

    model_config = {"from_attributes": True}
