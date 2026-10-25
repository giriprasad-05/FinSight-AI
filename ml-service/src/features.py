"""
features.py
------------
Purpose:
- Implements Step 3 of the FinSight AI machine learning pipeline.
- Converts raw OHLCV stock CSV files from `ml-service/data/raw/` into processed feature datasets inside `ml-service/data/processed/`.
- Computes 12 technical indicators and price metrics chronologically without data leakage.
- Cleans missing/infinite values, strictly validates data integrity, and saves per-stock datasets.

Features Calculated:
1. Daily_Return       - Daily percentage return (Close_t - Close_{t-1}) / Close_{t-1}
2. MA_5               - 5-day moving average of Close
3. MA_10              - 10-day moving average of Close
4. MA_20              - 20-day moving average of Close
5. MA_50              - 50-day moving average of Close
6. RSI_14             - Standard 14-period Relative Strength Index (Wilder's smoothing)
7. MACD               - 12-period EMA minus 26-period EMA of Close
8. MACD_Signal        - 9-period EMA of MACD
9. Volatility_20      - 20-day rolling standard deviation of Daily_Return
10. Volume_Change     - Percentage change in Volume from previous trading day
11. Price_Change_Pct  - (Close - Open) / Open
12. High_Low_Pct      - (High - Low) / Close

Usage:
  python src/features.py
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"

# Column Definitions
RAW_COLUMNS: List[str] = [
    "Date",
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "Ticker",
    "Market",
]

FEATURE_COLUMNS: List[str] = [
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

FINAL_COLUMN_ORDER: List[str] = RAW_COLUMNS + FEATURE_COLUMNS


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculates standard 14-period Relative Strength Index (RSI) using Wilder's smoothing.
    
    Robustness guarantees:
    - Avoids division-by-zero when average loss is 0.
    - Accurately computes RSI in [0, 100].
    - Returns NaN for initial warmup periods (< period).

    Args:
        series: Price series (Close prices).
        period: RSI lookback period (default: 14).

    Returns:
        pd.Series containing computed RSI values.
    """
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    # Wilder's smoothed moving averages (alpha = 1 / period)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    # Relative Strength (RS)
    rs = np.where(avg_loss == 0.0, np.nan, avg_gain / avg_loss)

    # RSI calculation with safe zero-loss edge case handling
    rsi = np.where(
        avg_loss == 0.0,
        np.where(avg_gain == 0.0, 50.0, 100.0),
        100.0 - (100.0 / (1.0 + rs)),
    )

    rsi_series = pd.Series(rsi, index=series.index, name=f"RSI_{period}")

    # Ensure NaN values are preserved during the initial warmup window
    rsi_series = rsi_series.where(avg_gain.notna() & avg_loss.notna(), np.nan)
    return rsi_series


def calculate_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes all 12 required technical indicators and market features for a single stock DataFrame.

    Data Leakage Prevention:
    - Converts Date to datetime and sorts ascending chronologically.
    - Removes duplicate dates.
    - Computes all rolling/EMA features strictly using current and historical rows (center=False).
    - Never shifts backwards or utilizes future data.

    Args:
        df: Input DataFrame containing raw OHLCV and metadata columns.

    Returns:
        Cleaned DataFrame with all features computed and formatted in FINAL_COLUMN_ORDER.
    """
    # Create working copy
    df = df.copy()

    # Validate raw column existence
    for col in RAW_COLUMNS:
        if col not in df.columns:
            raise KeyError(f"Input DataFrame is missing required raw column: '{col}'")

    # Step 1: Normalize Date, sort ascending chronologically, and drop duplicate dates
    df["Date_dt"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date_dt", ascending=True).drop_duplicates(subset=["Date_dt"]).reset_index(drop=True)
    df["Date"] = df["Date_dt"].dt.strftime("%Y-%m-%d")
    df = df.drop(columns=["Date_dt"])

    # Ensure OHLCV are float/numeric types
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 1. Daily_Return = (Close_t - Close_{t-1}) / Close_{t-1}
    df["Daily_Return"] = df["Close"].pct_change()

    # 2. MA_5 = 5-day moving average of Close
    df["MA_5"] = df["Close"].rolling(window=5, min_periods=5).mean()

    # 3. MA_10 = 10-day moving average of Close
    df["MA_10"] = df["Close"].rolling(window=10, min_periods=10).mean()

    # 4. MA_20 = 20-day moving average of Close
    df["MA_20"] = df["Close"].rolling(window=20, min_periods=20).mean()

    # 5. MA_50 = 50-day moving average of Close
    df["MA_50"] = df["Close"].rolling(window=50, min_periods=50).mean()

    # 6. RSI_14 = Standard 14-period RSI
    df["RSI_14"] = calculate_rsi(df["Close"], period=14)

    # 7. MACD = 12-period EMA minus 26-period EMA
    ema_12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema_26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema_12 - ema_26

    # 8. MACD_Signal = 9-period EMA of MACD
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    # 9. Volatility_20 = 20-day rolling standard deviation of Daily_Return
    df["Volatility_20"] = df["Daily_Return"].rolling(window=20, min_periods=20).std()

    # 10. Volume_Change = Percentage change in Volume from previous trading day
    vol_prev = df["Volume"].shift(1)
    df["Volume_Change"] = np.where(
        vol_prev > 0,
        (df["Volume"] - vol_prev) / vol_prev,
        np.nan,
    )

    # 11. Price_Change_Pct = (Close - Open) / Open
    df["Price_Change_Pct"] = np.where(
        df["Open"] != 0,
        (df["Close"] - df["Open"]) / df["Open"],
        np.nan,
    )

    # 12. High_Low_Pct = (High - Low) / Close
    df["High_Low_Pct"] = np.where(
        df["Close"] != 0,
        (df["High"] - df["Low"]) / df["Close"],
        np.nan,
    )

    # Reorder columns to exact final order
    df = df[FINAL_COLUMN_ORDER].copy()

    return df


def clean_missing_values(df: pd.DataFrame) -> (pd.DataFrame, int, int, int):
    """
    Cleans missing and infinite values from the calculated feature DataFrame.

    - Replaces infinite values with NaN.
    - Drops rows with NaN in any feature column without forward/backward filling.

    Args:
        df: DataFrame with computed features.

    Returns:
        Tuple of (cleaned_df, rows_before, rows_after, rows_removed)
    """
    rows_before = len(df)

    # Replace +/- infinity with NaN
    df = df.replace([np.inf, -np.inf], np.nan)

    # Remove rows with NaN in feature columns
    cleaned_df = df.dropna(subset=FEATURE_COLUMNS).reset_index(drop=True)

    rows_after = len(cleaned_df)
    rows_removed = rows_before - rows_after

    return cleaned_df, rows_before, rows_after, rows_removed


def validate_processed_data(
    df: pd.DataFrame,
    expected_ticker: Optional[str] = None,
    expected_market: Optional[str] = None,
) -> bool:
    """
    Performs comprehensive validation checks on a processed stock DataFrame.

    Checks:
    - Dataset is not empty.
    - Required columns exist in exact order.
    - Date is sorted ascending chronologically.
    - No duplicate dates exist.
    - All feature columns are numeric.
    - No NaN values remain in feature columns.
    - No infinite values remain.
    - Ticker and Market match expected values.

    Args:
        df: Processed DataFrame to validate.
        expected_ticker: Optional expected ticker symbol.
        expected_market: Optional expected market exchange.

    Returns:
        True if all validations pass.

    Raises:
        ValueError if any validation check fails.
    """
    # 1. Dataset not empty
    if df.empty:
        raise ValueError("Processed dataset is empty (0 rows).")

    # 2. Required columns exist and order is correct
    if list(df.columns) != FINAL_COLUMN_ORDER:
        raise ValueError(
            f"Column order/presence mismatch.\nExpected: {FINAL_COLUMN_ORDER}\nActual:   {list(df.columns)}"
        )

    # 3. Date is sorted ascending
    date_dt = pd.to_datetime(df["Date"])
    if not date_dt.is_monotonic_increasing:
        raise ValueError("Date column is not monotonically increasing (sorted ascending).")

    # 4. No duplicate dates
    if date_dt.duplicated().any():
        duplicate_dates = df.loc[date_dt.duplicated(), "Date"].tolist()
        raise ValueError(f"Duplicate dates found in dataset: {duplicate_dates}")

    # 5. All feature columns are numeric
    for col in FEATURE_COLUMNS:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise ValueError(f"Feature column '{col}' is not a numeric data type.")

    # 6. No NaN values in feature columns
    nan_counts = df[FEATURE_COLUMNS].isna().sum()
    if nan_counts.any():
        cols_with_nan = nan_counts[nan_counts > 0].to_dict()
        raise ValueError(f"Unresolved NaN values found in feature columns: {cols_with_nan}")

    # 7. No infinite values in feature columns
    for col in FEATURE_COLUMNS:
        if np.isinf(df[col]).any():
            raise ValueError(f"Infinite values found in feature column '{col}'.")

    # 8. Ticker remains correct
    if expected_ticker is not None:
        unique_tickers = df["Ticker"].unique()
        if len(unique_tickers) != 1 or unique_tickers[0] != expected_ticker:
            raise ValueError(
                f"Ticker mismatch: expected single value '{expected_ticker}', found {unique_tickers.tolist()}."
            )

    # 9. Market remains correct
    if expected_market is not None:
        unique_markets = df["Market"].unique()
        if len(unique_markets) != 1 or unique_markets[0] != expected_market:
            raise ValueError(
                f"Market mismatch: expected single value '{expected_market}', found {unique_markets.tolist()}."
            )

    return True


def process_stock_file(
    file_path: Path,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Processes an individual raw stock CSV file:
    1. Reads raw OHLCV data.
    2. Computes technical indicators.
    3. Cleans warmup NaNs and inf values.
    4. Validates output dataset.
    5. Saves to `data/processed/{ticker}_processed.csv`.

    Args:
        file_path: Path to the raw CSV file.
        output_dir: Destination directory for processed CSVs (defaults to PROCESSED_DATA_DIR).

    Returns:
        Dict summarizing processing statistics.
    """
    if output_dir is None:
        output_dir = PROCESSED_DATA_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n--- Processing: {file_path.name} ---")
    raw_df = pd.read_csv(file_path)

    if raw_df.empty:
        raise ValueError(f"Raw CSV file '{file_path.name}' is empty.")

    # Determine expected ticker and market if available in raw data
    expected_ticker = raw_df["Ticker"].iloc[0] if "Ticker" in raw_df.columns and not raw_df["Ticker"].empty else None
    expected_market = raw_df["Market"].iloc[0] if "Market" in raw_df.columns and not raw_df["Market"].empty else None

    # Calculate all technical features
    feature_df = calculate_features(raw_df)

    # Clean missing values
    cleaned_df, rows_before, rows_after, rows_removed = clean_missing_values(feature_df)
    print(f"  Rows before cleaning : {rows_before}")
    print(f"  Rows after cleaning  : {rows_after}")
    print(f"  Rows removed         : {rows_removed}")

    # Validate processed data
    validate_processed_data(
        df=cleaned_df,
        expected_ticker=expected_ticker,
        expected_market=expected_market,
    )
    print("  Validation status    : PASSED (Schema, Non-null, Monotonic Dates, Types)")

    # Save to processed directory with naming convention: {stem}_processed.csv
    output_filename = f"{file_path.stem}_processed.csv"
    output_path = output_dir / output_filename
    cleaned_df.to_csv(output_path, index=False)
    print(f"  Saved processed file : {output_path}")

    return {
        "raw_file": file_path.name,
        "processed_file": output_filename,
        "ticker": expected_ticker,
        "market": expected_market,
        "rows_before": rows_before,
        "rows_after": rows_after,
        "rows_removed": rows_removed,
        "output_path": str(output_path),
        "status": "SUCCESS",
    }


def main(
    raw_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Main entry point for Step 3 Feature Engineering Pipeline.
    Iterates over all CSV files in `raw_dir`, processes each stock independently,
    validates every dataset, and generates a pipeline summary report.

    Args:
        raw_dir: Path to raw data directory.
        output_dir: Path to processed data directory.

    Returns:
        Comprehensive execution summary dict.
    """
    if raw_dir is None:
        raw_dir = RAW_DATA_DIR

    if output_dir is None:
        output_dir = PROCESSED_DATA_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all CSV files in raw directory (excluding hidden/gitkeep)
    raw_csv_files = sorted([p for p in raw_dir.glob("*.csv") if p.is_file()])

    print("=" * 60)
    print("  FinSight AI - Step 3: Feature Engineering Pipeline")
    print("=" * 60)
    print(f"Raw Data Directory      : {raw_dir}")
    print(f"Processed Directory     : {output_dir}")
    print(f"Raw CSV Files Found     : {len(raw_csv_files)}")

    if not raw_csv_files:
        print("\n[WARNING] No raw CSV files found in data/raw/. Run data_fetcher.py first.")
        return {
            "total_raw_files": 0,
            "successful_count": 0,
            "failed_count": 0,
            "total_rows_before": 0,
            "total_rows_after": 0,
            "total_rows_removed": 0,
            "processed_files": [],
            "failed_files": [],
        }

    successful_results: List[Dict[str, Any]] = []
    failed_files: List[Dict[str, Any]] = []

    total_rows_before = 0
    total_rows_after = 0
    total_rows_removed = 0

    for file_path in raw_csv_files:
        try:
            result = process_stock_file(file_path=file_path, output_dir=output_dir)
            successful_results.append(result)
            total_rows_before += result["rows_before"]
            total_rows_after += result["rows_after"]
            total_rows_removed += result["rows_removed"]
        except Exception as e:
            print(f"[ERROR] Failed processing '{file_path.name}': {e}", file=sys.stderr)
            failed_files.append({"file": file_path.name, "error": str(e)})

    # Verify uniform column schema across all processed files
    schema_uniform = True
    if successful_results:
        first_df = pd.read_csv(successful_results[0]["output_path"])
        first_cols = list(first_df.columns)
        for res in successful_results[1:]:
            curr_df = pd.read_csv(res["output_path"])
            if list(curr_df.columns) != first_cols:
                schema_uniform = False
                print(f"[SCHEMA MISMATCH] {res['processed_file']} differs from {successful_results[0]['processed_file']}")

    print("\n" + "=" * 60)
    print("  Step 3 Pipeline Execution Summary")
    print("=" * 60)
    print(f"Total Raw Stock Files Found   : {len(raw_csv_files)}")
    print(f"Successfully Processed        : {len(successful_results)}")
    print(f"Failed Files                  : {len(failed_files)}")
    print(f"Total Rows Before Cleaning    : {total_rows_before}")
    print(f"Total Rows After Cleaning     : {total_rows_after}")
    print(f"Total Rows Removed            : {total_rows_removed}")
    print(f"Schema Uniformity Verified    : {'PASSED' if schema_uniform else 'FAILED'}")
    print("=" * 60)

    return {
        "total_raw_files": len(raw_csv_files),
        "successful_count": len(successful_results),
        "failed_count": len(failed_files),
        "total_rows_before": total_rows_before,
        "total_rows_after": total_rows_after,
        "total_rows_removed": total_rows_removed,
        "schema_uniform": schema_uniform,
        "processed_files": [r["processed_file"] for r in successful_results],
        "failed_files": failed_files,
    }


if __name__ == "__main__":
    main()
