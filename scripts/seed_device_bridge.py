#!/usr/bin/env python3
"""
Seed the device_bridge machine account for the monitor simulator.

Creates a non-human user with a long-lived token so the simulator
can POST vitals without interactive login.

Usage:
    python3 scripts/seed_device_bridge.py

Requires:
    - Backend DB to exist (run create_tables first or just run.py once)
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models import Personnel, SessionToken, Base
from app.models.base import engine, SessionLocal
from datetime import datetime, timezone

TOKEN_VALUE = os.getenv("DEVICE_BRIDGE_TOKEN", "device_bridge_token_2026")


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(Personnel).filter(Personnel.login == "device_bridge").first()
        if not user:
            user = Personnel(
                login="device_bridge",
                nom="Device",
                prenom="Bridge",
                role="admin",
                actif=True,
            )
            db.add(user)
            db.flush()
            print("Compte device_bridge créé.")
        else:
            print("Compte device_bridge existe déjà.")

        existing = (
            db.query(SessionToken)
            .filter(SessionToken.personnel_id == user.personnel_id, SessionToken.actif == True)
            .first()
        )
        if not existing:
            token = SessionToken(
                personnel_id=user.personnel_id,
                token=TOKEN_VALUE,
                expire_le=datetime(2027, 12, 31, tzinfo=timezone.utc),
                actif=True,
            )
            db.add(token)
            db.commit()
            print(f"Token créé : {TOKEN_VALUE}")
        else:
            print("Token actif existe déjà.")
        db.close()
    except Exception as e:
        db.close()
        print(f"Erreur : {e}")
        sys.exit(1)


if __name__ == "__main__":
    seed()
