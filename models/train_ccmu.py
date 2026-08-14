#!/usr/bin/env python3
"""Train an XGBoost classifier for CCMU priority suggestion (M2)."""

import json
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

CAT_FEATURES = ["sexe", "mode_arrivee", "tranche_horaire"]
NUM_FEATURES = [
    "age", "score_french", "poids", "temperature",
    "fc", "ta_systolique", "ta_diastolique", "spo2",
    "glasgow_total", "douleur_eva", "jour_semaine", "weekend",
]
TARGET = "score_ccmu"


def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df[TARGET] = df[TARGET].astype(int)
    return df


def main():
    path = DATA_DIR / "dataset_urgences_20k.csv"
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    df = load_data(path)
    print(f"Loaded {len(df)} rows, target distribution:\n{df[TARGET].value_counts().sort_index()}")

    encoders = {}
    for col in CAT_FEATURES:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        encoders[col] = {str(k): int(v) for k, v in zip(le.classes_, le.transform(le.classes_))}

    features = CAT_FEATURES + NUM_FEATURES
    X = df[features].values
    y = df[TARGET].values - 1  # XGBoost expects 0-based classes

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = XGBClassifier(
        n_estimators=400,
        max_depth=8,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        random_state=42,
        eval_metric="mlogloss",
        use_label_encoder=False,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)
    acc = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True)
    cm = confusion_matrix(y_test, y_pred).tolist()

    print(f"\nAccuracy: {acc:.3f}")
    print(f"\nClassification Report:\n{classification_report(y_test, y_pred)}")

    save_path = ARTIFACTS_DIR / "ccmu_model.joblib"
    artifact = {
        "model": model,
        "feature_names": features,
        "cat_features": CAT_FEATURES,
        "num_features": NUM_FEATURES,
        "target_name": TARGET,
        "encoders": encoders,
        "metrics": {
            "accuracy": acc,
            "classification_report": report,
            "confusion_matrix": cm,
        },
        "classes": [1, 2, 3, 4, 5],
    }
    joblib.dump(artifact, save_path)
    with open(ARTIFACTS_DIR / "ccmu_model.json", "w") as f:
        json.dump(artifact["metrics"], f, indent=2)

    print(f"\nModel saved to {save_path}")
    print(f"Metrics saved to {ARTIFACTS_DIR / 'ccmu_model.json'}")

    # Feature importance
    importance = model.feature_importances_
    feat_imp = sorted(zip(features, importance), key=lambda x: -x[1])
    print()
    print("Feature importance:")
    for name, imp in feat_imp:
        print(f"  {name}: {imp:.3f}")


if __name__ == "__main__":
    main()
