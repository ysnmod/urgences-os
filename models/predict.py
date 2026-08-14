"""Inference module for ER wait time prediction."""

import joblib
import pandas as pd
import numpy as np
from pathlib import Path

from models.features import CAT_COLS, NUM_COLS

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
DEFAULT_MODEL = ARTIFACTS_DIR / "wait_time_model.joblib"


def load_model(path: Path = DEFAULT_MODEL) -> dict:
    """Load trained model artifact with feature names and category mappings."""
    if not path.exists():
        raise FileNotFoundError(f"Model not found: {path}")
    return joblib.load(path)


def prepare_input(data: dict, artifact: dict) -> pd.DataFrame:
    """Convert a dict of raw feature values into a model-ready DataFrame.

    Encodes categoricals using the same category->code mapping learned
    during training so predictions are consistent.
    """
    category_mappings = artifact.get("category_mappings", {})
    feature_names = artifact.get("feature_names", [])

    df = pd.DataFrame([data])

    for col in CAT_COLS:
        if col in df.columns and col in category_mappings:
            cats = category_mappings[col]
            raw_val = df[col].iloc[0]
            if raw_val not in cats:
                msg = f"Unknown '{col}' value '{raw_val}'. Expected one of: {cats}"
                raise ValueError(msg)
            df[col] = pd.Categorical(df[col], categories=cats).codes

    for col in NUM_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["hour", "weekday", "month"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype(int)

    if "weekend" in df.columns:
        wd = df.get("weekday", pd.Series([np.nan]))
        df["weekend"] = wd.isin([5, 6]).astype(int) if wd.notna().any() else df["weekend"].astype(int)

    ordered = [c for c in feature_names if c in df.columns]
    missing = set(feature_names) - set(ordered)
    if missing:
        raise ValueError(f"Missing required features: {missing}")

    return df[ordered]


def predict(data: dict, artifact: dict | None = None) -> float:
    """Predict ER wait time in minutes from a dict of raw feature values."""
    if artifact is None:
        artifact = load_model()
    x = prepare_input(data, artifact)
    model = artifact["model"]
    pred = model.predict(x)[0]
    return float(round(pred, 1))
