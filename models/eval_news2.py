#!/usr/bin/env python3
"""
Comprehensive evaluation of the NEWS2 deterioration alert model (Cas4).

Checks:
1. Per-class precision/recall/F1 + confusion matrix + threshold reappraisal
2. Bias audit: performance by rythme_cardiaque, alerte status, sequence position
3. Calibration: reliability curve + Brier score
4. ROC-AUC + Precision-Recall curve
5. Feature importance (built-in + permutation)
6. Hyperparameter sweep (light)
7. Learning curve
8. Confidence distribution + prediction entropy
9. Summary with auto-flagged concerns
"""

import json
import sys
import joblib
import numpy as np
import pandas as pd
from pathlib import Path

from sklearn.model_selection import (
    train_test_split,
    StratifiedKFold,
    cross_val_score,
    learning_curve,
)
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    roc_auc_score,
    brier_score_loss,
    precision_recall_curve,
    average_precision_score,
)
from sklearn.inspection import permutation_importance
from xgboost import XGBClassifier

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
REPORT_DIR = Path(__file__).resolve().parent / "eval_reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

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

TREND_COLS = ["delta_fc", "delta_spo2", "delta_tas", "delta_gcs", "delta_fr"]
ALL_FEATURES = FEATURE_COLS + TREND_COLS

TARGET = "alerte_next"

np.random.seed(42)


def round4(x):
    return round(float(x), 4)


def load_and_prepare_data(csv_path):
    df = pd.read_csv(csv_path)
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

    X = df[ALL_FEATURES].values
    y = df[TARGET].values

    return X, y, df


def threshold_f1_scan(y_true, y_proba):
    """Find threshold that maximizes F1 for positive class."""
    best_f1, best_th = 0, 0.5
    results = []
    for th in np.linspace(0.1, 0.9, 81):
        y_pred = (y_proba >= th).astype(int)
        tp = ((y_pred == 1) & (y_true == 1)).sum()
        fp = ((y_pred == 1) & (y_true == 0)).sum()
        fn = ((y_pred == 0) & (y_true == 1)).sum()
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
        accuracy = (y_pred == y_true).mean()
        results.append((th, prec, rec, f1, accuracy))
        if f1 > best_f1:
            best_f1 = f1
            best_th = th
    return float(best_th), float(best_f1), results


# ──────────────────────── 1. LOAD MODEL + DATA ────────────────────────

print("=" * 72)
print("  NEWS2 DETERIORATION MODEL — COMPREHENSIVE EVALUATION")
print("=" * 72)

artifact = joblib.load(ARTIFACTS_DIR / "news2_model.joblib")
model: XGBClassifier = artifact["model"]
stored_threshold = artifact.get("threshold", 0.5)
stored_feature_names = artifact["feature_names"]

print(f"\n  Stored threshold: {stored_threshold:.3f}")
print(f"  Stored feature names ({len(stored_feature_names)}): {stored_feature_names}")

data_path = Path(__file__).resolve().parent.parent / "data" / "raw" / "dataset_news2_timeseries_30k.csv"
X, y, df = load_and_prepare_data(data_path)

n_pos = int(y.sum())
n_neg = len(y) - n_pos
print(f"\n📊 Dataset: {len(X)} rows, {len(ALL_FEATURES)} features ({len(df['patient_id'].unique())} patients)")
print(f"   Alerte next step: {n_pos} ({100*n_pos/len(y):.1f}%)")
print(f"   Stable: {n_neg} ({100*n_neg/len(y):.1f}%)")
print(f"   Ratio 1:{n_neg/n_pos:.1f}")

patient_ids = df["patient_id"].values
unique_pids = np.unique(patient_ids)
rng = np.random.RandomState(42)
rng.shuffle(unique_pids)
n_test_pids = int(len(unique_pids) * 0.2)
test_pids = set(unique_pids[:n_test_pids])
test_mask = np.array([pid in test_pids for pid in patient_ids])
X_train, X_test = X[~test_mask], X[test_mask]
y_train, y_test = y[~test_mask], y[test_mask]
df_test = df.iloc[test_mask].copy()
print(f"   Patient-based split: {len(unique_pids)-n_test_pids} train patients ({len(X_train)} rows), "
      f"{n_test_pids} test patients ({len(X_test)} rows)")

# ──────────────────────── 2. BASE METRICS ────────────────────────

print("\n" + "─" * 72)
print("📈 1. BASE METRICS")
print("─" * 72)

y_proba = model.predict_proba(X_test)[:, 1]
y_pred_default = model.predict(X_test)  # default threshold (0.5)
accuracy_default = accuracy_score(y_test, y_pred_default)

print(f"\n   Default threshold (0.5):  accuracy={accuracy_default:.4f}")

# Reappraise threshold
best_th, best_f1, th_results = threshold_f1_scan(y_test, y_proba)
y_pred = (y_proba >= best_th).astype(int)
accuracy_reappraised = accuracy_score(y_test, y_pred)

print(f"   Stored threshold ({stored_threshold:.3f}):  accuracy={accuracy_score(y_test, (y_proba >= stored_threshold).astype(int)):.4f}")
print(f"   Optimal threshold ({best_th:.3f}):  accuracy={accuracy_reappraised:.4f}  F1={best_f1:.4f}")

print(f"\n   Classification Report (threshold={best_th:.3f}):")
print(classification_report(y_test, y_pred, target_names=["Stable", "Alert Soon"]))

cm = confusion_matrix(y_test, y_pred)
cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)
print(f"   Confusion Matrix (rows=true, cols=pred):")
print(f"   TN={cm[0,0]:>5}  FP={cm[0,1]:>5}")
print(f"   FN={cm[1,0]:>5}  TP={cm[1,1]:>5}")
print(f"   Normalized:\n   [[{cm_norm[0,0]:.3f} {cm_norm[0,1]:.3f}]\n    [{cm_norm[1,0]:.3f} {cm_norm[1,1]:.3f}]]")

# False negative analysis (most critical errors — missed alerts)
fn_mask = (y_test == 1) & (y_pred == 0)
n_fn = fn_mask.sum()
print(f"\n   Critical errors (False Negatives = missed alerts): {n_fn}/{int(y_test.sum())} ({100*n_fn/y_test.sum():.1f}%)")
if n_fn > 0:
    fn_probas = y_proba[fn_mask]
    print(f"   Missed alerts — predicted probability range: [{fn_probas.min():.4f}, {fn_probas.max():.4f}]")
    print(f"   Missed alerts — mean probability: {fn_probas.mean():.4f}")

# ──────────────────────── 3. BIAS AUDIT ────────────────────────

print("\n" + "─" * 72)
print("⚖️  2. BIAS AUDIT")
print("─" * 72)

y_test_pred = y_pred
y_test_proba = y_proba
y_test_true = y_test


def evaluate_subgroup(mask, label):
    if mask.sum() < 10:
        return
    y_t = y_test_true[mask]
    y_p = y_test_pred[mask]
    acc = accuracy_score(y_t, y_p)
    # precision/recall for positive class
    tp = ((y_p == 1) & (y_t == 1)).sum()
    fp = ((y_p == 1) & (y_t == 0)).sum()
    fn = ((y_p == 0) & (y_t == 1)).sum()
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0
    print(f"   [{label}]  n={mask.sum():>5}  acc={acc:.4f}  prec={prec:.4f}  recall={rec:.4f}")


# 3a. By rythme cardiaque
print("\n   --- By Rythme ---")
df_test_ryth = df_test["rythme_cardiaque"].values
for rythme in sorted(df_test_ryth.unique()):
    mask = df_test_ryth == rythme
    evaluate_subgroup(mask, f"Rythme={rythme}")

# 3b. By current alert status (alerte at current step)
print("\n   --- By Current Alert Status ---")
for alerte in [0, 1]:
    mask = df_test["alerte_deterioration"].values == alerte
    evaluate_subgroup(mask, f"Alerte actuelle={'Oui' if alerte else 'Non'}")

# 3c. By sequence position (early vs late in the stay)
print("\n   --- By Sequence Position ---")
seq_max = df_test["sequence_step"].max()
df_test["seq_position"] = pd.cut(
    df_test["sequence_step"], bins=[0, 3, 7, seq_max + 1],
    labels=["debut (1-3)", "milieu (4-7)", "fin (8+)"]
)
for grp in ["debut (1-3)", "milieu (4-7)", "fin (8+)"]:
    mask = (df_test["seq_position"] == grp).values
    evaluate_subgroup(mask, f"Pos={grp}")

# ──────────────────────── 4. CALIBRATION ────────────────────────

print("\n" + "─" * 72)
print("🎯 3. CALIBRATION (Brier score)")
print("─" * 72)

brier = brier_score_loss(y_test, y_proba)
print(f"\n   Brier score: {brier:.4f}  (0=perfect, 0.25=coin flip)")

# Mean predicted probability for each true class
for label, label_name in [(0, "Stable"), (1, "Alert Soon")]:
    mask = y_test_true == label
    if mask.sum() > 0:
        mean_prob = y_proba[mask].mean()
        print(f"   {label_name}: mean_pred_prob={mean_prob:.4f}  (expected={label:.1f})")

# ──────────────────────── 5. ROC-AUC + PR-CURVE ────────────────────────

print("\n" + "─" * 72)
print("📉 4. ROC-AUC + PRECISION-RECALL")
print("─" * 72)

roc_auc = roc_auc_score(y_test, y_proba)
pr_auc = average_precision_score(y_test, y_proba)

print(f"\n   ROC-AUC: {roc_auc:.4f}  (random=0.5, perfect=1.0)")
print(f"   Avg Precision (PR-AUC): {pr_auc:.4f}")
print(f"   Positive rate: {y_test.mean():.4f}")
print(f"   Baseline PR-AUC (random): {y_test.mean():.4f}")

# ──────────────────────── 6. CROSS-VALIDATION ────────────────────────

print("\n" + "─" * 72)
print("🔁 5. 3-FOLD CROSS-VALIDATION")
print("─" * 72)

# Cross-val on the full training set for a more robust estimate
cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
# Use model's own params for cv (consistent with train_news2.py approach)
cv_params = model.get_params()
cv_params.pop("early_stopping_rounds", None)
cv_model = XGBClassifier(**cv_params)
cv_scores = cross_val_score(cv_model, X_train, y_train, cv=cv, scoring="roc_auc", n_jobs=1)
print(f"   Fold scores (ROC-AUC): {[round(s, 4) for s in cv_scores]}")
print(f"   Mean CV ROC-AUC: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

# Also compute accuracy-based cv
cv_acc = cross_val_score(cv_model, X_train, y_train, cv=cv, scoring="accuracy", n_jobs=1)
print(f"   Mean CV Accuracy: {cv_acc.mean():.4f} ± {cv_acc.std():.4f}")

# ──────────────────────── 7. FEATURE IMPORTANCE ────────────────────────

print("\n" + "─" * 72)
print("🔬 6. FEATURE IMPORTANCE")
print("─" * 72)

imp = model.feature_importances_
sorted_idx = np.argsort(imp)[::-1]

print(f"\n   --- Model built-in importance ---")
for idx in sorted_idx:
    print(f"   {ALL_FEATURES[idx]:20s}  {imp[idx]:.4f}")

print(f"\n   --- Permutation importance (on test set) ---")
perm_result = permutation_importance(
    model, X_test, y_test, n_repeats=10, random_state=42, n_jobs=1, scoring="roc_auc"
)
perm_imp = perm_result.importances_mean
perm_std = perm_result.importances_std
sorted_perm = np.argsort(perm_imp)[::-1]
for idx in sorted_perm:
    print(f"   {ALL_FEATURES[idx]:20s}  {perm_imp[idx]:.4f} ± {perm_std[idx]:.4f}")

# ──────────────────────── 8. HYPERPARAMETER SWEEP ────────────────────────

print("\n" + "─" * 72)
print("⚙️  7. HYPERPARAMETER SWEEP (light)")
print("─" * 72)

current_params = cv_params  # sanitized (no early_stopping_rounds)

param_grid = {
    "n_estimators": [100, 300, 500],
    "max_depth": [3, 5, 7, 10],
    "learning_rate": [0.04, 0.08, 0.15],
    "subsample": [0.7, 0.8, 1.0],
    "colsample_bytree": [0.7, 0.8, 1.0],
}

results = []
for param_name, values in param_grid.items():
    for val in values:
        params = dict(cv_params)
        params[param_name] = val
        m = XGBClassifier(**params)
        scores = cross_val_score(m, X_train, y_train, cv=3, scoring="roc_auc", n_jobs=1)
        mean_cv = scores.mean()
        results.append((param_name, val, mean_cv))
        delta = mean_cv - cv_scores.mean()
        marker = " ◀ CURRENT" if val == cv_params.get(param_name) else ""
        if abs(delta) > 0.001 or marker:
            print(f"   {param_name}={val:>3}  cv_auc={mean_cv:.4f}  (Δ={delta:+.4f}){marker}")

best_overall = max(results, key=lambda x: x[2])
print(f"\n   Best single-param improvement: {best_overall[0]}={best_overall[1]}  cv_auc={best_overall[2]:.4f}")

# ──────────────────────── 9. LEARNING CURVE ────────────────────────

print("\n" + "─" * 72)
print("📊 8. LEARNING CURVE (ROC-AUC vs training size)")
print("─" * 72)

try:
    train_sizes = np.linspace(0.1, 1.0, 6)
    train_sizes_abs, train_scores, val_scores = learning_curve(
        XGBClassifier(**cv_params),
        X_train, y_train,
        train_sizes=train_sizes,
        cv=3,
        scoring="roc_auc",
        n_jobs=1,
        random_state=42,
    )
    for i, sz in enumerate(train_sizes_abs):
        train_mean = train_scores[i].mean()
        val_mean = val_scores[i].mean()
        print(f"   n_train={int(sz):>6}  train_auc={train_mean:.4f}  val_auc={val_mean:.4f}  gap={train_mean - val_mean:.4f}")
except Exception as e:
    print(f"   Learning curve skipped ({e})")

# ──────────────────────── 10. CONFIDENCE + ENTROPY ────────────────────────

print("\n" + "─" * 72)
print("📊 9. CONFIDENCE DISTRIBUTION + ENTROPY")
print("─" * 72)

# Binary entropy
eps = 1e-12
p1 = y_proba
p0 = 1 - p1
entropy = -(p1 * np.log(p1 + eps) + p0 * np.log(p0 + eps))
print(f"\n   Mean prediction entropy: {entropy.mean():.4f}")
print(f"   Median entropy: {np.median(entropy):.4f}")
print(f"   Q1: {np.percentile(entropy, 25):.4f}, Q3: {np.percentile(entropy, 75):.4f}")
print(f"   High-entropy (>0.5) samples: {(entropy > 0.5).sum()} / {len(entropy)}")

# Max probability as confidence
max_proba = np.maximum(p1, p0)
bins = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0]
print(f"\n   --- Confidence distribution ---")
for i in range(len(bins) - 1):
    lo, hi = bins[i], bins[i + 1]
    mask = (max_proba >= lo) & (max_proba < hi)
    if mask.sum() > 0:
        correct = (y_test_pred[mask] == y_test_true[mask]).mean()
        n_alerts = y_test_true[mask].sum()
        print(f"   confidence [{lo:.2f}-{hi:.2f}): n={mask.sum():>5}  accuracy={correct:.4f}  alerts={int(n_alerts)}")

# ──────────────────────── 11. SUMMARY ────────────────────────

print("\n" + "=" * 72)
print("  EVALUATION SUMMARY")
print("=" * 72)

concerns = []

# Overfit check
val_gap = train_scores[-1].mean() - val_scores[-1].mean() if 'train_scores' in dir() else 0
if val_gap > 0.05:
    concerns.append(f"⚠️  Train/val gap ({val_gap:.4f}) > 0.05 — possible overfit")

# Threshold divergence
if abs(best_th - stored_threshold) > 0.05:
    concerns.append(f"⚠️  Optimal threshold ({best_th:.3f}) differs from stored ({stored_threshold:.3f}) by >0.05")

# False negative rate
fnr = n_fn / max(1, int(y_test.sum()))
if fnr > 0.15:
    concerns.append(f"⚠️  High false-negative rate: {fnr:.1%} — model misses many alerts")

# Calibration
if brier > 0.10:
    concerns.append(f"⚠️  Brier score ({brier:.4f}) > 0.10 — calibration could improve")

# Feature dominance
if imp[sorted_idx[0]] > 0.5:
    concerns.append(f"⚠️  Top feature '{ALL_FEATURES[sorted_idx[0]]}' dominates ({imp[sorted_idx[0]]:.1%})")

# Class imbalance impact
if n_pos / len(y) < 0.05:
    concerns.append(f"⚠️  Very low positive rate ({n_pos/len(y):.1%}) — PR-AUC more relevant than ROC-AUC")

if not concerns:
    print("\n   ✅ No major concerns detected.")
else:
    print(f"\n   🔍 {len(concerns)} concern(s):")
    for c in concerns:
        print(f"   {c}")

print(f"\n   Final test accuracy: {accuracy_reappraised:.4f}")
print(f"   Final threshold: {best_th:.3f}")
print(f"   ROC-AUC: {roc_auc:.4f}")
print(f"   PR-AUC: {pr_auc:.4f}")
print(f"   Brier: {brier:.4f}")
print(f"   CV ROC-AUC: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
print(f"   False-negative rate: {fnr:.1%}")

print(f"\n   Full report saved to: {REPORT_DIR}")
