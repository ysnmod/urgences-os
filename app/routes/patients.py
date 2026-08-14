from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.models import Patient, Sejour, Personnel
from app.schemas import PatientCreate, SejourCreate
from app.utils.db_utils import get_db
from app.dependencies import require_roles

router = APIRouter()


@router.get("/patients/search")
async def search_patients(
    q: str = Query(...),
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(
        require_roles("admin", "secretaire", "medecin", "infirmier")
    ),
):
    search_term = f"%{q.strip()}%"
    concat_fullname1 = Patient.nom + " " + Patient.prenom
    concat_fullname2 = Patient.prenom + " " + Patient.nom

    results = (
        db.query(Patient)
        .filter(
            (Patient.nom.ilike(search_term))
            | (Patient.prenom.ilike(search_term))
            | (Patient.numero_secu.ilike(search_term))
            | (concat_fullname1.ilike(search_term))
            | (concat_fullname2.ilike(search_term))
        )
        .limit(10)
        .all()
    )
    return [
        {
            "patient_id": p.patient_id,
            "nom": p.nom,
            "prenom": p.prenom,
            "date_naissance": str(p.date_naissance) if p.date_naissance else None,
            "numero_secu": p.numero_secu,
        }
        for p in results
    ]
