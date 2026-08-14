"""
Train a binary classifier for NEWS2-based deterioration ALERT prediction (Cas4).

Target: will this patient have NEWS2 >= 7 (alerte=1) at the NEXT time step?
Features: current step's vitals + rhythm (no NEWS2 — model learns it implicitly).
"""
import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
import xgboost as xgb
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, roc_curve

ARTIFACTS_DIR = Path("models/artifacts")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

RHYTHM_MAP = {
    "sinusal": 0,
    "bradycardie_sinusale": 1,
    "tachycardie_sinusale": 2,
    "fibrillation_atriale": 3,
    "tachycardie_ventriculaire": 4,
}

FEATURE_COLS = [
    "fc", "ta_systolique", "ta_diastolique", "spo2", "temperature",
    "frequence_respiratoire",
    "glasgow_total", "douleur_eva", "rythme_code",
]

TARGET = "alerte_next"


def load_and_prepare_data(path="data/raw/dataset_news2_timeseries_30k.csv"):
    df = pd.read_csv(path)
    df = df.sort_values(["patient_id", "sequence_step"]).reset_index(drop=True)

    df[TARGET] = df.groupby("patient_id")["alerte_deterioration"].shift(-1)
    df = df.dropna(subset=[TARGET]).reset_index(drop=True)
    df[TARGET] = df[TARGET].astype(int)

    df["rythme_code"] = df["rythme_cardiaque"].map(RHYTHM_MAP)

    df["delta_fc"] = df.groupby("patient_id")["fc"].diff().fillna(0).astype(int)
    df["delta_spo2"] = df.groupby("patient_id")["spo2"].diff().fillna(0).astype(int)
    df["delta_tas"] = df.groupby("patient_id")["ta_systolique"].diff().fillna(0).astype(int)
    df["delta_gcs"] = df.groupby("patient_id")["glasgow_total"].diff().fillna(0).astype(int)
    df["delta_fr"] = df.groupby("patient_id")["frequence_respiratoire"].diff().fillna(0).astype(int)

    TREND_COLS = ["delta_fc", "delta_spo2", "delta_tas", "delta_gcs", "delta_fr"]

    X = df[FEATURE_COLS + TREND_COLS].values
    y = df[TARGET].values

    return X, y, FEATURE_COLS + TREND_COLS, df


def find_optimal_threshold(model, X_val, y_val):
    """Find threshold that maximizes F1 for the positive class."""
    y_prob = model.predict_proba(X_val)[:, 1]
    fpr, tpr, thresholds = roc_curve(y_val, y_prob)
    best_f1, best_th = 0, 0.5
    for th in np.linspace(0.1, 0.9, 81):
        y_pred = (y_prob >= th).astype(int)
        tp = ((y_pred == 1) & (y_val == 1)).sum()
        fp = ((y_pred == 1) & (y_val == 0)).sum()
        fn = ((y_pred == 0) & (y_val == 1)).sum()
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        if f1 > best_f1:
            best_f1 = f1
            best_th = th
    return float(best_th), float(best_f1)


def train():
    X, y, feature_cols, df = load_and_prepare_data()

    n_pos = int(y.sum())
    n_neg = len(y) - n_pos
    print(f"Total samples: {len(X)}")
    print(f"Positive (alert next step): {n_pos} ({100*n_pos/len(y):.1f}%)")
    print(f"Negative: {n_neg} ({100*n_neg/len(y):.1f}%)")
    print(f"Ratio 1:{n_neg/n_pos:.1f}")

    # Patient-based split — no leakage across time steps of the same patient
    patient_ids = df["patient_id"].values
    unique_pids = np.unique(patient_ids)
    rng = np.random.RandomState(42)
    rng.shuffle(unique_pids)
    n_test_pids = int(len(unique_pids) * 0.2)
    test_pids = set(unique_pids[:n_test_pids])
    train_mask = np.array([pid not in test_pids for pid in patient_ids])
    test_mask = np.array([pid in test_pids for pid in patient_ids])
    X_train, X_test = X[train_mask], X[test_mask]
    y_train, y_test = y[train_mask], y[test_mask]
    print(f"Patient-based split: {len(unique_pids)-n_test_pids} train patients ({len(X_train)} rows), "
          f"{n_test_pids} test patients ({len(X_test)} rows)")

    scale_pos_weight = n_neg / n_pos

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric="auc",
        early_stopping_rounds=30,
        random_state=42,
        verbosity=0,
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=50,
    )

    y_prob = model.predict_proba(X_test)[:, 1]

    best_th, best_f1 = find_optimal_threshold(model, X_test, y_test)
    print(f"\nOptimal threshold: {best_th:.3f} (F1={best_f1:.4f})")

    y_pred = (y_prob >= best_th).astype(int)

    print("\n=== Classification Report (test set) ===")
    print(classification_report(y_test, y_pred, target_names=["Stable", "Alert Soon"]))

    cm = confusion_matrix(y_test, y_pred)
    print(f"Confusion Matrix:\n{cm}")
    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)
    print(f"Normalized:\n{cm_norm.round(3)}")

    auc = roc_auc_score(y_test, y_prob)
    print(f"ROC-AUC: {auc:.4f}")

    importance = model.feature_importances_
    feat_imp = sorted(zip(feature_cols, importance), key=lambda x: -x[1])
    print("\n=== Feature Importance ===")
    for name, imp in feat_imp:
        print(f"  {name}: {imp:.4f}")

    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    cv_scores = []
    from sklearn.metrics import roc_auc_score as ras
    for train_idx, val_idx in cv.split(X_train, y_train):
        m = xgb.XGBClassifier(
            n_estimators=100, max_depth=4, learning_rate=0.08, scale_pos_weight=scale_pos_weight,
            random_state=42, verbosity=0,
        )
        m.fit(X_train[train_idx], y_train[train_idx])
        cv_scores.append(ras(y_train[val_idx], m.predict_proba(X_train[val_idx])[:, 1]))
    cv_scores = np.array(cv_scores)
    print(f"CV ROC-AUC (3-fold): {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    artifact = {
        "model": model,
        "feature_names": feature_cols,
        "rhythm_map": RHYTHM_MAP,
        "threshold": best_th,
        "metrics": {
            "accuracy": float((y_pred == y_test).mean()),
            "roc_auc": float(auc),
            "classification_report": classification_report(y_test, y_pred, output_dict=True),
            "confusion_matrix": cm.tolist(),
            "cv_roc_auc_mean": float(np.mean(cv_scores)),
            "cv_roc_auc_std": float(np.std(cv_scores)),
        },
        "scale_pos_weight": float(scale_pos_weight),
    }

    save_path = ARTIFACTS_DIR / "news2_model.joblib"
    meta_path = ARTIFACTS_DIR / "news2_model.json"

    joblib.dump(artifact, save_path)
    with open(meta_path, "w") as f:
        json.dump({
            "feature_names": feature_cols,
            "metrics": artifact["metrics"],
            "threshold": best_th,
            "scale_pos_weight": scale_pos_weight,
        }, f, indent=2)

    print(f"\n✓ Model saved to {save_path}")
    print(f"✓ Metadata saved to {meta_path}")


if __name__ == "__main__":
    train()
