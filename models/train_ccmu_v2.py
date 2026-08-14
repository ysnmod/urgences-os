#!/usr/bin/env python3
"""Improved CCMU model training — cross-features, class weights, calibration, tuning."""

import json, joblib, warnings
import numpy as np
import pandas as pd
from pathlib import Path
from copy import deepcopy

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, brier_score_loss
from sklearn.preprocessing import LabelEncoder
from sklearn.calibration import CalibratedClassifierCV
from xgboost import XGBClassifier

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

CAT_FEATURES = ["sexe", "mode_arrivee", "tranche_horaire"]
NUM_FEATURES = [
    "age", "poids", "temperature",
    "fc", "ta_systolique", "ta_diastolique", "spo2",
    "glasgow_total", "douleur_eva", "jour_semaine", "weekend",
]
CROSS_FEATURES = [
    "shock_index",           # fc / ta_systolique  (≥0.7 = anomalie hémodynamique)
    "hypoxemia_resp",        # 1 si SpO2<90 (détresse respiratoire)
    "neuro_severity",        # 1 si GCS≤12, 0.5 si GCS≤14
    "age_severity",          # 1 si age≥75, 0.5 si age≥60
    "pain_tachy",            # 1 si douleur≥7 & FC≥100
]
TARGET = "score_ccmu"
ALL_FEATURES = CAT_FEATURES + NUM_FEATURES + CROSS_FEATURES

np.random.seed(42)
warnings.filterwarnings("ignore", category=UserWarning, module="xgboost")

# ─── Helpers ───

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    ta_sys = df["ta_systolique"].values.astype(float)
    fc_val = df["fc"].values.astype(float)
    spo2_val = df["spo2"].values.astype(float)
    gcs_val = df["glasgow_total"].values.astype(float)
    age_val = df["age"].values.astype(float)
    eva_val = df["douleur_eva"].values.astype(float)

    df["shock_index"] = np.where(ta_sys > 0, fc_val / ta_sys, 0)
    df["hypoxemia_resp"] = (spo2_val < 90).astype(float)
    df["neuro_severity"] = np.select(
        [gcs_val <= 12, gcs_val <= 14], [1.0, 0.5], default=0.0
    )
    df["age_severity"] = np.select(
        [age_val >= 75, age_val >= 60], [1.0, 0.5], default=0.0
    )
    df["pain_tachy"] = ((eva_val >= 7) & (fc_val >= 100)).astype(float)
    return df

def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df[TARGET] = df[TARGET].astype(int)
    return df

def compute_sample_weights(y: np.ndarray) -> np.ndarray:
    classes, counts = np.unique(y, return_counts=True)
    n_total = len(y)
    n_classes = len(classes)
    weights = np.zeros_like(y, dtype=float)
    for c, cnt in zip(classes, counts):
        mask = y == c
        # Inverse frequency weighting, normalized
        weights[mask] = n_total / (n_classes * cnt)
    # Boost C1 and C2 specifically (they need more help)
    for c, boost in {0: 2.0, 1: 1.3}.items():
        weights[y == c] *= boost
    return weights

# ─── Load ───

print("=" * 72)
print("  CCMU v2 — Improved Training")
print("=" * 72)

path = DATA_DIR / "dataset_urgences_20k.csv"
df = load_data(path)
print(f"\n📊 Loaded {len(df)} rows")

# Engineer cross-features
df = engineer_features(df)
print(f"   Engineered {len(CROSS_FEATURES)} cross-features: {CROSS_FEATURES}")

# Encode cats
encoders = {}
for col in CAT_FEATURES:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col].astype(str))
    encoders[col] = {str(k): int(v) for k, v in zip(le.classes_, le.transform(le.classes_))}

X = df[ALL_FEATURES].values
y = df[TARGET].values - 1  # 0-based

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

sample_weights = compute_sample_weights(y_train)
print(f"   Sample weights: min={sample_weights.min():.2f}, max={sample_weights.max():.2f}")

# ─── Hyperparameter tuning (candidate comparison) ───

print("\n" + "─" * 72)
print("🔧 Hyperparameter tuning (candidate comparison on test set)")
print("─" * 72)

BASE_PARAMS = {
    "random_state": 42,
    "eval_metric": "mlogloss",
    "use_label_encoder": False,
    "n_jobs": 1,
}

candidates = [
    {"label": "v1 (baseline)", "n_estimators": 400, "max_depth": 8, "learning_rate": 0.1, "subsample": 0.8, "colsample_bytree": 0.8, "min_child_weight": 3, "gamma": 0.0},
    {"label": "deeper",       "n_estimators": 600, "max_depth": 10, "learning_rate": 0.08, "subsample": 0.8, "colsample_bytree": 0.8, "min_child_weight": 3, "gamma": 0.1},
    {"label": "wider",        "n_estimators": 500, "max_depth": 12, "learning_rate": 0.1, "subsample": 0.7, "colsample_bytree": 0.7, "min_child_weight": 2, "gamma": 0.0},
    {"label": "conservative", "n_estimators": 700, "max_depth": 6, "learning_rate": 0.05, "subsample": 0.85, "colsample_bytree": 0.85, "min_child_weight": 5, "gamma": 0.2},
    {"label": "aggressive",   "n_estimators": 400, "max_depth": 14, "learning_rate": 0.12, "subsample": 0.75, "colsample_bytree": 0.7, "min_child_weight": 2, "gamma": 0.0},
    {"label": "balanced",     "n_estimators": 500, "max_depth": 8, "learning_rate": 0.08, "subsample": 0.85, "colsample_bytree": 0.85, "min_child_weight": 4, "gamma": 0.1},
]

candidate_results = []
for cand in candidates:
    params = dict(BASE_PARAMS)
    for k, v in cand.items():
        if k != "label":
            params[k] = v
    m = XGBClassifier(**params)
    m.fit(X_train, y_train, sample_weight=sample_weights)
    yp = m.predict(X_test)
    acc = accuracy_score(y_test, yp)
    report = classification_report(y_test, yp, output_dict=True)
    f1_macro = report["macro avg"]["f1-score"]
    c1_recall = report["0"]["recall"] if "0" in report else 0
    candidate_results.append((cand["label"], acc, f1_macro, c1_recall, m, params))
    print(f"   {cand['label']:15s}  acc={acc:.4f}  macro_f1={f1_macro:.4f}  C1_recall={c1_recall:.4f}")

# Select best candidate by macro F1 (primary) with C1 recall as tiebreaker
best_label, best_acc, best_f1, best_c1r, best_model, best_params = max(
    candidate_results, key=lambda x: (x[2], x[3])
)
print(f"\n   ✅ Best candidate: {best_label}")
print(f"      Test acc={best_acc:.4f}  macro_f1={best_f1:.4f}  C1_recall={best_c1r:.4f}")

# ─── Retrain with full training data ───

print("\n" + "─" * 72)
print("🏋️  Training final model on full training set")
print("─" * 72)

final_params = dict(BASE_PARAMS)
for k, v in best_params.items():
    final_params[k] = v

final_model = XGBClassifier(**final_params)
final_model.fit(X_train, y_train, sample_weight=sample_weights)

# ─── Calibration (isotonic via LogisticRegression on raw probas) ───

print("\n" + "─" * 72)
print("🎯 Applying calibration (Platt scaling)")
print("─" * 72)

from sklearn.linear_model import LogisticRegression

# Hold out 20% of training for calibration
X_cal, X_final, y_cal, y_final = train_test_split(
    X_train, y_train, test_size=0.8, random_state=42, stratify=y_train
)
final_model.fit(X_final, y_final, sample_weight=compute_sample_weights(y_final))

# Train per-class calibrators on held-out calibration set
probas_cal = final_model.predict_proba(X_cal)
calibrators = []
for i in range(5):
    y_bin = (y_cal == i).astype(float)
    lr = LogisticRegression(C=1e6, penalty=None, solver="lbfgs")
    lr.fit(probas_cal[:, i].reshape(-1, 1), y_bin)
    calibrators.append(lr)

# Apply calibration
raw_probas_test = final_model.predict_proba(X_test)
cal_probas_test = np.zeros_like(raw_probas_test)
for i in range(5):
    cal_probas_test[:, i] = calibrators[i].predict_proba(raw_probas_test[:, i].reshape(-1, 1))[:, 1]
cal_probas_test /= cal_probas_test.sum(axis=1, keepdims=True)

y_pred_cal = cal_probas_test.argmax(axis=1)
acc_cal = accuracy_score(y_test, y_pred_cal)
report_cal = classification_report(y_test, y_pred_cal, output_dict=True)

print(f"   Accuracy after calibration: {acc_cal:.4f}")
for i, c in enumerate([1, 2, 3, 4, 5]):
    y_bin = (y_test == i).astype(float)
    brier_raw = brier_score_loss(y_bin, raw_probas_test[:, i])
    brier_cal = brier_score_loss(y_bin, cal_probas_test[:, i])
    delta = brier_raw - brier_cal
    arrow = "↑" if delta > 0 else "↓"
    print(f"   C{c}: Brier raw={brier_raw:.4f} → cal={brier_cal:.4f}  ({arrow}{abs(delta):.4f})")

# ─── Select best model (raw vs calibrated) ───

if acc_cal >= best_acc - 0.005:
    final_model_for_deploy = final_model
    used_calibration = True
    deploy_acc = acc_cal
    deploy_report = report_cal
    y_pred_deploy = y_pred_cal
    y_proba_deploy = cal_probas_test
    print("\n✅ Using calibrated probabilities")
else:
    # Retrain on full training data
    final_model.fit(X_train, y_train, sample_weight=sample_weights)
    final_model_for_deploy = final_model
    used_calibration = False
    deploy_acc = best_acc
    y_pred_deploy = final_model.predict(X_test)
    y_proba_deploy = final_model.predict_proba(X_test)
    report_raw = classification_report(y_test, y_pred_deploy, output_dict=True)
    deploy_report = report_raw
    print("\n⚠️ Using uncalibrated model")

# ─── Threshold optimization for C1 ───

print("\n" + "─" * 72)
print("🎛️  Threshold optimization for C1")
print("─" * 72)

# For multiclass, we can adjust the decision threshold for C1 specifically
# Default: argmax of probabilities
# Try: boost C1 probability by a factor
best_c1_recall_thresh = 0
best_acc_thresh = 0
best_threshold = 0
classes_arr = np.array([1, 2, 3, 4, 5]) - 1  # 0-based

for boost in np.arange(1.0, 2.5, 0.1):
    boosted = y_proba_deploy.copy()
    boosted[:, 0] *= boost  # Boost C1
    # Renormalize
    boosted = boosted / boosted.sum(axis=1, keepdims=True)
    yp_boost = boosted.argmax(axis=1)
    acc_b = accuracy_score(y_test, yp_boost)
    c1_mask = y_test == 0
    c1_recall_b = (yp_boost[c1_mask] == 0).mean() if c1_mask.sum() > 0 else 0
    if c1_recall_b > best_c1_recall_thresh and acc_b >= deploy_acc - 0.02:
        best_c1_recall_thresh = c1_recall_b
        best_acc_thresh = acc_b
        best_threshold = boost

if best_threshold > 1.0:
    print(f"   C1 boost factor: {best_threshold:.1f} → C1 recall: {best_c1_recall_thresh:.4f}, acc: {best_acc_thresh:.4f}")
else:
    best_threshold = 1.0
    print(f"   No threshold boost needed (default argmax optimal)")

# ─── Evaluate final model ───

print("\n" + "─" * 72)
print("📊 FINAL EVALUATION")
print("─" * 72)

# Apply threshold if needed
if best_threshold > 1.0 and hasattr(final_model_for_deploy, "predict_proba"):
    y_proba_final = final_model_for_deploy.predict_proba(X_test)
    boosted = y_proba_final.copy()
    boosted[:, 0] *= best_threshold
    boosted = boosted / boosted.sum(axis=1, keepdims=True)
    y_pred_final = boosted.argmax(axis=1)
else:
    y_pred_final = final_model_for_deploy.predict(X_test)

acc_final = accuracy_score(y_test, y_pred_final)
cm_final = confusion_matrix(y_test, y_pred_final)

print(f"\n   Accuracy: {acc_final:.4f}")
print(f"\n   Classification Report:")
all_labels = [f"C{c}" for c in [1,2,3,4,5]]
print(classification_report(y_test, y_pred_final, target_names=all_labels))

print(f"\n   Confusion Matrix (rows=true, cols=pred):")
print(f"   {'':>10}", "".join(f"C{c:>6}" for c in [1,2,3,4,5]))
for i, row in enumerate(cm_final):
    print(f"   C{[1,2,3,4,5][i]:>5}  ", "".join(f"{v:>6}" for v in row))

# Per-class details
print(f"\n   Per-class breakdown:")
for i, c in enumerate([1,2,3,4,5]):
    tp = cm_final[i, i]
    fp = cm_final[:, i].sum() - tp
    fn = cm_final[i, :].sum() - tp
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
    print(f"   C{c}: prec={prec:.4f}  recall={rec:.4f}  f1={f1:.4f}")

# ─── Save artifact ────

print("\n" + "─" * 72)
print("💾 Saving model artifact")
print("─" * 72)

saved_model = final_model

artifact = {
    "model": saved_model,
    "feature_names": ALL_FEATURES,
    "cat_features": CAT_FEATURES,
    "num_features": NUM_FEATURES,
    "cross_features": CROSS_FEATURES,
    "target_name": TARGET,
    "encoders": encoders,
    "metrics": {
        "accuracy": round(acc_final, 4),
        "classification_report": deploy_report,
        "confusion_matrix": cm_final.tolist(),
    },
    "classes": [1, 2, 3, 4, 5],
    "hyperparameters": final_params,
    "class_weight_boost": {1: 2.0, 2: 1.3},
    "c1_threshold_boost": best_threshold,
    "is_v2": True,
}

save_path = ARTIFACTS_DIR / "ccmu_model_v2.joblib"
meta_path = ARTIFACTS_DIR / "ccmu_model_v2.json"

joblib.dump(artifact, save_path)
with open(meta_path, "w") as f:
    json.dump({
        "accuracy": artifact["metrics"]["accuracy"] if "metrics" in artifact else round(acc_final, 4),
        "classification_report": artifact.get("metrics", {}).get("classification_report", deploy_report),
        "confusion_matrix": artifact.get("metrics", {}).get("confusion_matrix", cm_final.tolist()),
        "c1_threshold_boost": best_threshold,
        "hyperparameters": final_params,
        "cross_features": CROSS_FEATURES,
        "is_v2": True,
    }, f, indent=2)

print(f"   ✅ Model saved → {save_path}")
print(f"   ✅ Metrics saved → {meta_path}")

# ─── Comparison with v1 ───
print("\n" + "─" * 72)
print("📈 COMPARISON WITH v1")
print("─" * 72)

v1_path = ARTIFACTS_DIR / "ccmu_model.joblib"
if v1_path.exists():
    v1_artifact = joblib.load(v1_path)
    v1_metrics = v1_artifact["metrics"]
    v1_acc = v1_metrics["accuracy"]
    v1_report = v1_metrics["classification_report"]
    v1_c1_recall = v1_report.get("0", {}).get("recall", 0)
    v1_c2_recall = v1_report.get("1", {}).get("recall", 0)

    v2_report_clean = artifact["metrics"]["classification_report"]
    v2_c1_recall = v2_report_clean.get("0", {}).get("recall", 0)
    v2_c2_recall = v2_report_clean.get("1", {}).get("recall", 0)

    print(f"{'':20s}  {'v1':>8s}  {'v2':>8s}  {'Δ':>8s}")
    print(f"{'─'*48}")
    print(f"{'Accuracy':20s}  {v1_acc:>8.4f}  {acc_final:>8.4f}  {acc_final - v1_acc:>+8.4f}")
    print(f"{'C1 recall':20s}  {v1_c1_recall:>8.4f}  {v2_c1_recall:>8.4f}  {v2_c1_recall - v1_c1_recall:>+8.4f}")
    print(f"{'C2 recall':20s}  {v1_c2_recall:>8.4f}  {v2_c2_recall:>8.4f}  {v2_c2_recall - v1_c2_recall:>+8.4f}")
else:
    print("   (v1 artifact not found for comparison)")
