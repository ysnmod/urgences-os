from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models import Personnel
from app.utils.db_utils import get_db
from app.dependencies import require_roles

router = APIRouter()


@router.get("/personnel/")
async def get_personnel(
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin")),
):
    personnel = db.query(Personnel).all()
    return [
        {
            "personnel_id": p.personnel_id,
            "nom": p.nom,
            "prenom": p.prenom,
            "login": p.login,
            "mot_de_passe_plain": p.mot_de_passe_plain,
            "role": p.role,
            "actif": p.actif,
        }
        for p in personnel
    ]


@router.post("/personnel/")
async def create_personnel(
    personnel_data: dict,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin")),
):
    from fastapi import HTTPException

    existing = (
        db.query(Personnel).filter(Personnel.login == personnel_data["login"]).first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Login déjà utilisé")

    from app.routes.auth import hash_password

    new_personnel = Personnel(
        nom=personnel_data["nom"],
        prenom=personnel_data["prenom"],
        login=personnel_data["login"],
        mot_de_passe=hash_password(personnel_data["mot_de_passe"]),
        mot_de_passe_plain=personnel_data["mot_de_passe"],
        role=personnel_data["role"],
        actif=True,
    )

    db.add(new_personnel)
    db.commit()
    db.refresh(new_personnel)

    return {
        "personnel_id": new_personnel.personnel_id,
        "nom": new_personnel.nom,
        "prenom": new_personnel.prenom,
        "login": new_personnel.login,
        "role": new_personnel.role,
        "actif": new_personnel.actif,
    }


@router.put("/personnel/{personnel_id}/actif")
async def toggle_personnel_actif(
    personnel_id: int,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin")),
):
    from fastapi import HTTPException

    personnel = (
        db.query(Personnel).filter(Personnel.personnel_id == personnel_id).first()
    )
    if not personnel:
        raise HTTPException(status_code=404, detail="Personnel non trouvé")

    if personnel.personnel_id == current_user.personnel_id:
        raise HTTPException(
            status_code=400, detail="Impossible de désactiver votre propre compte"
        )

    personnel.actif = not personnel.actif
    db.commit()

    return {
        "message": f"Personnel {'activé' if personnel.actif else 'désactivé'} avec succès"
    }


@router.put("/personnel/{personnel_id}/password")
async def change_personnel_password(
    personnel_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin")),
):
    from fastapi import HTTPException
    from app.routes.auth import hash_password

    personnel = (
        db.query(Personnel).filter(Personnel.personnel_id == personnel_id).first()
    )
    if not personnel:
        raise HTTPException(status_code=404, detail="Personnel non trouvé")

    new_password = data.get("mot_de_passe", "").strip()
    if not new_password or len(new_password) < 4:
        raise HTTPException(
            status_code=400, detail="Le mot de passe doit contenir au moins 4 caractères"
        )

    personnel.mot_de_passe = hash_password(new_password)
    personnel.mot_de_passe_plain = new_password
    db.commit()

    return {"message": "Mot de passe modifié avec succès"}
