from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models import Interaction, Medicament, Prescription
from app.utils.db_utils import get_db

router = APIRouter()

# French → English / brand → generic drug name aliases
_ALIASES: dict[str, list[str]] = {
    "paracetamol": ["acetaminophen", "paracetamol"],
    "acide acetylsalicylique": ["aspirin", "acetylsalicylic acid"],
    "ibuprofene": ["ibuprofen"],
    "coumadine": ["warfarin"],
    "rivotril": ["clonazepam"],
}


def _normalize(name: str) -> str:
    import re
    import unicodedata
    name = re.sub(r"\s+\d+[\s,./]*(?:mg|g|µg|mcg|UI|ml|%).*", "", name).strip()
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    return name.lower().strip()


def _expand(name: str) -> list[str]:
    name = _normalize(name)
    for fr, en_list in _ALIASES.items():
        if name == fr or name.startswith(fr):
            return [name] + en_list
    results = [name]
    first_word = name.split()[0] if name.split() else ""
    if first_word and first_word != name and len(first_word) > 2:
        results.append(first_word)
    return results


def _resolve_substance(drug_name: str, db: Session) -> str:
    """Resolve a medication name to its active substance using broader matching."""
    # Try exact match first
    sub = (
        db.query(Medicament.substance)
        .filter(Medicament.nom.ilike(f"%{drug_name.strip()}%"))
        .first()
    )
    if sub and sub[0]:
        return sub[0]
    # Try first word only (most brand names start with the drug name)
    first_word = drug_name.strip().split()[0] if drug_name.strip() else ""
    if first_word and len(first_word) > 2:
        sub = (
            db.query(Medicament.substance)
            .filter(Medicament.nom.ilike(f"{first_word}%"))
            .first()
        )
        if sub and sub[0]:
            return sub[0]
    return drug_name


@router.get("/interactions/check-by-sejour")
async def check_interactions_by_sejour(
    sejour_id: int = Query(...),
    new_drug: str = Query(""),
    db: Session = Depends(get_db),
):
    prescriptions = (
        db.query(Prescription)
        .filter(
            Prescription.sejour_id == sejour_id,
            Prescription.annule == False,
        )
        .all()
    )
    drug_names = [p.medicament for p in prescriptions]
    if new_drug:
        drug_names.append(new_drug)

    if len(drug_names) < 2:
        return {"interactions": []}

    search_terms = []
    for d in drug_names:
        sub = _resolve_substance(d, db)
        search_terms.extend(_expand(sub))
        search_terms.extend(_expand(d))
    search_terms = list(set(search_terms))

    results = []
    seen_pairs = set()
    for i, d1 in enumerate(search_terms):
        for d2 in search_terms[i + 1:]:
            pair = tuple(sorted([d1, d2]))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            rows = (
                db.query(Interaction)
                .filter(
                    or_(
                        Interaction.drug_a.ilike(f"%{d1}%")
                        & Interaction.drug_b.ilike(f"%{d2}%"),
                        Interaction.drug_a.ilike(f"%{d2}%")
                        & Interaction.drug_b.ilike(f"%{d1}%"),
                    )
                )
                .all()
            )
            for r in rows:
                results.append({
                    "drug_a": r.drug_a,
                    "drug_b": r.drug_b,
                    "niveau": r.niveau,
                    "description": r.description,
                })
    return {"interactions": results}


@router.get("/interactions/check")
async def check_interactions(
    drug_a: str = Query(""),
    drug_b: str = Query(""),
    drugs: str = Query(""),
    db: Session = Depends(get_db),
):
    if drugs:
        raw_list = [d.strip() for d in drugs.split(",") if d.strip()]
        if len(raw_list) < 2:
            return {"interactions": []}
        # Resolve each to substance, then expand with aliases
        search_terms = []
        for d in raw_list:
            sub = _resolve_substance(d, db)
            search_terms.extend(_expand(sub))
            search_terms.extend(_expand(d))
        search_terms = list(set(search_terms))

        results = []
        seen_pairs = set()
        for i, d1 in enumerate(search_terms):
            for d2 in search_terms[i + 1:]:
                pair = tuple(sorted([d1, d2]))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                rows = (
                    db.query(Interaction)
                    .filter(
                        or_(
                            Interaction.drug_a.ilike(f"%{d1}%")
                            & Interaction.drug_b.ilike(f"%{d2}%"),
                            Interaction.drug_a.ilike(f"%{d2}%")
                            & Interaction.drug_b.ilike(f"%{d1}%"),
                        )
                    )
                    .all()
                )
                for r in rows:
                    results.append({
                        "drug_a": r.drug_a,
                        "drug_b": r.drug_b,
                        "niveau": r.niveau,
                        "description": r.description,
                    })
        return {"interactions": results}

    if drug_a and drug_b:
        terms_a = _expand(_resolve_substance(drug_a, db))
        terms_b = _expand(_resolve_substance(drug_b, db))
        all_terms = list(set(terms_a + terms_b))
        rows = (
            db.query(Interaction)
            .filter(
                or_(
                    Interaction.drug_a.ilike(f"%{all_terms[0]}%")
                    & Interaction.drug_b.ilike(f"%{all_terms[-1]}%"),
                    Interaction.drug_a.ilike(f"%{all_terms[-1]}%")
                    & Interaction.drug_b.ilike(f"%{all_terms[0]}%"),
                )
            )
            .all()
        )
        return {
            "interactions": [
                {
                    "drug_a": r.drug_a,
                    "drug_b": r.drug_b,
                    "niveau": r.niveau,
                    "description": r.description,
                }
                for r in rows
            ]
        }

    return {"interactions": []}
