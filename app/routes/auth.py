from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import secrets
import bcrypt

from app.models import Personnel, SessionToken, log_action
from app.schemas import LoginRequest
from app.utils.db_utils import get_db
from app.dependencies import get_current_user

router = APIRouter()


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


@router.post("/login/")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(Personnel)
        .filter(Personnel.login == request.login, Personnel.actif == True)
        .first()
    )
    if not user or not verify_password(request.mot_de_passe, user.mot_de_passe):
        log_action(db, "LOGIN_ECHEC", detail={"login_tente": request.login})
        db.commit()
        raise HTTPException(status_code=401, detail="Identifiants incorrects")

    token_value = secrets.token_urlsafe(64)
    expire = datetime.now(timezone.utc) + timedelta(hours=12)
    session = SessionToken(
        token=token_value,
        personnel_id=user.personnel_id,
        expire_le=expire,
    )
    db.add(session)
    log_action(
        db,
        "LOGIN",
        personnel_id=user.personnel_id,
        entite="personnel",
        entite_id=user.personnel_id,
    )
    db.commit()

    return {
        "token": token_value,
        "personnel_id": user.personnel_id,
        "nom": user.nom,
        "prenom": user.prenom,
        "role": user.role,
        "expire_le": expire.isoformat(),
    }


@router.post("/logout/")
async def logout(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
    current_user: Personnel = Depends(get_current_user),
):
    if not authorization:
        return {"message": "Déconnecté"}
    token_value = authorization.replace("Bearer ", "")
    session = db.query(SessionToken).filter(SessionToken.token == token_value).first()
    if session:
        session.actif = False
        log_action(
            db,
            "LOGOUT",
            personnel_id=current_user.personnel_id,
            entite="personnel",
            entite_id=current_user.personnel_id,
        )
        db.commit()
    return {"message": "Déconnexion réussie"}
