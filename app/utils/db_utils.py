from sqlalchemy.orm import Session
from app.models.base import SessionLocal, engine, Base, upgrade_database
from datetime import datetime, timezone


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _coerce_utc(dt):
    """Convert a datetime to UTC timezone"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
