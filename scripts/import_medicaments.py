"""
Import script for the Base de Données Publique des Médicaments.
Downloads CIS_bdpm.txt from ANSM and imports into SQLite.

Usage: python3 scripts/import_medicaments.py
"""
import csv
import io
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import urllib.request
from app.models.base import Base, engine, SessionLocal
from app.models.medicament import Medicament

BDPM_URL = "https://base-donnees-publique.medicaments.gouv.fr/download/file/CIS_bdpm.txt"


def download_data(url: str) -> str:
    print(f"Téléchargement depuis {url}...")
    with urllib.request.urlopen(url) as resp:
        data = resp.read().decode("latin-1")
    print(f"  {len(data)} caractères reçus")
    return data


def parse_and_import(text: str):
    reader = csv.reader(io.StringIO(text), delimiter="\t")
    db = SessionLocal()
    try:
        total = 0
        inserted = 0
        skipped = 0
        batch = []

        for row in reader:
            total += 1
            if not row or not row[0].strip():
                continue
            cis_code = row[0].strip()
            denomination = row[1].strip() if len(row) > 1 else ""
            forme = row[2].strip() if len(row) > 2 else ""
            voie = row[3].strip() if len(row) > 3 else ""
            statut = row[4].strip() if len(row) > 4 else ""
            etat_com = row[6].strip() if len(row) > 6 else ""
            titulaire = row[10].strip() if len(row) > 10 else ""
            surv = row[11].strip() if len(row) > 11 else ""

            existing = db.query(Medicament).filter(Medicament.cis_code == cis_code).first()
            if existing:
                skipped += 1
                continue

            m = Medicament(
                cis_code=cis_code,
                nom=denomination,
                forme=forme,
                voie_administration=voie,
                statut_amm=statut,
                etat_commercialisation=etat_com,
                titulaire=titulaire,
                surveillance_renforcee=surv,
            )
            batch.append(m)

            if len(batch) >= 500:
                db.add_all(batch)
                db.commit()
                inserted += len(batch)
                batch = []

        if batch:
            db.add_all(batch)
            db.commit()
            inserted += len(batch)

        print(f"\nRésumé : {total} lignes lues, {inserted} insérées, {skipped} déjà existantes")
    finally:
        db.close()


def main():
    Base.metadata.create_all(bind=engine)
    text = download_data(BDPM_URL)
    parse_and_import(text)
    print("Import terminé avec succès.")


if __name__ == "__main__":
    main()
