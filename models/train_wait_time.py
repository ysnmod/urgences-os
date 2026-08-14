#!/usr/bin/env python3
"""Train a RandomForest regressor on ER wait time data."""

import argparse
import json
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from features import load_raw, engineer_features, get_feature_names, CAT_COLS

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", default="wait_time_model.joblib", help="Artifact filename")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--n-estimators", type=int, default=300)
    parser.add_argument("--max-depth", type=int, default=15)
    parser.add_argument("--min-samples-leaf", type=int, default=5)
    args = parser.parse_args()

    raw = load_raw()

    category_mappings: dict[str, list[str]] = {}
    for col in CAT_COLS:
        if col in raw.columns:
            category_mappings[col] = sorted(raw[col].dropna().unique().tolist())

    feats, target = engineer_features(raw)

    if target is None:
        raise ValueError("No target column found in dataset")

    X_train, X_test, y_train, y_test = train_test_split(
        feats, target, test_size=args.test_size, random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        min_samples_leaf=args.min_samples_leaf,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    print(f"MAE:  {mae:.1f} min")
    print(f"RMSE: {rmse:.1f} min")
    print(f"R²:   {r2:.3f}")

    save_path = ARTIFACTS_DIR / args.save
    artifact = {
        "model": model,
        "feature_names": get_feature_names(),
        "category_mappings": category_mappings,
        "metrics": {"mae": mae, "rmse": rmse, "r2": r2},
    }
    joblib.dump(artifact, save_path)
    with open(save_path.with_suffix(".json"), "w") as f:
        json.dump(artifact["metrics"], f, indent=2)
    print(f"Model saved to {save_path}")


if __name__ == "__main__":
    main()
