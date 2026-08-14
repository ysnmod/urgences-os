import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models import Base, engine, Interaction, SessionLocal

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "interactions.csv"


def seed_interactions():
    if not DATA_PATH.exists():
        print(f"Fichier introuvable: {DATA_PATH}")
        return

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    total = 0
    try:
        with open(DATA_PATH, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                drug_a = (row.get("drug_a") or "").strip()
                drug_b = (row.get("drug_b") or "").strip()
                niveau = (row.get("niveau") or "modéré").strip()
                description = (row.get("description") or "").strip()
                if not drug_a or not drug_b:
                    continue
                db.add(Interaction(
                    drug_a=drug_a,
                    drug_b=drug_b,
                    niveau=niveau,
                    description=description,
                ))
                total += 1
        db.commit()
        print(f"{total} interactions insérées depuis {DATA_PATH}")
    except Exception as e:
        db.rollback()
        print(f"Erreur: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_interactions()
