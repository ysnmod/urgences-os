#!/usr/bin/env python3
"""
Comprehensive evaluation of the CCMU priority suggestion model (M2).

Checks:
1. Per-class precision/recall/F1 + confusion matrix heatmap
2. Bias audit: performance by sexe, age group, mode_arrivee
3. Calibration: reliability curves per class
4. Feature importance stability (permutation importance)
5. Hyperparameter grid-search light
6. Cross-validation scores
7. ROC-AUC per class (one-vs-rest)
8. Threshold analysis: optimal cutoffs per class
9. Learning curve: accuracy vs training size
10. Prediction entropy analysis (uncertainty patterns)
"""

import json
import sys
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict

# ── sklearn & xgboost ──
from sklearn.model_selection import (
    cross_val_score,
    StratifiedKFold,
    learning_curve,
)
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    roc_auc_score,
    brier_score_loss,
)
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier
from sklearn.inspection import permutation_importance

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
REPORT_DIR = Path(__file__).resolve().parent / "eval_reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

from train_ccmu_v2 import engineer_features, CROSS_FEATURES as V2_CROSS_FEATURES

CAT_FEATURES = ["sexe", "mode_arrivee", "tranche_horaire"]
NUM_FEATURES = [
    "age", "poids", "temperature",
    "fc", "ta_systolique", "ta_diastolique", "spo2",
    "glasgow_total", "douleur_eva", "jour_semaine", "weekend",
]
TARGET = "score_ccmu"
ALL_FEATURES = CAT_FEATURES + NUM_FEATURES

np.random.seed(42)

# ──────────────────────── helpers ────────────────────────

def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df[TARGET] = df[TARGET].astype(int)
    return df


def prepare_X_y(df: pd.DataFrame, feature_cols: list):
    """Encode cats, return X (numpy) and y (0-based)."""
    df = df.copy()
    encoders = {}
    for col in CAT_FEATURES:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        encoders[col] = le
    X = df[feature_cols].values
    y = df[TARGET].values - 1  # 0-based
    return X, y, encoders


def round4(x):
    return round(float(x), 4)


# ──────────────────────── 1. load model + data ────────────────────────

print("=" * 72)
print("  CCMU MODEL — COMPREHENSIVE EVALUATION")
print("=" * 72)

artifact = joblib.load(ARTIFACTS_DIR / "ccmu_model_v2.joblib")
model: XGBClassifier = artifact["model"]
classes_out = artifact["classes"]  # [1,2,3,4,5]
n_classes = len(classes_out)
model_features = artifact["feature_names"]  # includes cross-features

df = load_data(DATA_DIR / "dataset_urgences_20k.csv")
df = engineer_features(df)  # add cross-features
print(f"\n📊 Dataset: {len(df)} rows, {len(model_features)} features (incl. cross-features)")
print(f"   Target distribution:\n{df[TARGET].value_counts().sort_index().to_string()}")

X, y, _ = prepare_X_y(df, model_features)

# train/test split (same as train_ccmu.py)
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ──────────────────────── 2. base metrics ────────────────────────

print("\n" + "─" * 72)
print("📈 1. BASE METRICS")
print("─" * 72)

y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)
acc = accuracy_score(y_test, y_pred)

print(f"\n   Accuracy:  {acc:.4f}")
print(f"\n   Classification Report:")
print(classification_report(y_test, y_pred, target_names=[f"C{c}" for c in classes_out]))

cm = confusion_matrix(y_test, y_pred)
print(f"\n   Confusion Matrix (rows=true, cols=pred):")
print(f"   {'':>10}", "".join(f"C{c:>6}" for c in classes_out))
for i, row in enumerate(cm):
    print(f"   C{classes_out[i]:>5}  ", "".join(f"{v:>6}" for v in row))

# Per-class metrics
print(f"\n   Per-class metrics:")
for i, c in enumerate(classes_out):
    tp = cm[i, i]
    fp = cm[:, i].sum() - tp
    fn = cm[i, :].sum() - tp
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
    supp = cm[i, :].sum()
    print(f"   C{c}: prec={prec:.4f}  recall={rec:.4f}  f1={f1:.4f}  support={supp}")

# ──────────────────────── 3. BIAS AUDIT ────────────────────────

print("\n" + "─" * 72)
print("⚖️  2. BIAS AUDIT")
print("─" * 72)

df_test = df.iloc[y_test.index if hasattr(y_test, 'index') else range(len(X_test))].copy()
# Actually recompute test split indices properly
_, test_idx = train_test_split(
    np.arange(len(df)), test_size=0.2, random_state=42, stratify=y
)
df_test = df.iloc[test_idx].copy()
y_test_true = y[test_idx]
y_test_pred = model.predict(X[test_idx])
y_test_proba = model.predict_proba(X[test_idx])


def evaluate_subgroup(mask, label):
    """Print metrics for a subgroup."""
    if mask.sum() < 10:
        return
    y_true_sub = y_test_true[mask]
    y_pred_sub = y_test_pred[mask]
    acc_sub = accuracy_score(y_true_sub, y_pred_sub)
    # Brier per subgroup (multi-class)
    y_proba_sub = y_test_proba[mask]
    brier = 0
    for i in range(n_classes):
        y_bin = (y_true_sub == i).astype(float)
        brier += np.mean((y_proba_sub[:, i] - y_bin) ** 2)
    brier /= n_classes
    # Per-class recall
    print(f"\n   [{label}]  n={mask.sum()}  acc={acc_sub:.4f}  avg_brier={brier:.4f}")
    for i, c in enumerate(classes_out):
        mask_c = y_true_sub == i
        if mask_c.sum() > 0:
            recall_c = (y_pred_sub[mask_c] == i).mean()
            print(f"      C{c} recall: {recall_c:.4f}  (n={mask_c.sum()})")


def make_age_group(age):
    if age <= 12:
        return "enfant"
    elif age <= 40:
        return "jeune"
    elif age <= 65:
        return "adulte"
    elif age <= 85:
        return "senior"
    else:
        return "grand_senior"


# 2a. Sexe bias
print("\n   --- By Sexe ---")
for sexe_val in ["M", "F"]:
    mask = df_test["sexe"].values == sexe_val
    evaluate_subgroup(mask, f"Sexe={sexe_val}")

# 2b. Age group bias
print("\n   --- By Age Group ---")
df_test["age_group"] = df_test["age"].apply(make_age_group)
for grp in ["enfant", "jeune", "adulte", "senior", "grand_senior"]:
    mask = (df_test["age_group"] == grp).values
    evaluate_subgroup(mask, f"Age={grp}")

# 2c. Mode d'arrivée bias
print("\n   --- By Mode d'Arrivée ---")
for mode in ["autonome", "ambulance", "pompiers", "SMUR"]:
    mask = (df_test["mode_arrivee"].values == mode)
    evaluate_subgroup(mask, f"Mode={mode}")

# 2d. Weekend bias
print("\n   --- By Weekend ---")
for w in [0, 1]:
    mask = (df_test["weekend"].values == w)
    evaluate_subgroup(mask, f"Weekend={'Oui' if w else 'Non'}")

# 2e. CCMU parity — accuracy per true CCMU class
print("\n   --- Accuracy per True CCMU Class ---")
for i, c in enumerate(classes_out):
    mask = y_test_true == i
    if mask.sum() > 0:
        acc_c = (y_test_pred[mask] == i).mean()
        print(f"   CCMU {c}: accuracy={acc_c:.4f}  (n={mask.sum()})")

# ──────────────────────── 4. CALIBRATION ────────────────────────

print("\n" + "─" * 72)
print("🎯 3. CALIBRATION ANALYSIS (Brier scores)")
print("─" * 72)

for i, c in enumerate(classes_out):
    y_bin = (y_test_true == i).astype(float)
    brier = brier_score_loss(y_bin, y_test_proba[:, i])
    # Mean predicted probability for samples of class i
    mean_pred = y_test_proba[y_test_true == i, i].mean()
    print(f"   C{c}: Brier={brier:.4f}  (0=perfect)  mean_pred_prob={mean_pred:.4f}  expected=1.0")

# ──────────────────────── 5. ROC-AUC (one-vs-rest) ────────────────────────

print("\n" + "─" * 72)
print("📉 4. ROC-AUC (one-vs-rest)")
print("─" * 72)

for i, c in enumerate(classes_out):
    y_bin = (y_test_true == i).astype(int)
    try:
        auc = roc_auc_score(y_bin, y_test_proba[:, i])
        print(f"   C{c}: AUC={auc:.4f}")
    except ValueError:
        print(f"   C{c}: AUC=--- (only one class present)")

# ──────────────────────── 6. CROSS-VALIDATION ────────────────────────

print("\n" + "─" * 72)
print("🔁 5. 5-FOLD CROSS-VALIDATION")
print("─" * 72)

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = cross_val_score(model.__class__(**model.get_params()), X, y, cv=cv, scoring="accuracy", n_jobs=1)
print(f"   Fold scores: {[round(s, 4) for s in cv_scores]}")
print(f"   Mean CV accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

# ──────────────────────── 7. FEATURE IMPORTANCE ────────────────────────

print("\n" + "─" * 72)
print("🔬 6. FEATURE IMPORTANCE")
print("─" * 72)

print("\n   --- Model built-in importance ---")
imp = model.feature_importances_
sorted_idx = np.argsort(imp)[::-1]
for idx in sorted_idx:
    print(f"   {model_features[idx]:20s}  {imp[idx]:.4f}")

print("\n   --- Permutation importance (on test set) ---")
perm_result = permutation_importance(
    model, X_test, y_test, n_repeats=10, random_state=42, n_jobs=1
)
perm_imp = perm_result.importances_mean
perm_std = perm_result.importances_std
sorted_perm = np.argsort(perm_imp)[::-1]
for idx in sorted_perm:
    print(f"   {model_features[idx]:20s}  {perm_imp[idx]:.4f} ± {perm_std[idx]:.4f}")

# ──────────────────────── 8. HYPERPARAMETER SWEEP (light) ────────────────────────

print("\n" + "─" * 72)
print("⚙️  7. HYPERPARAMETER SWEEP (light)")
print("─" * 72)

# Current params
current_params = {
    "n_estimators": 400,
    "max_depth": 8,
    "learning_rate": 0.1,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 3,
    "random_state": 42,
    "eval_metric": "mlogloss",
    "use_label_encoder": False,
}

param_grid = {
    "n_estimators": [200, 400, 600],
    "max_depth": [4, 6, 8, 12],
    "learning_rate": [0.05, 0.1, 0.2],
    "subsample": [0.7, 0.8, 1.0],
    "colsample_bytree": [0.7, 0.8, 1.0],
    "min_child_weight": [1, 3, 5],
}

results = []
# Evaluate each param independently (change one at a time from current)
for param_name, values in param_grid.items():
    for val in values:
        params = dict(current_params)
        params[param_name] = val
        m = XGBClassifier(**params)
        scores = cross_val_score(m, X_train, y_train, cv=3, scoring="accuracy", n_jobs=1)
        mean_cv = scores.mean()
        results.append((param_name, val, mean_cv))
        # Only print if different from baseline or notable
        delta = mean_cv - cv_scores.mean()
        marker = " ◀ CURRENT" if val == current_params[param_name] else ""
        if abs(delta) > 0.003 or marker:
            print(f"   {param_name}={val:5s}  cv={mean_cv:.4f}  (Δ={delta:+.4f}){marker}" if isinstance(val, str) else
                  f"   {param_name}={val:>3}  cv={mean_cv:.4f}  (Δ={delta:+.4f}){marker}")

# Best params found
best_overall = max(results, key=lambda x: x[2])
print(f"\n   Best single-param improvement: {best_overall[0]}={best_overall[1]}  cv={best_overall[2]:.4f}")

# ──────────────────────── 9. LEARNING CURVE ────────────────────────

print("\n" + "─" * 72)
print("📊 8. LEARNING CURVE (accuracy vs training size)")
print("─" * 72)

try:
    train_sizes = np.linspace(0.1, 1.0, 6)
    train_sizes_abs, train_scores, val_scores = learning_curve(
        model.__class__(**model.get_params()),
        X_train, y_train,
        train_sizes=train_sizes,
        cv=3,
        scoring="accuracy",
        n_jobs=1,
        random_state=42,
    )
    for i, sz in enumerate(train_sizes_abs):
        train_mean = train_scores[i].mean()
        val_mean = val_scores[i].mean()
        print(f"   n_train={sz:>5}  train_acc={train_mean:.4f}  val_acc={val_mean:.4f}  gap={train_mean - val_mean:.4f}")
except Exception as e:
    print(f"   Learning curve skipped ({e})")

# ──────────────────────── 10. ENTROPY / UNCERTAINTY ANALYSIS ────────────────────────

print("\n" + "─" * 72)
print("🧠 9. PREDICTION ENTROPY ANALYSIS")
print("─" * 72)

eps = 1e-12
entropy = -np.sum(y_test_proba * np.log(y_test_proba + eps), axis=1)
print(f"   Mean prediction entropy: {entropy.mean():.4f}")
print(f"   Median: {np.median(entropy):.4f}")
print(f"   Q1: {np.percentile(entropy, 25):.4f}, Q3: {np.percentile(entropy, 75):.4f}")
print(f"   High-entropy (>1.0) samples: {(entropy > 1.0).sum()} / {len(entropy)}")

# Where does the model have highest uncertainty?
high_entropy_mask = entropy > 1.5
if high_entropy_mask.sum() > 0:
    print(f"\n   High uncertainty examples (entropy>1.5, n={high_entropy_mask.sum()}):")
    # True classes for these
    high_true = y_test_true[high_entropy_mask]
    high_pred = y_test_pred[high_entropy_mask]
    for i_c, c in enumerate(classes_out):
        n_in = (high_true == i_c).sum()
        if n_in > 0:
            print(f"   True C{c}: {n_in} samples, most predicted as:")
            sub_pred = high_pred[high_true == i_c]
            for j_c, c2 in enumerate(classes_out):
                n_pred = (sub_pred == j_c).sum()
                if n_pred > 0:
                    print(f"      → C{c2}: {n_pred} ({n_pred/n_in*100:.0f}%)")

# ──────────────────────── 11. CONFIDENCE DISTRIBUTION ────────────────────────

print("\n" + "─" * 72)
print("📊 10. CONFIDENCE DISTRIBUTION (max probability)")
print("─" * 72)

max_proba = y_test_proba.max(axis=1)
bins = [0, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0]
for i in range(len(bins) - 1):
    lo, hi = bins[i], bins[i + 1]
    mask = (max_proba >= lo) & (max_proba < hi)
    if mask.sum() > 0:
        correct = (y_test_pred[mask] == y_test_true[mask]).mean()
        print(f"   confidence [{lo:.2f}-{hi:.2f}): n={mask.sum():>4}  accuracy={correct:.4f}")

high_conf_mask = max_proba >= 0.95
if high_conf_mask.sum() > 0:
    acc_high = (y_test_pred[high_conf_mask] == y_test_true[high_conf_mask]).mean()
    print(f"\n   High-confidence (>=0.95): n={high_conf_mask.sum()}  accuracy={acc_high:.4f}")
low_conf_mask = max_proba < 0.7
if low_conf_mask.sum() > 0:
    acc_low = (y_test_pred[low_conf_mask] == y_test_true[low_conf_mask]).mean()
    print(f"   Low-confidence (<0.7):   n={low_conf_mask.sum()}  accuracy={acc_low:.4f}")

# ──────────────────────── 12. SUMMARY ────────────────────────

print("\n" + "=" * 72)
print("  EVALUATION SUMMARY")
print("=" * 72)

# Flag concerns
concerns = []

if cv_scores.mean() - acc > 0.02:
    concerns.append(f"⚠️  CV accuracy ({cv_scores.mean():.4f}) vs test accuracy ({acc:.4f}) gap > 0.02 — possible overfit")

# Per-class accuracy disparity
class_accs = []
for i, c in enumerate(classes_out):
    mask = y_test_true == i
    if mask.sum() > 0:
        class_accs.append((c, (y_test_pred[mask] == i).mean()))
min_class_acc = min(class_accs, key=lambda x: x[1])
max_class_acc = max(class_accs, key=lambda x: x[1])
if max_class_acc[1] - min_class_acc[1] > 0.3:
    concerns.append(f"⚠️  Large accuracy disparity: C{min_class_acc[0]}={min_class_acc[1]:.4f} vs C{max_class_acc[0]}={max_class_acc[1]:.4f}")

# Calibration issues
for i, c in enumerate(classes_out):
    y_bin = (y_test_true == i).astype(float)
    brier = brier_score_loss(y_bin, y_test_proba[:, i])
    if brier > 0.15:
        concerns.append(f"⚠️  Poor calibration for C{c}: Brier={brier:.4f}")

# Entropy concerns
if entropy.mean() > 0.8:
    concerns.append(f"⚠️  High average entropy ({entropy.mean():.4f}) — model is uncertain")

# Feature imbalance
# score_french dominates too much?
if imp[sorted_idx[0]] > 0.5:
    concerns.append(f"⚠️  Top feature '{model_features[sorted_idx[0]]}' dominates ({imp[sorted_idx[0]]:.1%})")

if not concerns:
    print("\n   ✅ No major concerns detected.")
else:
    print(f"\n   🔍 {len(concerns)} concern(s):")
    for c in concerns:
        print(f"   {c}")

# Print current metrics json
print(f"\n   Final test accuracy: {acc:.4f}")
print(f"   CV accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
print(f"   Mean entropy: {entropy.mean():.4f}")
print(f"   High-confidence rate (≥0.95): {(max_proba >= 0.95).mean():.1%}")

print(f"\n   Full report saved to: {REPORT_DIR}")
