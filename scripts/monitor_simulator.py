#!/usr/bin/env python3
"""
Simulateur de flux continu pour moniteurs multiparamétriques connectés (HL7 v2.5.1 ORU^R01).

Détecte tous les patients installés dans des lits et émet périodiquement
des trames d'observation HL7 v2 ORU^R01 standardisées vers l'API Urgences OS.

Usage:
    python3 scripts/monitor_simulator.py

Prérequis:
    - Backend FastAPI tourne sur http://127.0.0.1:8000
    - Compte device_bridge créé (seed_device_bridge.py)
    - Au moins un patient installé dans un lit (affectation active)
"""
import asyncio
import os
import random
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.models import AffectationLit, Lit
from app.models.base import SessionLocal
from app.utils.hl7 import build_oru_r01_message

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
TOKEN = os.getenv("DEVICE_BRIDGE_TOKEN", "device_bridge_token_2026")
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "text/plain; charset=utf-8",
    "Accept": "text/plain",
}

PROFILS = [
    {"fc": 75, "ta_sys": 120, "ta_dia": 80, "spo2": 98, "temp": 37.0, "fr": 16, "nom": "stable"},
    {"fc": 88, "ta_sys": 110, "ta_dia": 70, "spo2": 96, "temp": 37.5, "fr": 18, "nom": "tachycarde"},
    {"fc": 105, "ta_sys": 100, "ta_dia": 65, "spo2": 94, "temp": 38.2, "fr": 22, "nom": "critique"},
    {"fc": 65, "ta_sys": 130, "ta_dia": 85, "spo2": 99, "temp": 36.8, "fr": 14, "nom": "stable"},
    {"fc": 55, "ta_sys": 140, "ta_dia": 90, "spo2": 97, "temp": 36.5, "fr": 12, "nom": "bradycarde"},
]

STATS = {"ok": 0, "fail": 0, "last_log": 0.0}


def get_installed_patients():
    """Récupère les lits occupés avec sejour_id."""
    db = SessionLocal()
    try:
        results = (
            db.query(Lit, AffectationLit)
            .join(AffectationLit, Lit.lit_id == AffectationLit.lit_id)
            .filter(AffectationLit.heure_fin.is_(None))
            .all()
        )
        return [
            {"numero_lit": lit.numero_lit, "sejour_id": aff.sejour_id, "lit_id": lit.lit_id}
            for lit, aff in results
        ]
    finally:
        db.close()


def generate_vitals(profil):
    """Génère un jeu de constantes avec bruit gaussien, clamping aux bornes cliniques."""
    return {
        "fc": max(30, min(220, int(profil["fc"] + random.gauss(0, 5)))),
        "ta_systolique": max(60, min(250, int(profil["ta_sys"] + random.gauss(0, 10)))),
        "ta_diastolique": max(30, min(150, int(profil["ta_dia"] + random.gauss(0, 5)))),
        "spo2": max(70, min(100, int(profil["spo2"] + random.gauss(0, 1)))),
        "temperature": round(max(34.0, min(42.0, profil["temp"] + random.gauss(0, 0.2))), 1),
        "frequence_respiratoire": max(6, min(40, int(profil["fr"] + random.gauss(0, 2)))),
        "glasgow": 15,
        "douleur": 0,
        "rythme_cardiaque": "sinusal",
    }


async def simulate_one_lit(numero_lit, sejour_id, index):
    """Boucle infinie pour un lit envoyant des trames HL7 ORU^R01 standardisées."""
    profil = PROFILS[index % len(PROFILS)]
    print(f"  [{numero_lit}] sejour_id={sejour_id} profil={profil['nom']} (Mode HL7 ORU^R01)")
    async with httpx.AsyncClient() as client:
        while True:
            vitals = generate_vitals(profil)
            hl7_frame = build_oru_r01_message(
                sejour_id=sejour_id,
                vitals=vitals,
                numero_lit=numero_lit,
                sending_app="MONITOR_PHILIPS_MP50",
            )
            try:
                r = await client.post(
                    f"{API_URL}/api/hl7/oru-r01",
                    content=hl7_frame,
                    headers=HEADERS,
                    timeout=5,
                )
                if r.status_code == 200:
                    STATS["ok"] += 1
                elif r.status_code == 401:
                    print(f"  [!!] Token invalide ou expiré. Arrêt du simulateur.")
                    return
                else:
                    STATS["fail"] += 1
                    if r.status_code == 404:
                        print(f"  [{numero_lit}] Patient sorti (404), arrêt.")
                        return
            except httpx.ConnectError:
                STATS["fail"] += 1
                print(f"  [!] Backend inaccessible, reconnexion dans 10s...")
                await asyncio.sleep(10)
                continue
            except httpx.TimeoutException:
                STATS["fail"] += 1
                await asyncio.sleep(5)
                continue

            now = asyncio.get_event_loop().time()
            if now - STATS["last_log"] >= 60:
                total = STATS["ok"] + STATS["fail"]
                pct = 100 * STATS["ok"] / total if total else 0
                print(f"  ═══ Résumé [{numero_lit}] — {STATS['ok']} trames HL7 transmises / {STATS['fail']} échecs ({pct:.1f}%)")
                STATS["last_log"] = now

            await asyncio.sleep(5 + random.uniform(-1, 2))


async def main():
    """Boucle principale avec re-scan périodique des patients installés."""
    print("=== Passerelle & Simulateur Monitoring Multiparamétrique (HL7 v2.5.1 ORU^R01) ===")
    print(f"API Passerelle : {API_URL}/api/hl7/oru-r01")
    tasks = {}

    try:
        while True:
            patients = get_installed_patients()
            current_ids = {p["sejour_id"] for p in patients}

            for sid in list(tasks.keys()):
                if sid not in current_ids:
                    print(f"  [!] Patient sejour_id={sid} libéré, arrêt du flux HL7")
                    tasks[sid].cancel()
                    del tasks[sid]

            for i, p in enumerate(patients):
                if p["sejour_id"] not in tasks:
                    print(f"  [+] Nouveau flux HL7 : {p['numero_lit']} → sejour_id={p['sejour_id']}")
                    tasks[p["sejour_id"]] = asyncio.create_task(
                        simulate_one_lit(p["numero_lit"], p["sejour_id"], i)
                    )

            if not tasks:
                print("  Aucun patient installé. Attente 30s...")
            else:
                print(f"  {len(tasks)} lit(s) actif(s) — prochain re-scan dans 30s")

            await asyncio.sleep(30)
    except asyncio.CancelledError:
        print("Arrêt du simulateur.")
        for t in tasks.values():
            t.cancel()


if __name__ == "__main__":
    print("Lancer avec : python3 scripts/monitor_simulator.py")
    print("(back-end FastAPI doit tourner sur http://127.0.0.1:8000)")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSimulateur arrêté.")
