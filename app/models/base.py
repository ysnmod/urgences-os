from pathlib import Path
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Date,
    DateTime,
    Text,
    ForeignKey,
    Boolean,
    Float,
    inspect,
    text,
)
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SQLALCHEMY_DATABASE_URL = f"sqlite:///{BASE_DIR / 'urgences.db'}"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def upgrade_database():
    """Add missing columns to existing database"""
    inspector = inspect(engine)

    columns = [col["name"] for col in inspector.get_columns("triage")]
    if "zone" not in columns:
        print("Adding 'zone' column to triage table...")
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE triage ADD COLUMN zone VARCHAR(50)"))
            conn.commit()
        print("Column 'zone' added successfully.")

    if "glasgow_e" not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE triage ADD COLUMN glasgow_e INTEGER"))
            conn.execute(text("ALTER TABLE triage ADD COLUMN glasgow_v INTEGER"))
            conn.execute(text("ALTER TABLE triage ADD COLUMN glasgow_m INTEGER"))
            conn.commit()

    if "courrier_sortie" not in [
        col["name"] for col in inspector.get_columns("sejour")
    ]:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE sejour ADD COLUMN courrier_sortie TEXT"))
            conn.commit()

    presc_added_columns = [col["name"] for col in inspector.get_columns("prescription")]
    if "annulant_id" not in presc_added_columns:
        with engine.connect() as conn:
            conn.execute(
                text("ALTER TABLE prescription ADD COLUMN annulant_id INTEGER")
            )
            conn.execute(
                text("ALTER TABLE prescription ADD COLUMN heure_annulation DATETIME")
            )
            conn.execute(
                text("ALTER TABLE prescription ADD COLUMN motif_annulation TEXT")
            )
            conn.commit()

    sejour_columns = [col["name"] for col in inspector.get_columns("sejour")]
    if "priorite_initiale" not in sejour_columns:
        with engine.connect() as conn:
            conn.execute(
                text("ALTER TABLE sejour ADD COLUMN priorite_initiale VARCHAR(50)")
            )
            conn.commit()

    presc_columns = [col["name"] for col in inspector.get_columns("prescription")]
    if "administrant_id" in presc_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE prescription DROP COLUMN administrant_id"))
            conn.execute(text("ALTER TABLE prescription DROP COLUMN heure_admin"))
            conn.execute(text("ALTER TABLE prescription DROP COLUMN administre"))
            conn.commit()

    salle_columns = [col["name"] for col in inspector.get_columns("salle")]
    if "specialite" not in salle_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE salle ADD COLUMN specialite VARCHAR(30)"))
            conn.commit()

    cv_columns = [col["name"] for col in inspector.get_columns("constantes_vitales")]
    if "risk_level" not in cv_columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE constantes_vitales ADD COLUMN risk_level VARCHAR(20)"))
            conn.execute(text("ALTER TABLE constantes_vitales ADD COLUMN risk_confidence FLOAT"))
            conn.commit()
