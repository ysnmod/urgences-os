from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float, JSON, Boolean
from sqlalchemy.orm import relationship
from app.models.base import Base


class DossierPrehospitalier(Base):
    __tablename__ = "dossier_prehospitalier"
    
    dossier_id = Column(Integer, primary_key=True, autoincrement=True)
    sejour_id = Column(Integer, ForeignKey("sejour.sejour_id"), nullable=True)
    patient_id = Column(Integer, ForeignKey("patient.patient_id"), nullable=True)
    
    # Données SAMU/SMUR
    numero_samu = Column(String(50), unique=True, index=True)
    heure_appel_samu = Column(DateTime)
    heure_depart_smur = Column(DateTime)
    heure_arrivee_site = Column(DateTime)
    heure_depart_site = Column(DateTime)
    heure_arrivee_hopital = Column(DateTime)
    
    # Équipe SMUR
    medecin_smur = Column(String(100))
    infirmier_smur = Column(String(100))
    ambulancier_smur = Column(String(100))
    vehicule_smur = Column(String(50))
    
    # Données préhospitalières
    motif_appel = Column(Text)
    contexte = Column(Text)
    antecedents = Column(Text)
    traitement_en_cours = Column(Text)
    allergies = Column(Text)
    
    # Constantes préhospitalières
    ta_prehospitaliere = Column(String(20))
    fc_prehospitaliere = Column(Integer)
    spo2_prehospitaliere = Column(Float)
    temperature_prehospitaliere = Column(Float)
    glycemie_prehospitaliere = Column(Float)
    glasgow_prehospitaliere = Column(Integer)
    glasgow_e_prehospitaliere = Column(Integer)
    glasgow_v_prehospitaliere = Column(Integer)
    glasgow_m_prehospitaliere = Column(Integer)
    douleur_prehospitaliere = Column(Integer)
    
    # ECG et monitoring
    rythme_cardiaque = Column(String(50))
    anomalies_ecg = Column(Text)
    monitoring = Column(JSON)
    
    # Traitements préhospitaliers
    traitements_prehospitaliers = Column(JSON)
    gestes_techniques = Column(JSON)
    
    # Transmissions
    transmissions_medecin = Column(Text)
    transmissions_infirmier = Column(Text)
    transmissions_ambulancier = Column(Text)
    
    # Statut et métadonnées
    statut = Column(String(50), default="PRÉ-ALERTE")  # PRÉ-ALERTE, EN ROUTE, ARRIVÉ, FUSIONNÉ
    priorite_samu = Column(String(50))  # URGENCE_VITALE, URGENCE_ABSOLUE, URGENCE_RELATIVE
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relations
    sejour = relationship("Sejour", backref="dossier_prehospitalier")
    patient = relationship("Patient", backref="dossiers_prehospitaliers")
    
    def __repr__(self):
        return f"<DossierPrehospitalier {self.dossier_id} - {self.numero_samu}>"