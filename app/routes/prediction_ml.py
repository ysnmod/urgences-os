from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from models.predict import load_model, predict
from models.predict_ccmu import suggest_priority, load_model as load_ccmu
from models.predict_news2 import predict_deterioration_risk, load_model as load_news2

router = APIRouter()

_artifact = None
_ccmu_artifact = None
_news2_artifact = None


def _get_artifact():
    global _artifact
    if _artifact is None:
        _artifact = load_model()
    return _artifact


def _get_ccmu_artifact():
    global _ccmu_artifact
    if _ccmu_artifact is None:
        _ccmu_artifact = load_ccmu()
    return _ccmu_artifact


def _get_news2_artifact():
    global _news2_artifact
    if _news2_artifact is None:
        _news2_artifact = load_news2()
    return _news2_artifact


class PredictionRequest(BaseModel):
    region: str = Field(description="Rural or Urban")
    urgency_level: str = Field(description="Critical, High, Medium, or Low")
    time_of_day: str = Field(description="Night, Early Morning, Late Morning, Afternoon, or Evening")
    day_of_week: str = Field(description="Monday through Sunday")
    season: str = Field(description="Winter, Spring, Summer, or Fall")
    nurse_patient_ratio: int = Field(ge=1, le=5, description="Nurse-to-patient ratio (1-5)")
    specialist_availability: int = Field(ge=0, le=10, description="Number of specialists available (0-10)")
    facility_beds: int = Field(ge=10, le=200, description="Number of facility beds (10-200)")
    hour: int = Field(ge=0, le=23, description="Hour of day (0-23)")
    weekday: int = Field(ge=0, le=6, description="Day of week as integer (0=Monday, 6=Sunday)")
    month: int = Field(ge=1, le=12, description="Month (1-12)")
    weekend: int = Field(ge=0, le=1, description="Is weekend? (0=No, 1=Yes)")


class PredictionResponse(BaseModel):
    predicted_wait_time_min: float
    urgency_level: str
    confidence_interval: str = ""


@router.post("/predict/wait-time", response_model=PredictionResponse)
async def predict_wait_time(req: PredictionRequest):
    """Predict ER wait time from triage-available features."""
    try:
        artifact = _get_artifact()
        data = req.model_dump()
        pred = predict(data, artifact)
        return PredictionResponse(
            predicted_wait_time_min=pred,
            urgency_level=req.urgency_level,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {e}")


@router.get("/predict/wait-time/features")
async def available_features():
    """Return the list of features the model expects and their valid values."""
    artifact = _get_artifact()
    return {
        "feature_names": artifact["feature_names"],
        "category_mappings": artifact.get("category_mappings", {}),
        "metrics": artifact["metrics"],
    }


class CCMUSuggestRequest(BaseModel):
    age: int = Field(ge=0, le=120)
    sexe: str = Field(pattern="^(M|F)$")
    mode_arrivee: str = Field(pattern="^(autonome|ambulance|pompiers|SMUR)$")
    score_french: int = Field(default=1, ge=1, le=5)
    poids: float = Field(ge=1, le=300)
    temperature: float = Field(ge=34, le=42)
    fc: int = Field(ge=30, le=250)
    ta_systolique: int = Field(ge=50, le=280)
    ta_diastolique: int = Field(ge=20, le=180)
    spo2: int = Field(ge=50, le=100)
    glasgow_total: int = Field(ge=3, le=15)
    douleur_eva: int = Field(ge=0, le=10)
    tranche_horaire: str = Field(pattern="^(Nuit|Matin|Après-midi|Soirée)$")
    jour_semaine: int = Field(ge=0, le=6)
    weekend: int = Field(ge=0, le=1)

    @field_validator("sexe", mode="before")
    @classmethod
    def normalize_sexe(cls, v):
        if v is None or v == "":
            return "M"
        v = str(v).strip().upper()
        if v in ("H", "HOMME", "M", "MASCULIN"):
            return "M"
        if v in ("F", "FEMME", "FEMININ"):
            return "F"
        return "M"

    @field_validator("mode_arrivee", mode="before")
    @classmethod
    def normalize_mode_arrivee(cls, v):
        if v is None or v == "":
            return "autonome"
        v = str(v).strip().lower()
        mapping = {
            "vsl": "ambulance",
            "samu": "SMUR",
            "ambulance": "ambulance",
            "pompiers": "pompiers",
            "smur": "SMUR",
            "autonome": "autonome",
            "domicile": "autonome",
            "pied": "autonome",
            "": "autonome",
        }
        return mapping.get(v, "autonome")

    @field_validator("spo2", mode="before")
    @classmethod
    def clamp_spo2(cls, v):
        try:
            return max(50, min(100, int(v)))
        except (ValueError, TypeError):
            return 98

    @field_validator("temperature", mode="before")
    @classmethod
    def clamp_temperature(cls, v):
        try:
            return max(34.0, min(42.0, float(v)))
        except (ValueError, TypeError):
            return 37.0

    @field_validator("fc", mode="before")
    @classmethod
    def clamp_fc(cls, v):
        try:
            return max(30, min(250, int(v)))
        except (ValueError, TypeError):
            return 80

    @field_validator("ta_systolique", mode="before")
    @classmethod
    def clamp_tas(cls, v):
        try:
            return max(50, min(280, int(v)))
        except (ValueError, TypeError):
            return 120

    @field_validator("ta_diastolique", mode="before")
    @classmethod
    def clamp_tad(cls, v):
        try:
            return max(20, min(180, int(v)))
        except (ValueError, TypeError):
            return 80

    @field_validator("glasgow_total", mode="before")
    @classmethod
    def clamp_glasgow(cls, v):
        try:
            return max(3, min(15, int(v)))
        except (ValueError, TypeError):
            return 15

    @field_validator("douleur_eva", mode="before")
    @classmethod
    def clamp_eva(cls, v):
        try:
            return max(0, min(10, int(v)))
        except (ValueError, TypeError):
            return 0


class CCMUSuggestResponse(BaseModel):
    predicted_ccmu: int
    confidence: float
    probabilities: dict[str, float]
    top_features: list[dict]


@router.post("/ml/suggest-priority", response_model=CCMUSuggestResponse)
async def suggest_ccmu_priority(req: CCMUSuggestRequest):
    """Suggest CCMU priority from triage vitals (M2 model)."""
    try:
        _get_ccmu_artifact()
        result = suggest_priority(
            age=req.age,
            sexe=req.sexe,
            mode_arrivee=req.mode_arrivee,
            score_french=req.score_french,
            poids=req.poids,
            temperature=req.temperature,
            fc=req.fc,
            ta_systolique=req.ta_systolique,
            ta_diastolique=req.ta_diastolique,
            spo2=req.spo2,
            glasgow_total=req.glasgow_total,
            douleur_eva=req.douleur_eva,
            tranche_horaire=req.tranche_horaire,
            jour_semaine=req.jour_semaine,
            weekend=req.weekend,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Suggestion error: {e}")


@router.get("/ml/suggest-priority/info")
async def ccmu_model_info():
    """Return CCMU model metadata."""
    art = _get_ccmu_artifact()
    return {
        "feature_names": art["feature_names"],
        "metrics": art["metrics"],
        "classes": art["classes"],
        "model_version": "v2" if art.get("is_v2") else "v1",
    }


class DeteriorationRiskRequest(BaseModel):
    fc: int = Field(ge=30, le=250, description="Heart rate")
    ta_systolique: int = Field(ge=50, le=280, description="Systolic BP")
    ta_diastolique: int = Field(ge=20, le=180, description="Diastolic BP")
    spo2: int = Field(ge=50, le=100, description="Oxygen saturation")
    temperature: float = Field(ge=34, le=42, description="Temperature")
    frequence_respiratoire: int = Field(default=16, ge=4, le=60, description="Respiratory rate")
    glasgow_total: int = Field(ge=3, le=15, description="GCS total")
    douleur_eva: int = Field(ge=0, le=10, description="Pain EVA")
    rythme: str = Field(default="sinusal", description="Cardiac rhythm")
    prev_fc: int | None = Field(default=None, ge=30, le=250)
    prev_spo2: int | None = Field(default=None, ge=50, le=100)
    prev_ta_systolique: int | None = Field(default=None, ge=50, le=280)
    prev_glasgow_total: int | None = Field(default=None, ge=3, le=15)
    prev_frequence_respiratoire: int | None = Field(default=None, ge=4, le=60)


class DeteriorationRiskResponse(BaseModel):
    alert_predicted: int
    confidence: float
    risk_level: str
    threshold: float


@router.post("/ml/deterioration-risk", response_model=DeteriorationRiskResponse)
async def predict_deterioration(req: DeteriorationRiskRequest):
    """Predict risk of NEWS2 >= 7 deterioration at the next time step (Cas4)."""
    try:
        _get_news2_artifact()
        return predict_deterioration_risk(
            fc=req.fc, ta_systolique=req.ta_systolique,
            ta_diastolique=req.ta_diastolique,
            spo2=req.spo2, temperature=req.temperature,
            frequence_respiratoire=req.frequence_respiratoire,
            glasgow_total=req.glasgow_total,
            douleur_eva=req.douleur_eva,
            rythme=req.rythme,
            prev_fc=req.prev_fc, prev_spo2=req.prev_spo2,
            prev_ta_systolique=req.prev_ta_systolique,
            prev_glasgow_total=req.prev_glasgow_total,
            prev_frequence_respiratoire=req.prev_frequence_respiratoire,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="News2 model not trained yet")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {e}")


@router.get("/ml/deterioration-risk/info")
async def deterioration_model_info():
    """Return Cas4 model metadata."""
    try:
        art = _get_news2_artifact()
        return {
            "feature_names": art["feature_names"],
            "metrics": art["metrics"],
            "threshold": art["threshold"],
        }
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="News2 model not trained yet")
