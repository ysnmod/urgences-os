import joblib
import numpy as np
from pathlib import Path

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
V2_PATH = ARTIFACTS_DIR / "ccmu_model_v2.joblib"
V1_PATH = ARTIFACTS_DIR / "ccmu_model.joblib"

_artifact = None
_is_v2 = None


def load_model(path: Path | None = None) -> dict:
    if path is not None:
        if not path.exists():
            raise FileNotFoundError(f"CCMU model not found: {path}")
        return joblib.load(path)

    if V2_PATH.exists():
        print("[predict_ccmu] Using v2 model with cross-features")
        return joblib.load(V2_PATH)

    print("[predict_ccmu] v2 not found, falling back to v1")
    return joblib.load(V1_PATH)


def _get_artifact():
    global _artifact, _is_v2
    if _artifact is None:
        _artifact = load_model()
        _is_v2 = _artifact.get("is_v2", False)
    return _artifact


def _engineer_cross_features(raw: dict) -> dict:
    shock_index = raw["fc"] / max(raw["ta_systolique"], 1)
    hypoxemia_resp = 1.0 if raw["spo2"] < 90 else 0.0
    neuro_severity = 1.0 if raw["glasgow_total"] <= 12 else (0.5 if raw["glasgow_total"] <= 14 else 0.0)
    age_severity = 1.0 if raw["age"] >= 75 else (0.5 if raw["age"] >= 60 else 0.0)
    pain_tachy = 1.0 if (raw["douleur_eva"] >= 7 and raw["fc"] >= 100) else 0.0

    return {
        "shock_index": round(shock_index, 4),
        "hypoxemia_resp": hypoxemia_resp,
        "neuro_severity": neuro_severity,
        "age_severity": age_severity,
        "pain_tachy": pain_tachy,
    }


def _predict_v1(art: dict, row: list, all_features: list) -> dict:
    model = art["model"]
    classes = art["classes"]
    X = np.array([row])
    pred_class_idx = int(model.predict(X)[0])
    proba = model.predict_proba(X)[0].tolist()

    predicted_class = classes[pred_class_idx]
    confidence = proba[pred_class_idx]

    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1][:3]
    top_features = [
        {"name": all_features[i], "importance": float(importances[i])}
        for i in indices
    ]

    return {
        "predicted_ccmu": predicted_class,
        "confidence": round(confidence, 3),
        "probabilities": {f"C{c}": round(proba[i], 3) for i, c in enumerate(classes)},
        "top_features": top_features,
    }


def _predict_v2(art: dict, row: list, all_features: list) -> dict:
    model = art["model"]
    classes = art["classes"]
    X = np.array([row])

    c1_boost = art.get("c1_threshold_boost", 1.0)
    proba = model.predict_proba(X)[0].copy()

    if c1_boost > 1.0:
        proba[0] *= c1_boost
        proba /= proba.sum()

    predicted_class_idx = int(np.argmax(proba))
    predicted_class = classes[predicted_class_idx]
    confidence = float(proba[predicted_class_idx])

    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1][:3]
    top_features = [
        {"name": all_features[i], "importance": float(importances[i])}
        for i in indices
    ]

    return {
        "predicted_ccmu": predicted_class,
        "confidence": round(confidence, 3),
        "probabilities": {f"C{c}": round(proba[i], 3) for i, c in enumerate(classes)},
        "top_features": top_features,
    }


def _clinical_ccmu_floor(raw: dict) -> int:
    """Minimum CCMU determined by clinical thresholds.
    
    Each vital sign maps to a CCMU level based on real triage guidelines.
    Returns the HIGHEST level triggered by any abnormality.
    """
    gcs = raw["glasgow_total"]
    spo2 = raw["spo2"]
    fc = raw["fc"]
    tas = raw["ta_systolique"]
    temp = raw["temperature"]
    eva = raw["douleur_eva"]

    levels = [1]

    if gcs <= 7 or spo2 <= 74 or fc < 35 or fc > 180 or tas <= 79:
        levels.append(5)

    if 8 <= gcs <= 12 or 75 <= spo2 <= 89 or (150 <= fc <= 180) or (35 <= fc <= 49) or 80 <= tas <= 89 or temp >= 40 or temp < 35:
        levels.append(4)

    if gcs in (13, 14) or 90 <= spo2 <= 94 or (101 <= fc <= 149) or (50 <= fc <= 59) or 90 <= tas <= 99 or temp >= 39 or eva >= 7:
        levels.append(3)

    minor_count = sum([
        spo2 <= 95,
        91 <= fc <= 100,
        50 <= fc <= 59,
        100 <= tas <= 109,
        tas >= 160,
        eva >= 4,
        38 <= temp < 39,
        temp < 36,
    ])
    if minor_count >= 1:
        levels.append(2)

    return max(levels)


def _clinical_ccmu_ceiling(raw: dict) -> int | None:
    gcs = raw["glasgow_total"]
    spo2 = raw["spo2"]
    fc = raw["fc"]
    tas = raw["ta_systolique"]
    temp = raw["temperature"]

    if any([
        gcs <= 12,
        spo2 <= 89,
        fc >= 150 or (35 <= fc <= 49),
        tas <= 89,
        temp >= 40 or temp < 35,
    ]):
        return None

    if any([
        gcs <= 14,
        spo2 <= 94,
        fc >= 101 or fc <= 59,
        tas <= 99 or tas >= 160,
        temp >= 39 or temp < 36,
        raw["douleur_eva"] >= 7,
    ]):
        return 3

    return 2


def suggest_priority(
    age: int,
    sexe: str,
    mode_arrivee: str,
    score_french: int,
    poids: float,
    temperature: float,
    fc: int,
    ta_systolique: int,
    ta_diastolique: int,
    spo2: int,
    glasgow_total: int,
    douleur_eva: int,
    tranche_horaire: str,
    jour_semaine: int,
    weekend: int,
) -> dict:
    art = _get_artifact()
    encoders = art["encoders"]
    all_features = art["feature_names"]

    raw = {
        "age": age,
        "sexe": sexe,
        "mode_arrivee": mode_arrivee,
        "score_french": score_french,
        "poids": poids,
        "temperature": temperature,
        "fc": fc,
        "ta_systolique": ta_systolique,
        "ta_diastolique": ta_diastolique,
        "spo2": spo2,
        "glasgow_total": glasgow_total,
        "douleur_eva": douleur_eva,
        "tranche_horaire": tranche_horaire,
        "jour_semaine": jour_semaine,
        "weekend": weekend,
    }

    if _is_v2:
        raw.update(_engineer_cross_features(raw))

    row = []
    for col in all_features:
        val = raw[col]
        if col in encoders:
            mapping = encoders[col]
            if val not in mapping:
                raise ValueError(
                    f"Unknown value '{val}' for {col}, "
                    f"expected one of: {list(mapping.keys())}"
                )
            val = mapping[val]
        row.append(float(val))

    if _is_v2:
        result = _predict_v2(art, row, all_features)
    else:
        result = _predict_v1(art, row, all_features)

    clinical_floor = _clinical_ccmu_floor(raw)
    if clinical_floor > result["predicted_ccmu"]:
        ml_ccmu = result["predicted_ccmu"]
        result["predicted_ccmu"] = clinical_floor
        result["confidence"] = 0.95
        result["clinical_override"] = True
        result["ml_predicted_ccmu"] = ml_ccmu
        probs = result["probabilities"]
        still_has_ml_prob = sum(v for k, v in probs.items() if int(k[1:]) >= clinical_floor)
        if still_has_ml_prob > 0:
            for k in list(probs.keys()):
                if int(k[1:]) < clinical_floor:
                    probs[k] = 0.0
            total = sum(probs.values())
            if total > 0:
                for k in probs:
                    probs[k] = round(probs[k] / total, 3)
        result["probabilities"] = probs

    clinical_ceiling = _clinical_ccmu_ceiling(raw)
    if clinical_ceiling is not None and result["predicted_ccmu"] > clinical_ceiling:
        ml_ccmu = result["predicted_ccmu"]
        result["predicted_ccmu"] = clinical_ceiling
        result["confidence"] = 0.85
        result["clinical_ceiling"] = True
        result["ml_predicted_ccmu"] = ml_ccmu
        probs = result["probabilities"]
        for k in list(probs.keys()):
            if int(k[1:]) > clinical_ceiling:
                probs[k] = 0.0
        total = sum(probs.values())
        if total > 0:
            for k in probs:
                probs[k] = round(probs[k] / total, 3)
        result["probabilities"] = probs

    return result
