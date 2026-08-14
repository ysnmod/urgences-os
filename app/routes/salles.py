from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.models import Salle, Lit, log_action, Personnel
from app.utils.db_utils import get_db
from app.dependencies import require_roles

router = APIRouter()


class SalleCreate(BaseModel):
    nom_salle: str
    zone: str
    specialite: Optional[str] = None
    capacite: Optional[int] = 0


class SalleUpdate(BaseModel):
    nom_salle: Optional[str] = None
    zone: Optional[str] = None
    specialite: Optional[str] = None
    capacite: Optional[int] = None


class LitBulkCreate(BaseModel):
    type_lit: str
    nombre: int


@router.get("/salles/")
async def get_salles(
    db: Session = Depends(get_db),
    current_user: Personnel = Depends(require_roles("admin", "infirmier", "medecin")),
):
    salles = db.query(Salle).all()
    resultats = []
    for s in salles:
        lits = db.query(Lit).filter(Lit.salle_id == s.salle_id).all()
        resultats.append({
            "salle_id": s.salle_id,
            "nom_salle": s.nom_salle,
            "zone": s.zone,
            "specialite": s.specialite,
            "capacite": s.capacite,
            "lits": [
                {
                    "lit_id": l.lit_id,
                    "numero_lit": l.numero_lit,
                    "type_lit": l.type_lit,
                    "statut": l.statut,
                }
                for l in lits
            ],
        })
    return resultats


@router.post("/salles/")
async def create_salle(
    salle_in: SalleCreate,
    db: Session = Depends(get_db),
    current_user: Personnel = Depends(require_roles("admin")),
):
    salle = Salle(
        nom_salle=salle_in.nom_salle,
        zone=salle_in.zone,
        specialite=salle_in.specialite,
        capacite=salle_in.capacite,
    )
    db.add(salle)
    db.flush()

    log_action(
        db,
        "SALLE_CREATE",
        personnel_id=current_user.personnel_id,
        entite="salle",
        entite_id=salle.salle_id,
        detail={"nom_salle": salle.nom_salle, "zone": salle.zone, "specialite": salle.specialite},
    )
    db.commit()
    return {
        "salle_id": salle.salle_id,
        "nom_salle": salle.nom_salle,
        "zone": salle.zone,
        "specialite": salle.specialite,
        "capacite": salle.capacite,
    }


@router.put("/salles/{salle_id}")
async def update_salle(
    salle_id: int,
    salle_in: SalleUpdate,
    db: Session = Depends(get_db),
    current_user: Personnel = Depends(require_roles("admin")),
):
    salle = db.query(Salle).filter(Salle.salle_id == salle_id).first()
    if not salle:
        raise HTTPException(status_code=404, detail="Zone introuvable")

    if salle_in.nom_salle is not None:
        salle.nom_salle = salle_in.nom_salle
    if salle_in.zone is not None:
        salle.zone = salle_in.zone
    if salle_in.specialite is not None:
        salle.specialite = salle_in.specialite
    if salle_in.capacite is not None:
        salle.capacite = salle_in.capacite

    log_action(
        db,
        "SALLE_UPDATE",
        personnel_id=current_user.personnel_id,
        entite="salle",
        entite_id=salle_id,
        detail=salle_in.model_dump(exclude_none=True),
    )
    db.commit()
    return {
        "salle_id": salle.salle_id,
        "nom_salle": salle.nom_salle,
        "zone": salle.zone,
        "specialite": salle.specialite,
        "capacite": salle.capacite,
    }


@router.delete("/salles/{salle_id}")
async def delete_salle(
    salle_id: int,
    db: Session = Depends(get_db),
    current_user: Personnel = Depends(require_roles("admin")),
):
    salle = db.query(Salle).filter(Salle.salle_id == salle_id).first()
    if not salle:
        raise HTTPException(status_code=404, detail="Zone introuvable")

    db.query(Lit).filter(Lit.salle_id == salle_id).delete()
    db.delete(salle)

    log_action(
        db,
        "SALLE_DELETE",
        personnel_id=current_user.personnel_id,
        entite="salle",
        entite_id=salle_id,
    )
    db.commit()
    return {"message": f"Zone {salle.nom_salle} supprimée avec ses lits"}


@router.post("/salles/{salle_id}/lits")
async def ajouter_lits(
    salle_id: int,
    lit_in: LitBulkCreate,
    db: Session = Depends(get_db),
    current_user: Personnel = Depends(require_roles("admin")),
):
    salle = db.query(Salle).filter(Salle.salle_id == salle_id).first()
    if not salle:
        raise HTTPException(status_code=404, detail="Zone introuvable")

    existing_count = (
        db.query(Lit)
        .filter(Lit.salle_id == salle_id, Lit.type_lit == lit_in.type_lit)
        .count()
    )
    nouveaux = []
    for i in range(lit_in.nombre):
        numero = f"{lit_in.type_lit.upper()[:4]}-{existing_count + i + 1}"
        lit = Lit(
            numero_lit=numero,
            salle_id=salle_id,
            type_lit=lit_in.type_lit,
            statut="libre",
        )
        db.add(lit)
        nouveaux.append({"numero_lit": numero, "type_lit": lit_in.type_lit})

    log_action(
        db,
        "LITS_BULK_CREATE",
        personnel_id=current_user.personnel_id,
        entite="salle",
        entite_id=salle_id,
        detail={"type_lit": lit_in.type_lit, "nombre": lit_in.nombre},
    )
    db.commit()
    return {"message": f"{lit_in.nombre} lit(s) ajouté(s)", "lits": nouveaux}
