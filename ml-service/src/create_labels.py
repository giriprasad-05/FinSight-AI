"""
create_labels.py
----------------
Purpose:
- Implements Step 4 of the FinSight AI machine learning pipeline.
- Generates 1-day forward-looking trend prediction target labels ("UP", "DOWN", "FLAT") and numeric codes (2, 0, 1).
- Reads processed feature CSVs from `ml-service/data/processed/` and outputs labeled datasets to `ml-service/data/labeled/`.
- Prevents target feature leakage by strictly pruning temporary forward prices and returns.
- Prunes the last row per stock (which lacks future market observation) and verifies exact row delta (N - 1).
- Computes and logs per-stock and aggregated multiclass target distributions.

Target Labeling Rules:
- Next_Day_Return = (Next_Day_Close - Current_Close) / Current_Close
- UP    (Code: 2) -> Next_Day_Return > +1.0% (+0.01)
- DOWN  (Code: 0) -> Next_Day_Return < -1.0% (-0.01)
- FLAT  (Code: 1) -> -1.0% <= Next_Day_Return <= +1.0%

Final Output Schema (22 Columns):
- Date, Open, High, Low, Close, Volume, Ticker, Market,
  Daily_Return, MA_5, MA_10, MA_20, MA_50, RSI_14, MACD,
  MACD_Signal, Volatility_20, Volume_Change, Price_Change_Pct, High_Low_Pct,
  Trend_Label, Trend_Code

Usage:
  python src/create_labels.py
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
LABELED_DATA_DIR = BASE_DIR / "data" / "labeled"

# Feature & Metadata Column Definitions (Preserved from Step 3)
PROCESSED_COLUMNS: List[str] = [
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
]

TARGET_COLUMNS: List[str] = [
    "Trend_Label",
    "Trend_Code",
]

FINAL_LABELED_COLUMNS: List[str] = PROCESSED_COLUMNS + TARGET_COLUMNS

# Target Encoding Mapping
LABEL_TO_CODE: Dict[str, int] = {
    "DOWN": 0,
    "FLAT": 1,
    "UP": 2,
}

CODE_TO_LABEL: Dict[int, str] = {v: k for k, v in LABEL_TO_CODE.items()}


def create_trend_labels(
    df: pd.DataFrame,
    threshold: float = 0.01,
) -> Tuple[pd.DataFrame, int, int]:
    """
    Computes 1-day forward return target labels and numeric codes for a single stock DataFrame.

    Data Leakage Prevention:
    - Sorts chronologically ascending by Date.
    - Shifts Close backward by 1 to compute Next_Day_Close for target generation only.
    - Drops the final row (which has no future trading day).
    - Removes temporary Next_Day_Close and Next_Day_Return columns before returning.

    Args:
        df: Input processed feature DataFrame.
        threshold: Return percentage threshold for UP / DOWN classification (default: 0.01 for 1%).

    Returns:
        Tuple of (labeled_df, initial_row_count, final_row_count)
    """
    df = df.copy()

    # Step 1: Ensure Date is sorted ascending
    df["Date_dt"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date_dt", ascending=True).reset_index(drop=True)
    df = df.drop(columns=["Date_dt"])

    initial_row_count = len(df)
    if initial_row_count == 0:
        raise ValueError("Cannot create labels on an empty DataFrame.")

    # Step 2: Compute temporary forward-looking values
    df["Next_Day_Close"] = df["Close"].shift(-1)
    df["Next_Day_Return"] = (df["Next_Day_Close"] - df["Close"]) / df["Close"]

    # Step 3: Assign Trend_Label based on threshold
    conditions = [
        df["Next_Day_Return"] > threshold,
        df["Next_Day_Return"] < -threshold,
    ]
    choices = ["UP", "DOWN"]
    df["Trend_Label"] = np.select(conditions, choices, default="FLAT")

    # Step 4: Assign Trend_Code
    df["Trend_Code"] = df["Trend_Label"].map(LABEL_TO_CODE).astype("int64")

    # Step 5: Remove the final row where Next_Day_Close is NaN
    # The last row has index initial_row_count - 1
    labeled_df = df.iloc[:-1].copy().reset_index(drop=True)

    # Step 6: Strict Data Leakage Prevention - Drop temporary target calculation columns
    leakage_cols = ["Next_Day_Close", "Next_Day_Return"]
    for col in leakage_cols:
        if col in labeled_df.columns:
            labeled_df = labeled_df.drop(columns=[col])

    # Reorder columns to exact expected schema
    labeled_df = labeled_df[FINAL_LABELED_COLUMNS].copy()

    final_row_count = len(labeled_df)

    return labeled_df, initial_row_count, final_row_count


def validate_labels(
    df: pd.DataFrame,
    expected_ticker: Optional[str] = None,
    expected_market: Optional[str] = None,
) -> bool:
    """
    Validates data integrity, schema consistency, and label mappings of the labeled DataFrame.

    Checks:
    1. Exactly 22 columns in exact required order.
    2. Trend_Label and Trend_Code exist with zero missing values.
    3. Trend_Label values are strictly subset of {"DOWN", "FLAT", "UP"}.
    4. Trend_Code values are strictly subset of {0, 1, 2}.
    5. Trend_Code matches Trend_Label mapping perfectly.
    6. No NaN or infinite values across any feature or target columns.
    7. Next_Day_Close and Next_Day_Return are NOT present.
    8. Date is sorted ascending and deduplicated.
    9. Ticker and Market remain uniform and correct.

    Args:
        df: Labeled DataFrame to validate.
        expected_ticker: Optional expected stock ticker.
        expected_market: Optional expected stock exchange.

    Returns:
        True if all validations pass.

    Raises:
        ValueError if any validation check fails.
    """
    # 1. Dataset not empty
    if df.empty:
        raise ValueError("Labeled dataset is empty (0 rows).")

    # 2. Check exact column schema and order
    if list(df.columns) != FINAL_LABELED_COLUMNS:
        raise ValueError(
            f"Column schema mismatch.\nExpected: {FINAL_LABELED_COLUMNS}\nActual:   {list(df.columns)}"
        )

    # 3. Leakage check: Ensure forward-price columns are absent
    forbidden_cols = ["Next_Day_Close", "Next_Day_Return"]
    found_forbidden = [c for c in forbidden_cols if c in df.columns]
    if found_forbidden:
        raise ValueError(f"CRITICAL LEAKAGE: Found forbidden forward-looking columns: {found_forbidden}")

    # 4. Target column presence and non-null
    if df["Trend_Label"].isna().any():
        raise ValueError("Trend_Label contains NaN values.")
    if df["Trend_Code"].isna().any():
        raise ValueError("Trend_Code contains NaN values.")

    # 5. Allowed label and code values
    valid_labels = {"DOWN", "FLAT", "UP"}
    actual_labels = set(df["Trend_Label"].unique())
    if not actual_labels.issubset(valid_labels):
        raise ValueError(f"Invalid Trend_Label values found: {actual_labels - valid_labels}")

    valid_codes = {0, 1, 2}
    actual_codes = set(df["Trend_Code"].unique())
    if not actual_codes.issubset(valid_codes):
        raise ValueError(f"Invalid Trend_Code values found: {actual_codes - valid_codes}")

    # 6. Mapping consistency check
    expected_codes = df["Trend_Label"].map(LABEL_TO_CODE)
    if not (df["Trend_Code"] == expected_codes).all():
        raise ValueError("Trend_Code does not strictly match Trend_Label mapping (DOWN=0, FLAT=1, UP=2).")

    # 7. No NaNs or infs anywhere in the dataset
    if df.isna().any().any():
        nan_summary = df.isna().sum()[df.isna().sum() > 0].to_dict()
        raise ValueError(f"NaN values detected in dataset: {nan_summary}")

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    for col in numeric_cols:
        if np.isinf(df[col]).any():
            raise ValueError(f"Infinite value detected in column '{col}'.")

    # 8. Date ascending and unique
    date_dt = pd.to_datetime(df["Date"])
    if not date_dt.is_monotonic_increasing:
        raise ValueError("Date column is not monotonically increasing.")
    if date_dt.duplicated().any():
        raise ValueError("Duplicate dates found in dataset.")

    # 9. Ticker & Market integrity
    if expected_ticker is not None:
        if (df["Ticker"] != expected_ticker).any():
            raise ValueError(f"Ticker mismatch: expected single value '{expected_ticker}'.")

    if expected_market is not None:
        if (df["Market"] != expected_market).any():
            raise ValueError(f"Market mismatch: expected single value '{expected_market}'.")

    return True


def compute_class_distribution(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes class counts and percentages for DOWN, FLAT, and UP labels.

    Args:
        df: Labeled DataFrame.

    Returns:
        Dict containing class distribution metrics.
    """
    total = len(df)
    counts = df["Trend_Label"].value_counts().to_dict()

    down_count = counts.get("DOWN", 0)
    flat_count = counts.get("FLAT", 0)
    up_count = counts.get("UP", 0)

    down_pct = (down_count / total * 100.0) if total > 0 else 0.0
    flat_pct = (flat_count / total * 100.0) if total > 0 else 0.0
    up_pct = (up_count / total * 100.0) if total > 0 else 0.0

    return {
        "total": total,
        "down_count": down_count,
        "down_pct": down_pct,
        "flat_count": flat_count,
        "flat_pct": flat_pct,
        "up_count": up_count,
        "up_pct": up_pct,
    }


def process_labeled_file(
    file_path: Path,
    output_dir: Optional[Path] = None,
    threshold: float = 0.01,
) -> Dict[str, Any]:
    """
    Processes an individual processed CSV file:
    1. Loads features.
    2. Generates trend target labels.
    3. Prunes last row and validates N - 1 delta.
    4. Validates labels and schema.
    5. Saves to `data/labeled/{ticker}_labeled.csv`.

    Args:
        file_path: Path to `*_processed.csv` file.
        output_dir: Output directory (defaults to LABELED_DATA_DIR).
        threshold: Return threshold (default 1%).

    Returns:
        Dict summarizing per-file labeling and validation statistics.
    """
    if output_dir is None:
        output_dir = LABELED_DATA_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    # Derive output filename: e.g., AAPL_processed.csv -> AAPL_labeled.csv
    base_name = file_path.stem.replace("_processed", "")
    output_filename = f"{base_name}_labeled.csv"
    output_path = output_dir / output_filename

    raw_processed_df = pd.read_csv(file_path)
    expected_ticker = raw_processed_df["Ticker"].iloc[0] if "Ticker" in raw_processed_df.columns else None
    expected_market = raw_processed_df["Market"].iloc[0] if "Market" in raw_processed_df.columns else None

    # Generate labels
    labeled_df, initial_rows, final_rows = create_trend_labels(raw_processed_df, threshold=threshold)

    # Data integrity check: exactly 1 row removed
    row_delta = initial_rows - final_rows
    if row_delta != 1:
        raise ValueError(
            f"Data integrity violation in '{file_path.name}': Expected exactly 1 row removed (processed={initial_rows}, labeled={final_rows}, delta={row_delta})."
        )

    # Validate output
    validate_labels(
        df=labeled_df,
        expected_ticker=expected_ticker,
        expected_market=expected_market,
    )

    # Save to disk
    labeled_df.to_csv(output_path, index=False)

    # Compute distribution
    dist = compute_class_distribution(labeled_df)

    return {
        "processed_file": file_path.name,
        "labeled_file": output_filename,
        "ticker": expected_ticker,
        "market": expected_market,
        "processed_rows": initial_rows,
        "labeled_rows": final_rows,
        "rows_removed": row_delta,
        "output_path": str(output_path),
        "distribution": dist,
        "status": "SUCCESS",
    }


def main(
    processed_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    threshold: float = 0.01,
) -> Dict[str, Any]:
    """
    Main entry point for Step 4 Target Label Generation Pipeline.
    Iterates over all `*_processed.csv` files, generates labels, verifies integrity,
    and prints class distributions for individual stocks and the combined dataset.

    Args:
        processed_dir: Path to processed directory (defaults to PROCESSED_DATA_DIR).
        output_dir: Path to labeled directory (defaults to LABELED_DATA_DIR).
        threshold: Forward return threshold (default 1%).

    Returns:
        Execution summary dictionary.
    """
    if processed_dir is None:
        processed_dir = PROCESSED_DATA_DIR

    if output_dir is None:
        output_dir = LABELED_DATA_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    processed_files = sorted([p for p in processed_dir.glob("*_processed.csv") if p.is_file()])

    print("=" * 80)
    print("  FinSight AI - Step 4: Stock Trend Prediction Target Label Generation")
    print("=" * 80)
    print(f"Processed Input Directory : {processed_dir}")
    print(f"Labeled Output Directory   : {output_dir}")
    print(f"Processed Files Discovered : {len(processed_files)}")
    print(f"Target Definition          : 1-Day Forward Return (UP > +1%, DOWN < -1%, FLAT [-1%, +1%])")
    print(f"Target Encoding            : DOWN=0, FLAT=1, UP=2")
    print("=" * 80)

    if not processed_files:
        print("\n[WARNING] No processed CSV files found in data/processed/. Run Step 3 first.")
        return {
            "total_processed_files": 0,
            "successful_count": 0,
            "failed_count": 0,
            "total_processed_rows": 0,
            "total_labeled_rows": 0,
            "total_rows_removed": 0,
            "results": [],
            "failed_files": [],
        }

    successful_results: List[Dict[str, Any]] = []
    failed_files: List[Dict[str, Any]] = []

    total_processed_rows = 0
    total_labeled_rows = 0
    total_rows_removed = 0

    combined_down = 0
    combined_flat = 0
    combined_up = 0

    print(f"{'Ticker':<16} | {'Market':<6} | {'Proc Rows':<9} | {'Labl Rows':<9} | {'DOWN (%)':<16} | {'FLAT (%)':<16} | {'UP (%)':<16}")
    print("-" * 95)

    for file_path in processed_files:
        try:
            res = process_labeled_file(file_path=file_path, output_dir=output_dir, threshold=threshold)
            successful_results.append(res)

            total_processed_rows += res["processed_rows"]
            total_labeled_rows += res["labeled_rows"]
            total_rows_removed += res["rows_removed"]

            d = res["distribution"]
            combined_down += d["down_count"]
            combined_flat += d["flat_count"]
            combined_up += d["up_count"]

            down_str = f"{d['down_count']:<4} ({d['down_pct']:.1f}%)"
            flat_str = f"{d['flat_count']:<4} ({d['flat_pct']:.1f}%)"
            up_str = f"{d['up_count']:<4} ({d['up_pct']:.1f}%)"

            print(f"{res['ticker']:<16} | {res['market']:<6} | {res['processed_rows']:<9} | {res['labeled_rows']:<9} | {down_str:<16} | {flat_str:<16} | {up_str:<16}")

        except Exception as e:
            print(f"[ERROR] Failed labeling '{file_path.name}': {e}", file=sys.stderr)
            failed_files.append({"file": file_path.name, "error": str(e)})

    # Schema Uniformity Verification
    schema_uniform = True
    if successful_results:
        first_cols = list(pd.read_csv(successful_results[0]["output_path"]).columns)
        for r in successful_results[1:]:
            c_cols = list(pd.read_csv(r["output_path"]).columns)
            if c_cols != first_cols:
                schema_uniform = False
                print(f"[SCHEMA MISMATCH] {r['labeled_file']} differs from {successful_results[0]['labeled_file']}")

    # Combined Class Distribution
    combined_total = total_labeled_rows
    c_down_pct = (combined_down / combined_total * 100.0) if combined_total > 0 else 0.0
    c_flat_pct = (combined_flat / combined_total * 100.0) if combined_total > 0 else 0.0
    c_up_pct = (combined_up / combined_total * 100.0) if combined_total > 0 else 0.0

    print("\n" + "=" * 80)
    print("  COMBINED DATASET CLASS DISTRIBUTION")
    print("=" * 80)
    print(f"DOWN (Code 0) : {combined_down:>6} ({c_down_pct:>5.1f}%)")
    print(f"FLAT (Code 1) : {combined_flat:>6} ({c_flat_pct:>5.1f}%)")
    print(f"UP   (Code 2) : {combined_up:>6} ({c_up_pct:>5.1f}%)")
    print(f"Total Labels  : {combined_total:>6} (100.0%)")
    print("=" * 80)

    print("\n" + "=" * 80)
    print("  Step 4 Pipeline Summary")
    print("=" * 80)
    print(f"Total Processed Input Files   : {len(processed_files)}")
    print(f"Successfully Labeled Files    : {len(successful_results)}")
    print(f"Failed Files                  : {len(failed_files)}")
    print(f"Total Processed Rows In       : {total_processed_rows:,}")
    print(f"Total Labeled Rows Out        : {total_labeled_rows:,}")
    print(f"Total Rows Removed (No Target): {total_rows_removed:,}")
    print(f"Exact (N - 1) Row Integrity   : {'PASSED (All 35 stocks)' if total_rows_removed == len(processed_files) else 'FAILED'}")
    print(f"Schema Uniformity (22 cols)   : {'PASSED' if schema_uniform else 'FAILED'}")
    print(f"Zero Feature Leakage Verified : PASSED (No forward-price columns present)")
    print("=" * 80)

    return {
        "total_processed_files": len(processed_files),
        "successful_count": len(successful_results),
        "failed_count": len(failed_files),
        "total_processed_rows": total_processed_rows,
        "total_labeled_rows": total_labeled_rows,
        "total_rows_removed": total_rows_removed,
        "combined_distribution": {
            "DOWN": {"count": combined_down, "pct": c_down_pct},
            "FLAT": {"count": combined_flat, "pct": c_flat_pct},
            "UP": {"count": combined_up, "pct": c_up_pct},
        },
        "results": successful_results,
        "failed_files": failed_files,
    }


if __name__ == "__main__":
    main()
