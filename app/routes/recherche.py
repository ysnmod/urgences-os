from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, select
from app.models import Medicament, TypeExamen
from app.utils.db_utils import get_db

router = APIRouter()


@router.get("/medicaments/search")
async def search_medicaments(
    q: str = Query("", max_length=100),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    if not q:
        total = db.query(func.count(Medicament.id)).scalar() or 0
        results = (
            db.query(Medicament)
            .order_by(Medicament.nom)
            .limit(limit)
            .all()
        )
    else:
        query_lower = f"%{q}%"
        prefix_like = f"{q}%"
        base_q = db.query(Medicament).filter(
            Medicament.nom.ilike(query_lower)
            | Medicament.cis_code.ilike(f"{q}%")
        )
        total = base_q.count()
        results = (
            base_q
            .order_by(
                case(
                    (func.lower(Medicament.nom).like(prefix_like), 0),
                    else_=1
                ),
                func.length(Medicament.nom),
            )
            .limit(limit)
            .all()
        )
    return {
        "results": [
            {
                "id": m.id,
                "cis_code": m.cis_code,
                "nom": m.nom,
                "forme": m.forme,
                "voie_administration": m.voie_administration,
            }
            for m in results
        ],
        "total": total,
    }


@router.get("/examens-types/search")
async def search_examens_types(
    q: str = Query("", max_length=100),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    if not q:
        total = db.query(func.count(TypeExamen.id)).scalar() or 0
        results = (
            db.query(TypeExamen)
            .order_by(TypeExamen.nom)
            .limit(limit)
            .all()
        )
    else:
        base_q = db.query(TypeExamen).filter(TypeExamen.nom.ilike(f"%{q}%"))
        total = base_q.count()
        results = (
            base_q
            .order_by(TypeExamen.nom)
            .limit(limit)
            .all()
        )
    return {
        "results": [
            {
                "id": t.id,
                "nom": t.nom,
                "categorie": t.categorie,
            }
            for t in results
        ],
        "total": total,
    }
