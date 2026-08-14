import json
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import bcrypt

from app.models.base import Base, engine, SessionLocal, upgrade_database
from app.models import Personnel, Salle, Lit, log_action


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


from app.routes.admissions_sejours import router as admissions_router
from app.routes.auth import router as auth_router
from app.routes.lits import router as lits_router
from app.routes.patients import router as patients_router
from app.routes.triage import router as triage_router
from app.routes.sejours import router as sejours_router
from app.routes.stats import router as stats_router
from app.routes.personnel import router as personnel_router
from app.routes.alertes import router as alertes_router
from app.routes.prescriptions import router as prescriptions_router
from app.routes.examens import router as examens_router
from app.routes.observations import router as observations_router
from app.routes.audit import router as audit_router
from app.routes.websocket import router as websocket_router
from app.routes.samu_integration import router as samu_router
from app.routes.recherche import router as recherche_router
from app.routes.interactions import router as interactions_router
from app.routes.prediction_ml import router as prediction_router
from app.routes.monitoring import router as monitoring_router
from app.routes.salles import router as salles_router
from app.routes.hl7_gateway import router as hl7_router


# Monkey-patch: add Z suffix to all ISO datetime strings in JSON responses
# so browsers interpret them as UTC and convert to local timezone correctly.
_original_render = JSONResponse.render


def _patched_render(self, content):
    text = json.dumps(
        content,
        ensure_ascii=False,
        allow_nan=True,
        default=str,
    )
    text = re.sub(
        r'"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)(?=")',
        r'"\1Z',
        text,
    )
    return text.encode("utf-8")


JSONResponse.render = _patched_render


def seed_data():
    db = SessionLocal()
    try:
        if db.query(Personnel).count() == 0:
            users = [
                Personnel(nom="Admin", prenom="Super", login="admin",
                          mot_de_passe=hash_password("admin"), role="admin"),
                Personnel(nom="House", prenom="Gregory", login="medecin",
                          mot_de_passe=hash_password("medecin"), role="medecin"),
                Personnel(nom="Hathaway", prenom="Carol", login="infirmier",
                          mot_de_passe=hash_password("infirmier"), role="infirmier"),
                Personnel(nom="Secretaire", prenom="Accueil", login="secretaire",
                          mot_de_passe=hash_password("secretaire"), role="secretaire"),
            ]
            existing_logins = {u.login for u in db.query(Personnel).all()}
            for u in users:
                if u.login not in existing_logins:
                    db.add(u)
            db.commit()

        if db.query(Salle).count() == 0:
            salles = [
                Salle(nom_salle="Accueil", zone="Accueil", specialite="accueil", capacite=10),
                Salle(nom_salle="Box de Soins", zone="Soins", specialite="soins", capacite=15),
                Salle(nom_salle="Déchocage", zone="Reanimation", specialite="dechocage", capacite=8),
                Salle(nom_salle="Hospitalisation", zone="Hospitalisation", specialite="hospitalisation", capacite=20),
            ]
            db.add_all(salles)
            db.commit()

            salles = db.query(Salle).all()
            lits = []
            for i in range(1, 4):
                lits.append(Lit(numero_lit=f"BOX-{i}", salle_id=salles[0].salle_id, type_lit="box"))
            for i in range(1, 6):
                lits.append(Lit(numero_lit=f"SOINS-{i}", salle_id=salles[1].salle_id, type_lit="soins"))
            for i in range(1, 4):
                lits.append(Lit(numero_lit=f"DECHO-{i}", salle_id=salles[2].salle_id, type_lit="reanimation"))
            for i in range(1, 6):
                lits.append(Lit(numero_lit=f"CC-{i}", salle_id=salles[3].salle_id, type_lit="observation"))
            db.add_all(lits)
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    upgrade_database()
    seed_data()
    yield


app = FastAPI(title="API Urgences Hospitalieres", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:3004",
        "http://localhost:3005",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admissions_router)
app.include_router(auth_router)
app.include_router(lits_router)
app.include_router(patients_router)
app.include_router(triage_router)
app.include_router(monitoring_router)
app.include_router(sejours_router)
app.include_router(stats_router)
app.include_router(personnel_router)
app.include_router(alertes_router)
app.include_router(prescriptions_router)
app.include_router(examens_router)
app.include_router(observations_router)
app.include_router(audit_router)
app.include_router(websocket_router)
app.include_router(samu_router)
app.include_router(recherche_router)
app.include_router(interactions_router)
app.include_router(prediction_router)
app.include_router(salles_router)
app.include_router(hl7_router)
