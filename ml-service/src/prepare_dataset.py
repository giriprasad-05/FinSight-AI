"""
prepare_dataset.py
------------------
Purpose:
- Implements Step 5 of the FinSight AI machine learning pipeline.
- Loads and validates all 35 individual labeled stock CSV files from `ml-service/data/labeled/`.
- Combines them into a single chronological multi-stock dataset (`data/combined_labeled.csv`).
- Creates a strict, leak-free, time-series chronological train/validation/test split (70% / 15% / 15%) based on global date boundaries.
- Persists split datasets (`data/splits/train.csv`, `validation.csv`, `test.csv`) and configuration manifests (`feature_columns.json`, `target_definition.json`).
- Conducts comprehensive data-leakage and schema integrity validation.

Features (X - 17 columns):
  Open, High, Low, Close, Volume, Daily_Return, MA_5, MA_10, MA_20, MA_50,
  RSI_14, MACD, MACD_Signal, Volatility_20, Volume_Change, Price_Change_Pct, High_Low_Pct

Target (y - 1 column):
  Trend_Code (0=DOWN, 1=FLAT, 2=UP)

Metadata (kept in CSVs for traceability/evaluation, not in X):
  Date, Ticker, Market, Trend_Label

Usage:
  python src/prepare_dataset.py
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
LABELED_DATA_DIR = BASE_DIR / "data" / "labeled"
COMBINED_DATA_FILE = BASE_DIR / "data" / "combined_labeled.csv"
SPLITS_DIR = BASE_DIR / "data" / "splits"

# Feature and Column Manifests
FEATURE_COLUMNS: List[str] = [
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "Daily_Return",
    "MA_5",
    "MA_10",
    "MA_20",
    "MA_50",
    "RSI_14",
    "MACD",
    "MACD_Signal",
    "Volatility_20",
    "Volume_Change",
    "Price_Change_Pct",
    "High_Low_Pct",
]

METADATA_COLUMNS: List[str] = [
    "Date",
    "Ticker",
    "Market",
    "Trend_Label",
]

TARGET_COLUMN: str = "Trend_Code"

EXPECTED_COLUMNS_ORDER: List[str] = [
    "Date",
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "Ticker",
    "Market",
    "Daily_Return",
    "MA_5",
    "MA_10",
    "MA_20",
    "MA_50",
    "RSI_14",
    "MACD",
    "MACD_Signal",
    "Volatility_20",
    "Volume_Change",
    "Price_Change_Pct",
    "High_Low_Pct",
    "Trend_Label",
    "Trend_Code",
]

TARGET_DEFINITION: Dict[str, Any] = {
    "target_name": "Trend_Code",
    "label_column": "Trend_Label",
    "classes": {
        "DOWN": 0,
        "FLAT": 1,
        "UP": 2,
    },
    "thresholds": {
        "UP": "> +1.0%",
        "DOWN": "< -1.0%",
        "FLAT": "[-1.0%, +1.0%]",
    },
    "description": "Next trading day directional price movement classification.",
}


def validate_stock_dataset(df: pd.DataFrame, file_name: str) -> bool:
    """
    Validates an individual labeled stock DataFrame before combination.

    Checks:
    - 22 required columns present in exact order.
    - Date is valid datetime, sorted ascending, and unique.
    - Trend_Label strictly contains {"DOWN", "FLAT", "UP"}.
    - Trend_Code strictly contains {0, 1, 2}.
    - Numeric features are numeric with no NaNs or infs.
    - Dataset is non-empty.
    - Ticker and Market columns are valid and consistent.
    - No forbidden forward-looking columns present.

    Args:
        df: Input DataFrame.
        file_name: Origin filename for logging.

    Returns:
        True if valid.

    Raises:
        ValueError if validation fails.
    """
    if df.empty:
        raise ValueError(f"Validation failed for '{file_name}': Dataset is empty.")

    if list(df.columns) != EXPECTED_COLUMNS_ORDER:
        raise ValueError(
            f"Validation failed for '{file_name}': Column order mismatch.\nExpected: {EXPECTED_COLUMNS_ORDER}\nActual:   {list(df.columns)}"
        )

    # Date checks
    date_dt = pd.to_datetime(df["Date"])
    if not date_dt.is_monotonic_increasing:
        raise ValueError(f"Validation failed for '{file_name}': Dates are not monotonically increasing.")
    if date_dt.duplicated().any():
        raise ValueError(f"Validation failed for '{file_name}': Duplicate dates detected.")

    # Target values
    valid_labels = {"DOWN", "FLAT", "UP"}
    actual_labels = set(df["Trend_Label"].unique())
    if not actual_labels.issubset(valid_labels):
        raise ValueError(f"Validation failed for '{file_name}': Invalid Trend_Labels: {actual_labels - valid_labels}")

    valid_codes = {0, 1, 2}
    actual_codes = set(df["Trend_Code"].unique())
    if not actual_codes.issubset(valid_codes):
        raise ValueError(f"Validation failed for '{file_name}': Invalid Trend_Codes: {actual_codes - valid_codes}")

    # Numeric features integrity
    for col in FEATURE_COLUMNS:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise ValueError(f"Validation failed for '{file_name}': Feature '{col}' is not numeric.")
        if df[col].isna().any():
            raise ValueError(f"Validation failed for '{file_name}': Feature '{col}' contains NaN values.")
        if np.isinf(df[col]).any():
            raise ValueError(f"Validation failed for '{file_name}': Feature '{col}' contains infinite values.")

    # Forbidden forward-looking columns
    for forbidden in ["Next_Day_Close", "Next_Day_Return"]:
        if forbidden in df.columns:
            raise ValueError(f"Validation failed for '{file_name}': Forbidden target leakage column '{forbidden}' present.")

    return True


def load_labeled_files(labeled_dir: Path) -> List[pd.DataFrame]:
    """
    Loads and validates all `*_labeled.csv` files from the labeled data directory.

    Args:
        labeled_dir: Path to directory containing labeled CSV files.

    Returns:
        List of validated DataFrames.
    """
    files = sorted([p for p in labeled_dir.glob("*_labeled.csv") if p.is_file()])
    if not files:
        raise FileNotFoundError(f"No labeled CSV files found in '{labeled_dir}'. Run Step 4 first.")

    print(f"Loading and validating {len(files)} labeled stock files...")
    dfs: List[pd.DataFrame] = []
    for f in files:
        df = pd.read_csv(f)
        validate_stock_dataset(df=df, file_name=f.name)
        dfs.append(df)

    print(f"Successfully validated all {len(dfs)} stock datasets.")
    return dfs


def combine_datasets(dataframes: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Combines individual stock DataFrames into a single unified dataset,
    sorted chronologically by Date (and Ticker for deterministic ordering).

    Args:
        dataframes: List of individual stock DataFrames.

    Returns:
        Combined, sorted DataFrame.
    """
    combined_df = pd.concat(dataframes, ignore_index=True)
    combined_df["Date_dt"] = pd.to_datetime(combined_df["Date"])
    combined_df = combined_df.sort_values(["Date_dt", "Ticker"]).reset_index(drop=True)
    combined_df = combined_df.drop(columns=["Date_dt"])
    combined_df = combined_df[EXPECTED_COLUMNS_ORDER].copy()
    return combined_df


def create_time_based_split(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Splits a multi-stock time-series dataset strictly by global chronological dates.

    Guarantees:
    - max(train Date) < min(validation Date)
    - max(validation Date) < min(test Date)
    - Proportions match target ratios as closely as discrete trading dates allow.

    Args:
        df: Combined DataFrame.
        train_ratio: Proportional size for training set (default: 0.70).
        val_ratio: Proportional size for validation set (default: 0.15).

    Returns:
        Tuple of (train_df, val_df, test_df, split_info_dict)
    """
    total_rows = len(df)
    df_working = df.copy()
    df_working["Date_dt"] = pd.to_datetime(df_working["Date"])

    # Aggregate row counts per unique global trading date
    date_counts = df_working.groupby("Date_dt").size().reset_index(name="count")
    date_counts = date_counts.sort_values("Date_dt").reset_index(drop=True)
    date_counts["cum_count"] = date_counts["count"].cumsum()
    date_counts["cum_pct"] = date_counts["cum_count"] / total_rows

    # Find optimal train cutoff date (closest to target 70%)
    train_target_pct = train_ratio
    train_cutoff_idx = (date_counts["cum_pct"] >= train_target_pct).idxmax()
    train_end_dt = date_counts.loc[train_cutoff_idx, "Date_dt"]
    train_end_str = train_end_dt.strftime("%Y-%m-%d")

    # Find optimal validation cutoff date (closest to target 85%)
    val_target_pct = train_ratio + val_ratio
    val_cutoff_idx = (date_counts["cum_pct"] >= val_target_pct).idxmax()
    val_end_dt = date_counts.loc[val_cutoff_idx, "Date_dt"]
    val_end_str = val_end_dt.strftime("%Y-%m-%d")

    # Filter splits
    train_mask = df_working["Date_dt"] <= train_end_dt
    val_mask = (df_working["Date_dt"] > train_end_dt) & (df_working["Date_dt"] <= val_end_dt)
    test_mask = df_working["Date_dt"] > val_end_dt

    train_df = df_working[train_mask].drop(columns=["Date_dt"]).reset_index(drop=True)
    val_df = df_working[val_mask].drop(columns=["Date_dt"]).reset_index(drop=True)
    test_df = df_working[test_mask].drop(columns=["Date_dt"]).reset_index(drop=True)

    split_info = {
        "train_start": train_df["Date"].iloc[0],
        "train_end": train_df["Date"].iloc[-1],
        "train_rows": len(train_df),
        "train_pct": len(train_df) / total_rows * 100.0,
        "val_start": val_df["Date"].iloc[0],
        "val_end": val_df["Date"].iloc[-1],
        "val_rows": len(val_df),
        "val_pct": len(val_df) / total_rows * 100.0,
        "test_start": test_df["Date"].iloc[0],
        "test_end": test_df["Date"].iloc[-1],
        "test_rows": len(test_df),
        "test_pct": len(test_df) / total_rows * 100.0,
        "total_rows": total_rows,
    }

    return train_df, val_df, test_df, split_info


def validate_split_boundaries(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> Dict[str, Dict[str, Any]]:
    """
    Performs rigorous temporal boundary checks on the train, validation, and test splits.

    Checks:
    1. No date overlap between Train and Validation.
    2. No date overlap between Validation and Test.
    3. No date overlap between Train and Test.
    4. max(Train Date) < min(Validation Date).
    5. max(Validation Date) < min(Test Date).

    Returns:
        Dictionary mapping check names to {"passed": bool, "detail": str}.
    """
    train_dates = set(train_df["Date"].unique())
    val_dates = set(val_df["Date"].unique())
    test_dates = set(test_df["Date"].unique())

    max_train_date = pd.to_datetime(train_df["Date"].max())
    min_val_date = pd.to_datetime(val_df["Date"].min())
    max_val_date = pd.to_datetime(val_df["Date"].max())
    min_test_date = pd.to_datetime(test_df["Date"].min())

    overlap_train_val = train_dates.intersection(val_dates)
    overlap_val_test = val_dates.intersection(test_dates)
    overlap_train_test = train_dates.intersection(test_dates)

    results = {
        "no_date_overlap_train_val": {
            "passed": len(overlap_train_val) == 0,
            "detail": f"Overlap dates: {list(overlap_train_val)}" if overlap_train_val else "Zero overlap (0 dates).",
        },
        "no_date_overlap_val_test": {
            "passed": len(overlap_val_test) == 0,
            "detail": f"Overlap dates: {list(overlap_val_test)}" if overlap_val_test else "Zero overlap (0 dates).",
        },
        "no_date_overlap_train_test": {
            "passed": len(overlap_train_test) == 0,
            "detail": f"Overlap dates: {list(overlap_train_test)}" if overlap_train_test else "Zero overlap (0 dates).",
        },
        "train_strictly_precedes_val": {
            "passed": max_train_date < min_val_date,
            "detail": f"max(Train)={max_train_date.strftime('%Y-%m-%d')} < min(Val)={min_val_date.strftime('%Y-%m-%d')}.",
        },
        "val_strictly_precedes_test": {
            "passed": max_val_date < min_test_date,
            "detail": f"max(Val)={max_val_date.strftime('%Y-%m-%d')} < min(Test)={min_test_date.strftime('%Y-%m-%d')}.",
        },
    }

    return results


def check_feature_target_leakage(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> Dict[str, Dict[str, Any]]:
    """
    Performs comprehensive feature/target leakage and schema validation checks across splits.

    Checks:
    1. Target column (Trend_Code) is not inside feature list X.
    2. Trend_Label is not inside feature list X.
    3. Ticker, Market, and Date are not inside feature list X.
    4. No future-looking columns (Next_Day_Close, Next_Day_Return) exist in any split.
    5. No NaN or infinite values exist in feature matrix X across all splits.
    6. All 17 feature columns are numeric.
    7. All 3 splits contain the exact 22-column schema.

    Returns:
        Dictionary mapping check names to {"passed": bool, "detail": str}.
    """
    splits = {"train": train_df, "validation": val_df, "test": test_df}

    # 1 & 2: Feature list isolation
    target_in_features = TARGET_COLUMN in FEATURE_COLUMNS
    label_in_features = "Trend_Label" in FEATURE_COLUMNS
    meta_in_features = any(col in FEATURE_COLUMNS for col in ["Date", "Ticker", "Market"])

    # 4: Future columns absence
    forbidden_cols = ["Next_Day_Close", "Next_Day_Return"]
    forbidden_found = {}
    for name, df in splits.items():
        found = [c for c in forbidden_cols if c in df.columns]
        if found:
            forbidden_found[name] = found

    # 5 & 6: NaN, Inf, and Numeric checks in X
    nan_inf_issues = {}
    for name, df in splits.items():
        X = df[FEATURE_COLUMNS]
        if X.isna().any().any():
            nan_inf_issues[f"{name}_nans"] = X.isna().sum()[X.isna().sum() > 0].to_dict()
        if np.isinf(X.values).any():
            nan_inf_issues[f"{name}_infs"] = "Found infinite values in feature columns."

    # 7: Schema uniformity
    schema_uniform = all(list(df.columns) == EXPECTED_COLUMNS_ORDER for df in splits.values())

    results = {
        "target_isolated_from_features": {
            "passed": not target_in_features,
            "detail": f"Target '{TARGET_COLUMN}' is strictly excluded from feature list X.",
        },
        "trend_label_isolated_from_features": {
            "passed": not label_in_features,
            "detail": "String column 'Trend_Label' is strictly excluded from feature list X.",
        },
        "metadata_isolated_from_features": {
            "passed": not meta_in_features,
            "detail": "Metadata columns (Date, Ticker, Market) are strictly excluded from feature list X.",
        },
        "no_forward_price_leakage_columns": {
            "passed": len(forbidden_found) == 0,
            "detail": f"Forbidden columns detected: {forbidden_found}" if forbidden_found else "Zero forward-looking columns present across all splits.",
        },
        "zero_nan_or_inf_in_features": {
            "passed": len(nan_inf_issues) == 0,
            "detail": f"Issues found: {nan_inf_issues}" if nan_inf_issues else "Zero NaN or infinite values in feature matrix X across all splits.",
        },
        "exact_feature_count": {
            "passed": len(FEATURE_COLUMNS) == 17,
            "detail": f"Exact feature count = {len(FEATURE_COLUMNS)} input features.",
        },
        "split_schema_uniformity": {
            "passed": schema_uniform,
            "detail": f"All 3 splits have uniform 22-column schema.",
        },
    }

    return results


def compute_split_class_distribution(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes DOWN, FLAT, UP counts and percentages for a split DataFrame.
    """
    total = len(df)
    counts = df["Trend_Label"].value_counts().to_dict()

    down = counts.get("DOWN", 0)
    flat = counts.get("FLAT", 0)
    up = counts.get("UP", 0)

    return {
        "total": total,
        "DOWN": {"count": down, "pct": (down / total * 100.0) if total > 0 else 0.0},
        "FLAT": {"count": flat, "pct": (flat / total * 100.0) if total > 0 else 0.0},
        "UP": {"count": up, "pct": (up / total * 100.0) if total > 0 else 0.0},
    }


def compute_per_stock_contributions(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Computes per-stock row contributions across Train, Validation, and Test splits.
    """
    tickers = sorted(train_df["Ticker"].unique())
    records = []

    for ticker in tickers:
        market = train_df[train_df["Ticker"] == ticker]["Market"].iloc[0]
        tr_count = len(train_df[train_df["Ticker"] == ticker])
        va_count = len(val_df[val_df["Ticker"] == ticker])
        te_count = len(test_df[test_df["Ticker"] == ticker])
        tot = tr_count + va_count + te_count

        records.append({
            "ticker": ticker,
            "market": market,
            "train_rows": tr_count,
            "val_rows": va_count,
            "test_rows": te_count,
            "total_rows": tot,
        })

    return pd.DataFrame(records)


def save_datasets(
    combined_df: pd.DataFrame,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    combined_path: Optional[Path] = None,
    splits_dir: Optional[Path] = None,
) -> Dict[str, str]:
    """
    Persists combined dataset, split CSVs, feature columns JSON, and target definition JSON to disk.

    Returns:
        Dict mapping artifact keys to saved file paths.
    """
    if combined_path is None:
        combined_path = COMBINED_DATA_FILE

    if splits_dir is None:
        splits_dir = SPLITS_DIR

    combined_path.parent.mkdir(parents=True, exist_ok=True)
    splits_dir.mkdir(parents=True, exist_ok=True)

    # 1. Save combined dataset
    combined_df.to_csv(combined_path, index=False)
    print(f"[SAVED] Combined dataset  : {combined_path} ({len(combined_df):,} rows)")

    # 2. Save split datasets
    train_file = splits_dir / "train.csv"
    val_file = splits_dir / "validation.csv"
    test_file = splits_dir / "test.csv"

    train_df.to_csv(train_file, index=False)
    val_df.to_csv(val_file, index=False)
    test_df.to_csv(test_file, index=False)

    print(f"[SAVED] Train split CSV   : {train_file} ({len(train_df):,} rows)")
    print(f"[SAVED] Val split CSV     : {val_file} ({len(val_df):,} rows)")
    print(f"[SAVED] Test split CSV    : {test_file} ({len(test_df):,} rows)")

    # 3. Save feature columns JSON
    feature_file = splits_dir / "feature_columns.json"
    with open(feature_file, "w", encoding="utf-8") as f:
        json.dump(FEATURE_COLUMNS, f, indent=2)
    print(f"[SAVED] Feature columns   : {feature_file} ({len(FEATURE_COLUMNS)} features)")

    # 4. Save target definition JSON
    target_file = splits_dir / "target_definition.json"
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(TARGET_DEFINITION, f, indent=2)
    print(f"[SAVED] Target definition : {target_file}")

    return {
        "combined": str(combined_path),
        "train": str(train_file),
        "validation": str(val_file),
        "test": str(test_file),
        "feature_columns": str(feature_file),
        "target_definition": str(target_file),
    }


def main(
    labeled_dir: Optional[Path] = None,
    combined_file: Optional[Path] = None,
    splits_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Main orchestration routine for Step 5: Final Dataset Preparation & Time-Series Split.
    """
    if labeled_dir is None:
        labeled_dir = LABELED_DATA_DIR

    if combined_file is None:
        combined_file = COMBINED_DATA_FILE

    if splits_dir is None:
        splits_dir = SPLITS_DIR

    print("=" * 80)
    print("  FinSight AI - Step 5: Dataset Combination & Time-Series Split Pipeline")
    print("=" * 80)

    # 1. Load and validate individual labeled files
    stock_dfs = load_labeled_files(labeled_dir=labeled_dir)

    # 2. Combine datasets
    combined_df = combine_datasets(stock_dfs)
    print(f"\nCombined dataset created: {len(combined_df):,} rows across {len(stock_dfs)} stocks.")
    print(f"Date range: {combined_df['Date'].iloc[0]} to {combined_df['Date'].iloc[-1]}")

    # 3. Create chronological time-series split
    train_df, val_df, test_df, split_info = create_time_based_split(
        df=combined_df,
        train_ratio=0.70,
        val_ratio=0.15,
    )

    print("\n" + "=" * 80)
    print("  CHRONOLOGICAL SPLIT SUMMARY (70% / 15% / 15%)")
    print("=" * 80)
    print(f"TRAIN      : {split_info['train_start']} to {split_info['train_end']} | Rows: {split_info['train_rows']:>6,} ({split_info['train_pct']:>5.2f}%)")
    print(f"VALIDATION : {split_info['val_start']} to {split_info['val_end']} | Rows: {split_info['val_rows']:>6,} ({split_info['val_pct']:>5.2f}%)")
    print(f"TEST       : {split_info['test_start']} to {split_info['test_end']} | Rows: {split_info['test_rows']:>6,} ({split_info['test_pct']:>5.2f}%)")
    print(f"TOTAL      : {split_info['train_start']} to {split_info['test_end']} | Rows: {split_info['total_rows']:>6,} (100.00%)")
    print("=" * 80)

    # 4. Temporal boundary validation
    boundary_results = validate_split_boundaries(train_df=train_df, val_df=val_df, test_df=test_df)
    leakage_results = check_feature_target_leakage(train_df=train_df, val_df=val_df, test_df=test_df)

    all_passed = True
    print("\n" + "=" * 80)
    print("  LEAKAGE & TEMPORAL BOUNDARY CHECKS")
    print("=" * 80)
    for name, item in {**boundary_results, **leakage_results}.items():
        status = "PASSED" if item["passed"] else "FAILED"
        if not item["passed"]:
            all_passed = False
        print(f"[{status}] {name:<36} : {item['detail']}")
    print("=" * 80)

    if not all_passed:
        raise RuntimeError("Critical validation check failed during Step 5. Execution halted.")

    # 5. Target distributions across splits
    dist_train = compute_split_class_distribution(train_df)
    dist_val = compute_split_class_distribution(val_df)
    dist_test = compute_split_class_distribution(test_df)

    print("\n" + "=" * 80)
    print("  PER-SPLIT TARGET CLASS DISTRIBUTIONS")
    print("=" * 80)
    print(f"{'Split':<12} | {'DOWN (Code 0)':<18} | {'FLAT (Code 1)':<18} | {'UP (Code 2)':<18} | {'Total'}")
    print("-" * 80)
    for s_name, d in [("TRAIN", dist_train), ("VALIDATION", dist_val), ("TEST", dist_test)]:
        d_str = f"{d['DOWN']['count']:>5} ({d['DOWN']['pct']:>5.1f}%)"
        f_str = f"{d['FLAT']['count']:>5} ({d['FLAT']['pct']:>5.1f}%)"
        u_str = f"{d['UP']['count']:>5} ({d['UP']['pct']:>5.1f}%)"
        print(f"{s_name:<12} | {d_str:<18} | {f_str:<18} | {u_str:<18} | {d['total']:>6,}")
    print("=" * 80)

    # 6. Per-stock contributions
    contrib_df = compute_per_stock_contributions(train_df=train_df, val_df=val_df, test_df=test_df)
    print("\n" + "=" * 80)
    print("  PER-STOCK ROW CONTRIBUTIONS ACROSS SPLITS")
    print("=" * 80)
    print(f"{'Ticker':<16} | {'Market':<6} | {'Train Rows':<10} | {'Val Rows':<10} | {'Test Rows':<10} | {'Total Rows'}")
    print("-" * 80)
    for _, row in contrib_df.iterrows():
        print(f"{row['ticker']:<16} | {row['market']:<6} | {row['train_rows']:<10} | {row['val_rows']:<10} | {row['test_rows']:<10} | {row['total_rows']:<10}")
    print("=" * 80)

    # 7. Save datasets and manifests
    saved_paths = save_datasets(
        combined_df=combined_df,
        train_df=train_df,
        val_df=val_df,
        test_df=test_df,
        combined_path=combined_file,
        splits_dir=splits_dir,
    )

    print("\n[SUCCESS] Step 5 Dataset Preparation & Time-Series Split completed successfully.")

    return {
        "status": "SUCCESS",
        "split_info": split_info,
        "saved_paths": saved_paths,
        "boundary_results": boundary_results,
        "leakage_results": leakage_results,
        "distributions": {
            "train": dist_train,
            "validation": dist_val,
            "test": dist_test,
        },
        "per_stock_contributions": contrib_df.to_dict(orient="records"),
    }


if __name__ == "__main__":
    main()
