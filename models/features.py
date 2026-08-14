"""Feature engineering for ER wait time prediction (Kaggle dataset)."""

import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

CAT_COLS = [
    "region",
    "urgency_level",
    "time_of_day",
    "day_of_week",
    "season",
]

NUM_COLS = [
    "nurse_patient_ratio",
    "specialist_availability",
    "facility_beds",
]

TARGET_COL = "total_wait_time"


def load_raw(filename: str = "er_wait_time.csv") -> pd.DataFrame:
    """Load the raw Kaggle ER wait time CSV."""
    path = DATA_DIR / "raw" / filename
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    df = pd.read_csv(path)
    df = df.rename(columns={
        "Region": "region",
        "Urgency Level": "urgency_level",
        "Time of Day": "time_of_day",
        "Day of Week": "day_of_week",
        "Season": "season",
        "Nurse-to-Patient Ratio": "nurse_patient_ratio",
        "Specialist Availability": "specialist_availability",
        "Facility Size (Beds)": "facility_beds",
        "Total Wait Time (min)": "total_wait_time",
        "Visit Date": "visit_date",
    })
    return df


def encode_categories(df: pd.DataFrame) -> pd.DataFrame:
    """Map categorical strings to integers deterministically."""
    mapping = {}
    for col in CAT_COLS:
        if col in df.columns:
            unique = sorted(df[col].dropna().unique())
            mapping[col] = {v: i for i, v in enumerate(unique)}
            df[col] = df[col].map(mapping[col])
    df["_category_mapping"] = [mapping] * len(df)
    return df


def engineer_features(df: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray | None]:
    """Prepare feature matrix and target vector."""
    df = df.copy()

    rename_map = {
        "Region": "region",
        "Urgency Level": "urgency_level",
        "Time of Day": "time_of_day",
        "Day of Week": "day_of_week",
        "Season": "season",
        "Nurse-to-Patient Ratio": "nurse_patient_ratio",
        "Specialist Availability": "specialist_availability",
        "Facility Size (Beds)": "facility_beds",
        "Total Wait Time (min)": "total_wait_time",
        "Visit Date": "visit_date",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    if "visit_date" in df.columns:
        dt = pd.to_datetime(df["visit_date"])
        if "time_of_day" not in df.columns:
            df["time_of_day"] = pd.cut(
                dt.dt.hour,
                bins=[-1, 6, 10, 12, 16, 20, 24],
                labels=["Night", "Early Morning", "Late Morning", "Afternoon", "Evening", "Night"],
            )
        if "day_of_week" not in df.columns:
            df["day_of_week"] = dt.dt.day_name()
        if "season" not in df.columns:
            df["season"] = dt.dt.month.map({
                12: "Winter", 1: "Winter", 2: "Winter",
                3: "Spring", 4: "Spring", 5: "Spring",
                6: "Summer", 7: "Summer", 8: "Summer",
                9: "Fall", 10: "Fall", 11: "Fall",
            })
        df["hour"] = dt.dt.hour
        df["weekday"] = dt.dt.weekday
        df["month"] = dt.dt.month
        df["weekend"] = df["weekday"].isin([5, 6]).astype(int)

    target = df[TARGET_COL].values if TARGET_COL in df.columns else None

    drop_cols = [
        "Visit ID", "Patient ID", "Hospital ID", "Hospital Name",
        "visit_date",
        "Day of Week", "Season", "Time of Day",
        "Time to Registration (min)", "Time to Triage (min)",
        "Time to Medical Professional (min)", "Patient Outcome",
        "Patient Satisfaction", "_category_mapping",
    ]
    if TARGET_COL in df.columns:
        drop_cols.append(TARGET_COL)

    for col in CAT_COLS:
        if col in df.columns:
            df[col] = df[col].astype("category").cat.codes

    feature_df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")
    # Ensure column order matches get_feature_names() for deterministic inference
    ordered = get_feature_names()
    feature_df = feature_df[[c for c in ordered if c in feature_df.columns]]
    return feature_df, target


def get_feature_names() -> list[str]:
    """Return ordered list of feature names the model expects."""
    return CAT_COLS + NUM_COLS + ["hour", "weekday", "month", "weekend"]


if __name__ == "__main__":
    df = load_raw()
    print(f"Loaded {len(df)} rows, columns: {list(df.columns)}")
    feats, target = engineer_features(df)
    print(f"Features ({feats.shape[1]}): {list(feats.columns)}")
    print(f"Features shape: {feats.shape}")
    if target is not None:
        print(f"Target range: {target.min():.0f} – {target.max():.0f} min (mean={target.mean():.0f})")
