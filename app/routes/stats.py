from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.models import Sejour, Lit, Examen, Personnel, TypeExamen, TriageRecord, Observation
from app.utils.db_utils import get_db
from app.dependencies import require_roles
import pytz
from datetime import datetime, timezone, timedelta
from sqlalchemy import extract

router = APIRouter()


@router.get("/stats/")
async def get_stats(
    tz: str = Query(default="Europe/Paris"),
    db: Session = Depends(get_db),
    current_user: "Personnel" = Depends(require_roles("admin")),
):
    try:
        hospital_tz = pytz.timezone(tz)
    except Exception:
        hospital_tz = pytz.timezone("Europe/Paris")

    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(hospital_tz)

    today_local = now_local.date()
    current_month = now_local.month
    current_year = now_local.year

    start_of_day_local = hospital_tz.localize(
        datetime(today_local.year, today_local.month, today_local.day, 0, 0, 0)
    )
    end_of_day_local = hospital_tz.localize(
        datetime(today_local.year, today_local.month, today_local.day, 23, 59, 59)
    )
    start_of_day_utc = start_of_day_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_of_day_utc = end_of_day_local.astimezone(timezone.utc).replace(tzinfo=None)

    total_actifs = db.query(Sejour).filter(Sejour.statut != "Sorti").count()
    en_attente_triage = (
        db.query(Sejour)
        .filter(
            Sejour.statut == "En attente de triage",
            ~Sejour.triages.any()
        )
        .count()
    )

    actifs = db.query(Sejour).filter(Sejour.statut != "Sorti").all()

    avg_wait = 0
    if actifs:
        total_mins = 0
        count = 0
        for s in actifs:
            arrivee = s.date_arrivee
            if not arrivee:
                continue
            if arrivee.tzinfo is None:
                arrivee = arrivee.replace(tzinfo=timezone.utc)
            total_mins += (now_utc - arrivee).total_seconds() / 60
            count += 1
        avg_wait = round(total_mins / count) if count else 0

    total_lits = db.query(Lit).count()
    lits_occupes = db.query(Lit).filter(Lit.statut == "occupe").count()
    taux_occupation = round((lits_occupes / total_lits * 100) if total_lits > 0 else 0)

    examens_en_attente = (
        db.query(Examen)
        .join(Sejour)
        .filter(Examen.statut == "demande", Sejour.statut != "Sorti")
        .count()
    )

    repartition = {
        "Salle d'attente": 0,
        "Box": 0,
        "Soins": 0,
        "Déchocage": 0,
        "Circuit Court": 0,
        "Hospitalisation": 0,
    }
    for s in actifs:
        aff_active = next((a for a in s.affectations_lit if a.heure_fin is None), None)
        if aff_active and aff_active.lit:
            t = aff_active.lit.type_lit
            if t == "box":
                secteur = "Box"
            elif t == "soins":
                secteur = "Soins"
            elif t == "reanimation":
                secteur = "Déchocage"
            elif t == "observation":
                secteur = "Circuit Court"
            elif t == "hospitalisation":
                secteur = "Hospitalisation"
            else:
                secteur = t.capitalize()
        else:
            triage = s.triages[-1] if s.triages else None
            if triage and triage.zone:
                z = triage.zone
                if z == "Attente":
                    secteur = "Salle d'attente"
                elif z == "Dechocage":
                    secteur = "Déchocage"
                else:
                    secteur = z
            else:
                secteur = "Salle d'attente"
        repartition[secteur] = repartition.get(secteur, 0) + 1

    servis_jour = (
        db.query(Sejour)
        .filter(
            Sejour.statut == "Sorti",
            Sejour.date_sortie >= start_of_day_utc,
            Sejour.date_sortie <= end_of_day_utc,
        )
        .count()
    )
    servis_mois = (
        db.query(Sejour)
        .filter(
            Sejour.statut == "Sorti",
            extract("month", Sejour.date_sortie) == current_month,
            extract("year", Sejour.date_sortie) == current_year,
        )
        .count()
    )
    servis_annee = (
        db.query(Sejour)
        .filter(
            Sejour.statut == "Sorti",
            extract("year", Sejour.date_sortie) == current_year,
        )
        .count()
    )

    # KPI 1: DMS 24h
    dms_list = db.query(Sejour).filter(
        Sejour.statut == "Sorti",
        Sejour.date_sortie >= now_utc - timedelta(hours=24)
    ).all()
    dms_vals = []
    for s in dms_list:
        if s.date_arrivee and s.date_sortie:
            arr = s.date_arrivee.replace(tzinfo=timezone.utc) if s.date_arrivee.tzinfo is None else s.date_arrivee
            sor = s.date_sortie.replace(tzinfo=timezone.utc) if s.date_sortie.tzinfo is None else s.date_sortie
            dms_vals.append((sor - arr).total_seconds() / 60)
    avg_dms = round(sum(dms_vals) / len(dms_vals)) if dms_vals else 0

    # KPI 2: Attente Médicale (Triage ➔ Médecin)
    target_sejours = db.query(Sejour).filter(
        Sejour.date_arrivee >= now_utc - timedelta(hours=24)
    ).all()
    delays = []
    for s in target_sejours:
        first_triage = sorted([t.heure_triage for t in s.triages if t.heure_triage]) if s.triages else None
        first_obs = sorted([o.date_obs for o in s.observations if o.date_obs]) if s.observations else None
        if first_triage and first_obs:
            t_time = first_triage[0].replace(tzinfo=timezone.utc) if first_triage[0].tzinfo is None else first_triage[0]
            o_time = first_obs[0].replace(tzinfo=timezone.utc) if first_obs[0].tzinfo is None else first_obs[0]
            diff = (o_time - t_time).total_seconds() / 60
            if diff > 0:
                delays.append(diff)
    avg_triage_medecin = round(sum(delays) / len(delays)) if delays else 0

    # KPI 3: Délai Moyen d'Obtention des Examens (Biologie vs Imagerie) sur 24h
    exams_done = db.query(Examen, TypeExamen.categorie).join(TypeExamen, Examen.type_examen == TypeExamen.nom).filter(
        Examen.statut == 'réalisé',
        Examen.heure_prescription >= now_utc - timedelta(hours=24)
    ).all()
    bio_delays = []
    img_delays = []
    for e, cat in exams_done:
        if e.heure_prescription and e.heure_resultat:
            hp = e.heure_prescription.replace(tzinfo=timezone.utc) if e.heure_prescription.tzinfo is None else e.heure_prescription
            hr = e.heure_resultat.replace(tzinfo=timezone.utc) if e.heure_resultat.tzinfo is None else e.heure_resultat
            diff = (hr - hp).total_seconds() / 60
            if diff > 0:
                if cat == 'biologie':
                    bio_delays.append(diff)
                elif cat == 'imagerie':
                    img_delays.append(diff)
    avg_bio_min = round(sum(bio_delays) / len(bio_delays)) if bio_delays else 0
    avg_img_min = round(sum(img_delays) / len(img_delays)) if img_delays else 0

    # KPI 4: Orientation des Sorties
    sorties = db.query(Sejour.mode_sortie).filter(
        Sejour.statut == "Sorti"
    ).all()
    distribution = {"Domicile": 0, "Hospitalisation": 0, "Transfert": 0}
    for row in sorties:
        mode = row[0]
        if mode:
            if "domicile" in mode.lower():
                distribution["Domicile"] += 1
            elif "hospitalisation" in mode.lower() or "hopital" in mode.lower():
                distribution["Hospitalisation"] += 1
            elif "transfert" in mode.lower() or "muté" in mode.lower():
                distribution["Transfert"] += 1
            else:
                distribution["Domicile"] += 1

    # KPI 5: Gravité Clinique Active (Répartition CCMU)
    ccmu_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, "non_trie": 0}
    for s in actifs:
        triage = s.triages[-1] if s.triages else None
        if triage and triage.score_ccmu:
            ccmu_counts[triage.score_ccmu] = ccmu_counts.get(triage.score_ccmu, 0) + 1
        else:
            ccmu_counts["non_trie"] += 1

    return {
        "total_actifs": total_actifs,
        "en_attente_triage": en_attente_triage,
        "avg_wait_minutes": avg_wait,
        "taux_occupation": taux_occupation,
        "total_lits": total_lits,
        "lits_occupes": lits_occupes,
        "examens_en_attente": examens_en_attente,
        "repartition_zones": repartition,
        "servis_jour": servis_jour,
        "servis_mois": servis_mois,
        "servis_annee": servis_annee,
        "dms_minutes": avg_dms,
        "attente_medecin_minutes": avg_triage_medecin,
        "delai_biologie_minutes": avg_bio_min,
        "delai_imagerie_minutes": avg_img_min,
        "repartition_sorties": distribution,
        "repartition_ccmu": ccmu_counts,
    }
