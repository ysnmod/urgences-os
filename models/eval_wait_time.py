#!/usr/bin/env python3
"""
Comprehensive evaluation of the ER Wait Time regression model (Cas5).

Checks:
1. Base regression metrics: MAE, RMSE, R², MAPE, MedAE
2. Residuals analysis: scatter predicted vs actual, histogram, distribution stats
3. Error by wait-time range (short vs long waits)
4. Bias audit by categorical features: region, urgency, time_of_day, day_of_week
5. Cross-validation (5-fold KFold)
6. Feature importance (built-in + permutation)
7. Hyperparameter sweep (light)
8. Learning curve
9. Prediction intervals (std across RandomForest trees)
10. Top/bottom predictions (best & worst errors)
11. Summary with auto-flagged concerns
"""

import json
import sys
import joblib
import numpy as np
import pandas as pd
from pathlib import Path

from sklearn.model_selection import (
    train_test_split,
    KFold,
    cross_val_score,
    learning_curve,
    cross_validate,
)
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    mean_absolute_percentage_error,
    median_absolute_error,
)
from sklearn.inspection import permutation_importance
from sklearn.ensemble import RandomForestRegressor

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
REPORT_DIR = Path(__file__).resolve().parent / "eval_reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Import project feature engineering
sys.path.insert(0, str(Path(__file__).resolve().parent))
from features import load_raw, engineer_features, get_feature_names, CAT_COLS, NUM_COLS, TARGET_COL

np.random.seed(42)

ALL_FEATURES = get_feature_names()


def round4(x):
    return round(float(x), 4)


# ──────────────────────── 1. LOAD MODEL + DATA ────────────────────────

print("=" * 72)
print("  ER WAIT TIME MODEL — COMPREHENSIVE EVALUATION")
print("=" * 72)

artifact = joblib.load(ARTIFACTS_DIR / "wait_time_model.joblib")
model: RandomForestRegressor = artifact["model"]
stored_metrics = artifact.get("metrics", {})

print(f"\n  Stored metrics: MAE={stored_metrics.get('mae', '?'):.1f} min, "
      f"RMSE={stored_metrics.get('rmse', '?'):.1f} min, "
      f"R²={stored_metrics.get('r2', '?'):.3f}")
print(f"  Feature names ({len(ALL_FEATURES)}): {ALL_FEATURES}")
print(f"  Model: RandomForestRegressor, {model.n_estimators} trees, max_depth={model.max_depth}")

raw = load_raw()
feats, target = engineer_features(raw)
X = feats.values
y = target

print(f"\n📊 Dataset: {len(X)} rows, {len(ALL_FEATURES)} features")
print(f"   Target range: {y.min():.0f} – {y.max():.0f} min  (mean={y.mean():.1f}, std={y.std():.1f})")

# Random split — valid here (independent visits, no time-series)
X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
    X, y, np.arange(len(X)), test_size=0.2, random_state=42
)
df_test_raw = raw.iloc[idx_test].copy()
feats_test = feats.iloc[idx_test].copy()

print(f"   Train: {len(X_train)} rows, Test: {len(X_test)} rows")

# ──────────────────────── 2. BASE REGRESSION METRICS ────────────────────────

print("\n" + "─" * 72)
print("📈 1. BASE REGRESSION METRICS")
print("─" * 72)

y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)
mape = mean_absolute_percentage_error(y_test, y_pred)
medae = median_absolute_error(y_test, y_pred)

print(f"\n   MAE:  {mae:.1f} min  (avg error)")
print(f"   RMSE: {rmse:.1f} min  (penalises large errors)")
print(f"   R²:   {r2:.4f}       (1.0=perfect)")
print(f"   MAPE: {mape:.1%}     (relative error)")
print(f"   MedAE:{medae:.1f} min  (median error)")

# Compare with stored
delta_mae = mae - stored_metrics.get("mae", mae)
delta_rmse = rmse - stored_metrics.get("rmse", rmse)
print(f"\n   Δ vs stored:  MAE={delta_mae:+.1f}  RMSE={delta_rmse:+.1f}  R²={r2-stored_metrics.get('r2',r2):+.4f}")

# ──────────────────────── 3. RESIDUALS ANALYSIS ────────────────────────

print("\n" + "─" * 72)
print("📊 2. RESIDUALS ANALYSIS")
print("─" * 72)

residuals = y_test - y_pred
abs_errors = np.abs(residuals)

print(f"\n   Residuals (actual - predicted):")
print(f"   Mean: {residuals.mean():.1f} min  (bias; 0 = unbiased)")
print(f"   Std:  {residuals.std():.1f} min")
print(f"   Min:  {residuals.min():.1f} min")
print(f"   Max:  {residuals.max():.1f} min")
print(f"   Skew: {pd.Series(residuals).skew():.2f}  (0=symmetric)")
print(f"   Kurt: {pd.Series(residuals).kurtosis():.2f}  (0=normal tails)")

# Residuals percentiles
for pct in [10, 25, 50, 75, 90, 95, 99]:
    val = np.percentile(abs_errors, pct)
    print(f"   P{pct} abs error: {val:.1f} min")

# Over/under estimation breakdown
over = (residuals > 0).sum()
under = (residuals < 0).sum()
exact = (residuals == 0).sum()
print(f"\n   Over-estimated (actual > predicted): {over} ({100*over/len(residuals):.1f}%)")
print(f"   Under-estimated (predicted > actual): {under} ({100*under/len(residuals):.1f}%)")
print(f"   Exact: {exact}")

# ──────────────────────── 4. ERROR BY WAIT-TIME RANGE ────────────────────────

print("\n" + "─" * 72)
print("📊 3. ERROR BY WAIT-TIME RANGE")
print("─" * 72)

ranges = [
    ("< 30 min", lambda t: t < 30),
    ("30-60 min", lambda t: (t >= 30) & (t < 60)),
    ("60-120 min", lambda t: (t >= 60) & (t < 120)),
    ("120+ min", lambda t: t >= 120),
]

for label, cond in ranges:
    mask = cond(y_test)
    if mask.sum() > 0:
        mae_r = mean_absolute_error(y_test[mask], y_pred[mask])
        rmse_r = np.sqrt(mean_squared_error(y_test[mask], y_pred[mask]))
        r2_r = r2_score(y_test[mask], y_pred[mask])
        mape_r = mean_absolute_percentage_error(
            np.maximum(y_test[mask], 1), np.maximum(y_pred[mask], 1)
        )
        mean_actual = y_test[mask].mean()
        mean_pred = y_pred[mask].mean()
        print(f"   [{label:>12}] n={mask.sum():>4}  MAE={mae_r:.1f}  RMSE={rmse_r:.1f}  "
              f"MAPE={mape_r:.1%}  R²={r2_r:.3f}  actual_mean={mean_actual:.0f}  pred_mean={mean_pred:.0f}")

# ──────────────────────── 5. BIAS AUDIT ────────────────────────

print("\n" + "─" * 72)
print("⚖️  4. BIAS AUDIT BY CATEGORICAL FEATURES")
print("─" * 72)


def evaluate_subgroup(mask, label):
    if mask.sum() < 10:
        return
    y_t = y_test[mask]
    y_p = y_pred[mask]
    mae_s = mean_absolute_error(y_t, y_p)
    rmse_s = np.sqrt(mean_squared_error(y_t, y_p))
    mape_s = mean_absolute_percentage_error(np.maximum(y_t, 1), np.maximum(y_p, 1))
    bias_s = (y_t - y_p).mean()
    print(f"   [{label:>35}] n={mask.sum():>4}  MAE={mae_s:.1f}  "
          f"MAPE={mape_s:.1%}  bias={bias_s:+.1f}")


# 5a. By region
print("\n   --- By Region ---")
for region_val in sorted(df_test_raw["region"].dropna().unique()):
    mask = (df_test_raw["region"].values == region_val)
    evaluate_subgroup(mask, f"Region={region_val}")

# 5b. By urgency level
print("\n   --- By Urgency Level ---")
for urg in sorted(df_test_raw["urgency_level"].dropna().unique()):
    mask = (df_test_raw["urgency_level"].values == urg)
    evaluate_subgroup(mask, f"Urgency={urg}")

# 5c. By time of day
print("\n   --- By Time of Day ---")
for tod in sorted(df_test_raw["time_of_day"].dropna().unique()):
    mask = (df_test_raw["time_of_day"].values == tod)
    evaluate_subgroup(mask, f"Time={tod}")

# 5d. By day of week
print("\n   --- By Day of Week ---")
for dow in sorted(df_test_raw["day_of_week"].dropna().unique()):
    mask = (df_test_raw["day_of_week"].values == dow)
    evaluate_subgroup(mask, f"Day={dow}")

# ──────────────────────── 6. CROSS-VALIDATION ────────────────────────

print("\n" + "─" * 72)
print("🔁 5. 5-FOLD CROSS-VALIDATION")
print("─" * 72)

cv_params = {
    "n_estimators": 100,        # lighter for CV speed
    "max_depth": model.max_depth,
    "min_samples_leaf": model.min_samples_leaf,
    "random_state": 42,
    "n_jobs": 1,
}
cv_rf = RandomForestRegressor(**cv_params)
cv = KFold(n_splits=5, shuffle=True, random_state=42)

scoring = {"mae": "neg_mean_absolute_error", "rmse": "neg_root_mean_squared_error", "r2": "r2"}
cv_results = cross_validate(cv_rf, X_train, y_train, cv=cv, scoring=scoring, n_jobs=1)

cv_mae = -cv_results["test_mae"]
cv_rmse = -cv_results["test_rmse"]
cv_r2 = cv_results["test_r2"]

print(f"   Fold MAE:  {[round(v, 1) for v in cv_mae]}")
print(f"   Fold RMSE: {[round(v, 1) for v in cv_rmse]}")
print(f"   Fold R²:   {[round(v, 3) for v in cv_r2]}")
print(f"   Mean CV MAE:  {cv_mae.mean():.1f} ± {cv_mae.std():.1f} min")
print(f"   Mean CV RMSE: {cv_rmse.mean():.1f} ± {cv_rmse.std():.1f} min")
print(f"   Mean CV R²:   {cv_r2.mean():.4f} ± {cv_r2.std():.4f}")

# ──────────────────────── 7. FEATURE IMPORTANCE ────────────────────────

print("\n" + "─" * 72)
print("🔬 6. FEATURE IMPORTANCE")
print("─" * 72)

imp = model.feature_importances_
sorted_idx = np.argsort(imp)[::-1]

print(f"\n   --- Model built-in importance ---")
for idx in sorted_idx:
    print(f"   {ALL_FEATURES[idx]:25s}  {imp[idx]:.4f}")

print(f"\n   --- Permutation importance (on test set, neg MAE) ---")
perm_result = permutation_importance(
    model, X_test, y_test, n_repeats=10, random_state=42, n_jobs=1,
    scoring="neg_mean_absolute_error",
)
perm_imp = -perm_result.importances_mean   # flip sign: higher = more important
perm_std = perm_result.importances_std
sorted_perm = np.argsort(perm_imp)[::-1]
for idx in sorted_perm:
    print(f"   {ALL_FEATURES[idx]:25s}  {perm_imp[idx]:.2f} ± {perm_std[idx]:.2f}")

# ──────────────────────── 8. HYPERPARAMETER SWEEP ────────────────────────

print("\n" + "─" * 72)
print("⚙️  7. HYPERPARAMETER SWEEP (light)")
print("─" * 72)

param_grid = {
    "n_estimators": [100, 300, 500],
    "max_depth": [8, 15, 25, 40],
    "min_samples_leaf": [1, 5, 10, 20],
}

results = []
for param_name, values in param_grid.items():
    for val in values:
        params = dict(cv_params)
        params[param_name] = val
        m = RandomForestRegressor(**params)
        cv_mae_val = -cross_val_score(m, X_train, y_train, cv=3, scoring="neg_mean_absolute_error", n_jobs=1)
        mean_cv = cv_mae_val.mean()
        results.append((param_name, val, mean_cv))
        delta = mean_cv - cv_mae.mean()
        marker = " ◀ CURRENT" if (
            (param_name == "n_estimators" and val == 300) or
            (param_name == "max_depth" and val == 15) or
            (param_name == "min_samples_leaf" and val == 5)
        ) else ""
        if abs(delta) > 0.1 or marker:
            print(f"   {param_name}={val:>3}  cv_mae={mean_cv:.1f}  (Δ={delta:+.1f}){marker}")

best_overall = min(results, key=lambda x: x[2])
print(f"\n   Best single-param improvement: {best_overall[0]}={best_overall[1]}  cv_mae={best_overall[2]:.1f}")

# ──────────────────────── 9. LEARNING CURVE ────────────────────────

print("\n" + "─" * 72)
print("📊 8. LEARNING CURVE (MAE vs training size)")
print("─" * 72)

try:
    train_sizes = np.linspace(0.1, 1.0, 6)
    train_sizes_abs, train_scores, val_scores = learning_curve(
        RandomForestRegressor(**cv_params),
        X_train, y_train,
        train_sizes=train_sizes,
        cv=3,
        scoring="neg_mean_absolute_error",
        n_jobs=1,
        random_state=42,
    )
    for i, sz in enumerate(train_sizes_abs):
        train_mean = -train_scores[i].mean()
        val_mean = -val_scores[i].mean()
        print(f"   n_train={int(sz):>5}  train_mae={train_mean:.1f} min  val_mae={val_mean:.1f} min  gap={train_mean - val_mean:+.1f}")
except Exception as e:
    print(f"   Learning curve skipped ({e})")

# ──────────────────────── 10. PREDICTION INTERVALS ────────────────────────

print("\n" + "─" * 72)
print("🎯 9. PREDICTION INTERVALS (std across trees)")
print("─" * 72)

# Get individual tree predictions for uncertainty estimation
tree_preds = np.array([tree.predict(X_test) for tree in model.estimators_])  # (n_trees, n_samples)
pred_std = tree_preds.std(axis=0)
mean_pred = tree_preds.mean(axis=0)  # should equal y_pred

print(f"\n   Mean prediction std: {pred_std.mean():.1f} min")
print(f"   Median prediction std: {np.median(pred_std):.1f} min")
print(f"   Q1-Q3: [{np.percentile(pred_std, 25):.1f}, {np.percentile(pred_std, 75):.1f}]")

# Calibration: does higher std correlate with higher error?
corr_std_error = np.corrcoef(pred_std, abs_errors)[0, 1]
print(f"   Correlation (std vs |error|): {corr_std_error:.3f}  (>0 means std reflects uncertainty)")

# Std by wait-time range
print(f"\n   Prediction std by wait-time range:")
for label, cond in ranges:
    mask = cond(y_test)
    if mask.sum() > 0:
        std_r = pred_std[mask].mean()
        err_r = abs_errors[mask].mean()
        print(f"   [{label:>12}] n={mask.sum():>4}  mean_std={std_r:.1f} min  mean_|error|={err_r:.1f} min")

# ──────────────────────── 11. TOP / BOTTOM PREDICTIONS ────────────────────────

print("\n" + "─" * 72)
print("🔍 10. BEST & WORST PREDICTIONS")
print("─" * 72)

# Top 5 best predictions
best_idx = np.argsort(abs_errors)[:5]
print(f"\n   --- Best 5 predictions (lowest absolute error) ---")
for i, bi in enumerate(best_idx):
    print(f"   #{i+1}: actual={y_test[bi]:.0f} min  predicted={y_pred[bi]:.0f} min  "
          f"error={abs_errors[bi]:.0f} min  std={pred_std[bi]:.1f}")

# Top 5 worst predictions
worst_idx = np.argsort(abs_errors)[-5:][::-1]
print(f"\n   --- Worst 5 predictions (highest absolute error) ---")
for i, wi in enumerate(worst_idx):
    print(f"   #{i+1}: actual={y_test[wi]:.0f} min  predicted={y_pred[wi]:.0f} min  "
          f"error={abs_errors[wi]:.0f} min  std={pred_std[wi]:.1f}")

# ──────────────────────── 12. SUMMARY ────────────────────────

print("\n" + "=" * 72)
print("  EVALUATION SUMMARY")
print("=" * 72)

concerns = []

# R² check
if r2 < 0.5:
    concerns.append(f"⚠️  R² ({r2:.4f}) < 0.5 — model explains <50% of variance")

# MAE check
if mae > 20:
    concerns.append(f"⚠️  MAE ({mae:.1f} min) > 20 min — error may be clinically significant")

# Train/val gap
if 'train_scores' in dir():
    gap_mae = -train_scores[-1].mean() - (-val_scores[-1].mean())
    if gap_mae < -5:
        concerns.append(f"⚠️  Train/val MAE gap ({gap_mae:.1f} min) — possible overfit")

# Feature dominance
if imp[sorted_idx[0]] > 0.4:
    concerns.append(f"⚠️  Top feature '{ALL_FEATURES[sorted_idx[0]]}' dominates ({imp[sorted_idx[0]]:.1%})")

# Bias check — large bias for some subgroups
for label, cond in ranges:
    mask = cond(y_test)
    if mask.sum() > 0:
        bias_r = (y_test[mask] - y_pred[mask]).mean()
        mae_r = mean_absolute_error(y_test[mask], y_pred[mask])
        if abs(bias_r) > mae_r * 0.5 and mask.sum() > 20:
            concerns.append(f"⚠️  Large bias for '{label}': {bias_r:+.1f} min (MAE={mae_r:.1f})")

# CV vs test gap
if abs(cv_mae.mean() - mae) > 5:
    concerns.append(f"⚠️  CV MAE ({cv_mae.mean():.1f}) differs from test MAE ({mae:.1f}) by >5 min")

# Prediction uncertainty calibration
if corr_std_error < 0.3:
    concerns.append(f"⚠️  Prediction std poorly correlated with error (r={corr_std_error:.3f}) — intervals not well calibrated")

if not concerns:
    print("\n   ✅ No major concerns detected.")
else:
    print(f"\n   🔍 {len(concerns)} concern(s):")
    for c in concerns:
        print(f"   {c}")

print(f"\n   Final test MAE:  {mae:.1f} min")
print(f"   Final test RMSE: {rmse:.1f} min")
print(f"   Final test R²:   {r2:.4f}")
print(f"   CV MAE:  {cv_mae.mean():.1f} ± {cv_mae.std():.1f} min")
print(f"   CV R²:   {cv_r2.mean():.4f} ± {cv_r2.std():.4f}")
print(f"   Prediction std: {pred_std.mean():.1f} min (avg)")
print(f"   Over/under: {over}/{under}")

print(f"\n   Full report saved to: {REPORT_DIR}")
