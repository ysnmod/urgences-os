"""NEWS2 deterioration risk prediction (Cas4)."""
import joblib
import numpy as np
from pathlib import Path

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"

RHYTHM_MAP = {
    "sinusal": 0, "bradycardie_sinusale": 1, "tachycardie_sinusale": 2,
    "fibrillation_atriale": 3, "tachycardie_ventriculaire": 4,
}
RHYTHM_REVERSE = {v: k for k, v in RHYTHM_MAP.items()}

_artifact = None


def load_model():
    global _artifact
    if _artifact is None:
        path = ARTIFACTS_DIR / "news2_model.joblib"
        if not path.exists():
            raise FileNotFoundError(f"Model not found at {path}")
        _artifact = joblib.load(path)
    return _artifact


def predict_deterioration_risk(
    fc: int, ta_systolique: int, ta_diastolique: int,
    spo2: int, temperature: float, glasgow_total: int,
    douleur_eva: int, rythme: str, frequence_respiratoire: int,
    prev_fc: int | None = None,
    prev_spo2: int | None = None,
    prev_ta_systolique: int | None = None,
    prev_glasgow_total: int | None = None,
    prev_frequence_respiratoire: int | None = None,
) -> dict:
    artifact = load_model()
    model = artifact["model"]
    threshold = artifact["threshold"]
    feature_names = artifact["feature_names"]

    rythme_code = RHYTHM_MAP.get(rythme.lower().strip(), 0)

    delta_fc = (fc - prev_fc) if prev_fc is not None else 0
    delta_spo2 = (spo2 - prev_spo2) if prev_spo2 is not None else 0
    delta_tas = (ta_systolique - prev_ta_systolique) if prev_ta_systolique is not None else 0
    delta_gcs = (glasgow_total - prev_glasgow_total) if prev_glasgow_total is not None else 0
    delta_fr = (frequence_respiratoire - prev_frequence_respiratoire) if prev_frequence_respiratoire is not None else 0

    features = np.array([[
        fc, ta_systolique, ta_diastolique, spo2, temperature,
        frequence_respiratoire,
        glasgow_total, douleur_eva, rythme_code,
        delta_fc, delta_spo2, delta_tas, delta_gcs, delta_fr,
    ]])

    proba = model.predict_proba(features)[0, 1]
    prediction = int(proba >= threshold)

    return {
        "alert_predicted": prediction,
        "confidence": round(float(proba), 4),
        "risk_level": "HIGH" if proba >= 0.7 else ("MODERATE" if proba >= 0.3 else "LOW"),
        "threshold": float(threshold),
    }
