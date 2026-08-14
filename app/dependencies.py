from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional

from app.models import Personnel, SessionToken
from app.utils.db_utils import get_db


security = HTTPBearer(auto_error=False)


def get_current_user(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> "Personnel":
    """Get current authenticated user from token"""
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Non authentifié")

    token_value = credentials.credentials
    now = datetime.now(timezone.utc)
    session = (
        db.query(SessionToken)
        .filter(
            SessionToken.token == token_value,
            SessionToken.actif == True,
            SessionToken.expire_le > now,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=401, detail="Session expirée ou invalide")

    user = (
        db.query(Personnel)
        .filter(Personnel.personnel_id == session.personnel_id, Personnel.actif == True)
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=401, detail="Utilisateur inactif ou introuvable"
        )
    return user


def require_roles(*roles: str):
    """Dependency to require specific roles"""

    def _dep(current_user: "Personnel" = Depends(get_current_user)) -> "Personnel":
        if roles and current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Accès interdit")
        return current_user

    return _dep
