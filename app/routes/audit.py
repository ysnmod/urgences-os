from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.models import AuditLog, Personnel
from app.utils.db_utils import get_db
from app.dependencies import require_roles

router = APIRouter()


@router.get("/audit/")
async def get_audit_logs(
    limit: int = Query(default=100),
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin")),
):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "log_id": log.log_id,
            "timestamp": log.timestamp,
            "personnel_id": log.personnel_id,
            "action": log.action,
            "entite": log.entite,
            "entite_id": log.entite_id,
            "detail": log.detail,
            "ip_address": log.ip_address,
        }
        for log in logs
    ]
