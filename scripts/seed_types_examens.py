import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.base import Base, engine, SessionLocal
from app.models.type_examen import TypeExamen

EXAMENS = [
    # Imagerie
    ("Radiographie thoracique", "imagerie"),
    ("Radiographie abdominale", "imagerie"),
    ("Radiographie osseuse", "imagerie"),
    ("Scanner cérébral", "imagerie"),
    ("Scanner thoracique", "imagerie"),
    ("Scanner abdominal", "imagerie"),
    ("IRM cérébrale", "imagerie"),
    ("IRM médullaire", "imagerie"),
    ("Échographie abdominale", "imagerie"),
    ("Échographie cardiaque", "imagerie"),
    ("Écho-Doppler vasculaire", "imagerie"),
    ("Angiographie", "imagerie"),
    # Biologie
    ("NFS (Numération Formule Sanguine)", "biologie"),
    ("Bilan de coagulation", "biologie"),
    ("Ionogramme sanguin", "biologie"),
    ("Bilan rénal (urée, créatinine)", "biologie"),
    ("Bilan hépatique", "biologie"),
    ("Troponine", "biologie"),
    ("D-dimères", "biologie"),
    ("Gaz du sang artériel", "biologie"),
    ("Lactates", "biologie"),
    ("CRP (Protéine C réactive)", "biologie"),
    ("Procalcitonine (PCT)", "biologie"),
    ("Hémocultures", "biologie"),
    ("BU (Bandelette Urinaire)", "biologie"),
    ("ECBU (Examen Cytobactériologique des Urines)", "biologie"),
    # Fonctionnel
    ("ECG (Électrocardiogramme)", "fonctionnel"),
    ("EEG (Électroencéphalogramme)", "fonctionnel"),
    ("EFR (Épreuves Fonctionnelles Respiratoires)", "fonctionnel"),
    ("Holter ECG", "fonctionnel"),
    ("Holter TA", "fonctionnel"),
    # Gestes techniques
    ("PL (Ponction Lombaire)", "geste"),
    ("Ponction pleurale", "geste"),
    ("Ponction d'ascite", "geste"),
    ("Ponction articulaire", "geste"),
    ("Sondage vésical", "geste"),
    ("Sondage nasogastrique", "geste"),
    ("Pose de voie veineuse centrale", "geste"),
    ("Intubation", "geste"),
    ("Massage cardiaque", "geste"),
]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        count = 0
        for nom, categorie in EXAMENS:
            existing = db.query(TypeExamen).filter(TypeExamen.nom == nom).first()
            if not existing:
                db.add(TypeExamen(nom=nom, categorie=categorie))
                count += 1
        db.commit()
        print(f"{count} types d'examens insérés (total: {len(EXAMENS)} dans la liste)")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
