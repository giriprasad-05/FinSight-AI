"""
predict.py
-----------
Step 8 of the FinSight AI ML pipeline.

Production prediction engine for the v2 XGBoost trend model.
Accepts a ticker symbol, downloads recent OHLCV data from Yahoo Finance,
computes the exact 15 features used during v2 training, runs the model,
and returns structured prediction output.

Public API:
    predict_stock(ticker)          -- Download + predict for any ticker
    predict_from_csv(csv_path)     -- Offline prediction from a labeled CSV
    run_tests()                    -- Run consistency checks + live tests

Usage:
    python src/predict.py
    python src/predict.py AAPL
    python src/predict.py RELIANCE.NS
"""

import json
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import xgboost as xgb
import yfinance as yf

# Reuse validated feature-calculation logic from the training pipeline
from features import calculate_rsi

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ===================================================================
# Paths
# ===================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
SPLITS_DIR = BASE_DIR / "data" / "splits"

MODEL_V2_PATH = MODELS_DIR / "xgboost_trend_model_v2.json"
METADATA_V2_PATH = MODELS_DIR / "model_metadata_v2.json"
LABELED_DIR = BASE_DIR / "data" / "labeled"

# ===================================================================
# Constants
# ===================================================================
CODE_TO_LABEL = {0: "DOWN", 1: "FLAT", 2: "UP"}

# Number of calendar days of history to request from Yahoo Finance.
# MA_50 needs at least 50 trading days; Volatility_20 needs 20; RSI_14 needs
# 14 warmup. Request a substantial buffer to handle weekends/holidays.
HISTORY_CALENDAR_DAYS = 365   # ~250 trading days -- well above the 50-bar minimum

# Indian NSE tickers end with .NS or .BO
INDIAN_SUFFIXES = (".NS", ".BO")

# ===================================================================
# Singleton model loader (load once, reuse across calls)
# ===================================================================
_model_cache: Optional[xgb.XGBClassifier] = None
_metadata_cache: Optional[Dict[str, Any]] = None
_v2_features_cache: Optional[List[str]] = None


def _load_model_once() -> tuple:
    """
    Loads the v2 XGBoost model and its metadata on first call; returns
    cached objects on subsequent calls.

    Returns:
        (model, metadata, v2_features_list)

    Raises:
        FileNotFoundError: If model or metadata files are missing.
        ValueError: If the model feature count does not match v2 metadata.
    """
    global _model_cache, _metadata_cache, _v2_features_cache

    if _model_cache is not None:
        return _model_cache, _metadata_cache, _v2_features_cache

    if not MODEL_V2_PATH.exists():
        raise FileNotFoundError(
            f"V2 model file not found: {MODEL_V2_PATH}\n"
            "Run Step 7 (improve_model.py) to generate xgboost_trend_model_v2.json."
        )
    if not METADATA_V2_PATH.exists():
        raise FileNotFoundError(
            f"V2 metadata file not found: {METADATA_V2_PATH}"
        )

    # Load metadata
    with open(METADATA_V2_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    v2_features = metadata["feature_names"]
    expected_n = metadata["feature_count"]

    # Load model
    model = xgb.XGBClassifier()
    model.load_model(str(MODEL_V2_PATH))

    # Validate feature count via the booster
    booster_feat_count = model.n_features_in_
    if booster_feat_count != expected_n:
        raise ValueError(
            f"Feature count mismatch: model expects {booster_feat_count} features "
            f"but metadata declares {expected_n}. Model artifact may be corrupt."
        )
    if len(v2_features) != expected_n:
        raise ValueError(
            f"Metadata feature list has {len(v2_features)} entries "
            f"but feature_count is {expected_n}."
        )

    _model_cache = model
    _metadata_cache = metadata
    _v2_features_cache = v2_features
    return model, metadata, v2_features


# ===================================================================
# Feature calculation (inference-safe, mirrors training pipeline)
# ===================================================================

def _compute_features_for_inference(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Computes all technical features for inference using the exact same logic
    as the training pipeline (features.py).

    Calculates ALL features including MA_10 and MA_20 (they appear in
    features.py intermediate calculations), then subsets to the 15 v2 features.

    Args:
        df_raw: Raw OHLCV DataFrame with columns Open, High, Low, Close, Volume.
                Must have a Date column (string or datetime).
                May optionally have Ticker and Market columns.

    Returns:
        DataFrame with all computed features (not yet subset to v2 features).

    Raises:
        ValueError: If required OHLCV columns are missing or data is insufficient.
    """
    required = ["Date", "Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in required if c not in df_raw.columns]
    if missing:
        raise ValueError(f"Raw data is missing required OHLCV columns: {missing}")

    df = df_raw.copy()

    # Normalize date, sort ascending, drop duplicates
    df["Date_dt"] = pd.to_datetime(df["Date"])
    df = (df.sort_values("Date_dt", ascending=True)
            .drop_duplicates(subset=["Date_dt"])
            .reset_index(drop=True))
    df["Date"] = df["Date_dt"].dt.strftime("%Y-%m-%d")
    df = df.drop(columns=["Date_dt"])

    # Ensure numeric OHLCV
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 1. Daily_Return
    df["Daily_Return"] = df["Close"].pct_change()

    # 2. MA_5
    df["MA_5"] = df["Close"].rolling(window=5, min_periods=5).mean()

    # 3. MA_10 (computed but excluded from v2 feature set)
    df["MA_10"] = df["Close"].rolling(window=10, min_periods=10).mean()

    # 4. MA_20 (computed but excluded from v2 feature set)
    df["MA_20"] = df["Close"].rolling(window=20, min_periods=20).mean()

    # 5. MA_50
    df["MA_50"] = df["Close"].rolling(window=50, min_periods=50).mean()

    # 6. RSI_14 (reuse exact training implementation from features.py)
    df["RSI_14"] = calculate_rsi(df["Close"], period=14)

    # 7. MACD = EMA_12 - EMA_26
    ema_12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema_26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema_12 - ema_26

    # 8. MACD_Signal = 9-period EMA of MACD
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    # 9. Volatility_20 = 20-day rolling std of Daily_Return
    df["Volatility_20"] = df["Daily_Return"].rolling(window=20, min_periods=20).std()

    # 10. Volume_Change = (Vol - Vol_prev) / Vol_prev
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

    # Replace inf values with NaN
    df = df.replace([np.inf, -np.inf], np.nan)

    return df


def _select_v2_features(df_features: pd.DataFrame,
                         v2_features: List[str]) -> pd.DataFrame:
    """
    Subsets a fully-featured DataFrame to exactly the 15 v2 model features,
    drops rows with any NaN/Inf in those features, and validates the result.

    Args:
        df_features: DataFrame from _compute_features_for_inference().
        v2_features: Ordered list of 15 feature column names.

    Returns:
        Cleaned DataFrame with only the 15 v2 feature columns.

    Raises:
        ValueError: If any v2 feature column is missing or no valid rows remain.
    """
    missing = [c for c in v2_features if c not in df_features.columns]
    if missing:
        raise ValueError(f"Feature computation did not produce columns: {missing}")

    subset = df_features[v2_features].copy()

    # Drop rows with NaN in any v2 feature
    valid_mask = ~(subset.isna().any(axis=1) | np.isinf(subset.values).any(axis=1))
    subset = subset[valid_mask].reset_index(drop=True)

    # Re-align the date index for traceability
    date_subset = df_features.loc[valid_mask, "Date"].reset_index(drop=True)
    subset.insert(0, "Date", date_subset)

    if subset.empty:
        raise ValueError(
            "No valid feature rows after dropping NaN/Inf. "
            "Not enough historical data to compute all features. "
            "Need at least 50 trading days for MA_50."
        )

    return subset


# ===================================================================
# Market detection
# ===================================================================

def _detect_market(ticker: str) -> str:
    """Returns 'NSE' for Indian tickers, 'US' for all others."""
    if any(ticker.upper().endswith(s) for s in INDIAN_SUFFIXES):
        return "NSE"
    return "US"


# ===================================================================
# Core prediction function
# ===================================================================

def predict_stock(ticker: str) -> Dict[str, Any]:
    """
    Downloads recent OHLCV data for a ticker, computes v2 features,
    runs the XGBoost v2 model, and returns a structured prediction dict.

    Args:
        ticker: Stock ticker symbol (e.g. 'AAPL', 'RELIANCE.NS').

    Returns:
        Dict with keys:
            ticker, market, prediction, prediction_code, confidence,
            probabilities, indicators, data_date, model_version,
            feature_count, trading_rows_used.

    Raises:
        ValueError: For any data/feature/model problem.
        RuntimeError: For Yahoo Finance download failures.
    """
    ticker = ticker.strip().upper()
    market = _detect_market(ticker)

    # ----------------------------------------------------------------
    # 1. Load model (singleton)
    # ----------------------------------------------------------------
    model, metadata, v2_features = _load_model_once()

    # ----------------------------------------------------------------
    # 2. Download OHLCV data from Yahoo Finance
    # ----------------------------------------------------------------
    import datetime
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=HISTORY_CALENDAR_DAYS)

    try:
        raw = yf.download(
            ticker,
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            interval="1d",
            auto_adjust=True,
            progress=False,
        )
    except Exception as exc:
        raise RuntimeError(f"Yahoo Finance download failed for '{ticker}': {exc}") from exc

    if raw is None or raw.empty:
        raise ValueError(
            f"No data returned for ticker '{ticker}'. "
            "Check the ticker symbol — Indian NSE tickers need the '.NS' suffix."
        )

    # Flatten MultiIndex columns if present (yfinance >= 0.2 sometimes returns them)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [col[0] for col in raw.columns]

    # Reset index so Date becomes a column
    raw = raw.reset_index()
    raw = raw.rename(columns={"index": "Date", "Datetime": "Date"})
    if "Date" not in raw.columns and raw.index.name == "Date":
        raw = raw.reset_index()

    # Ensure standard OHLCV column names
    col_map = {c: c.capitalize() for c in raw.columns if c.lower() in
               ["open", "high", "low", "close", "volume"]}
    raw = raw.rename(columns=col_map)

    # Convert Date to string
    raw["Date"] = pd.to_datetime(raw["Date"]).dt.strftime("%Y-%m-%d")

    n_rows = len(raw)
    if n_rows < 60:
        raise ValueError(
            f"Insufficient history for '{ticker}': only {n_rows} trading days "
            f"returned (need at least 60 for MA_50 + warmup)."
        )

    # ----------------------------------------------------------------
    # 3. Compute features (exact same logic as training)
    # ----------------------------------------------------------------
    df_features = _compute_features_for_inference(raw)
    df_v2 = _select_v2_features(df_features, v2_features)

    # ----------------------------------------------------------------
    # 4. Select the most recent valid row
    # ----------------------------------------------------------------
    latest_row = df_v2.iloc[-1]
    latest_date = str(latest_row["Date"])
    feature_values = latest_row[v2_features].astype(np.float32).values.reshape(1, -1)

    # Validate no NaN/Inf slipped through
    if np.isnan(feature_values).any():
        raise ValueError(f"NaN in feature vector for '{ticker}' on {latest_date}.")
    if np.isinf(feature_values).any():
        raise ValueError(f"Infinite value in feature vector for '{ticker}' on {latest_date}.")

    # ----------------------------------------------------------------
    # 5. Run model
    # ----------------------------------------------------------------
    feature_df = pd.DataFrame(feature_values, columns=v2_features)
    probs = model.predict_proba(feature_df)[0]   # shape (3,)
    pred_code = int(np.argmax(probs))
    pred_label = CODE_TO_LABEL[pred_code]
    confidence = float(probs[pred_code])

    # ----------------------------------------------------------------
    # 6. Build output dict
    # ----------------------------------------------------------------
    # Pull individual indicator values for UI display
    feat_row = latest_row[v2_features]

    result = {
        "ticker": ticker,
        "market": market,
        "prediction": pred_label,
        "prediction_code": pred_code,
        "confidence": round(confidence, 6),
        "probabilities": {
            "DOWN": round(float(probs[0]), 6),
            "FLAT": round(float(probs[1]), 6),
            "UP":   round(float(probs[2]), 6),
        },
        "indicators": {
            "close":           round(float(feat_row["Close"]), 4),
            "daily_return":    round(float(feat_row["Daily_Return"]), 6),
            "ma_5":            round(float(feat_row["MA_5"]), 4),
            "ma_50":           round(float(feat_row["MA_50"]), 4),
            "rsi_14":          round(float(feat_row["RSI_14"]), 4),
            "macd":            round(float(feat_row["MACD"]), 6),
            "macd_signal":     round(float(feat_row["MACD_Signal"]), 6),
            "volatility_20":   round(float(feat_row["Volatility_20"]), 6),
            "volume_change":   round(float(feat_row["Volume_Change"]), 6),
            "price_change_pct":round(float(feat_row["Price_Change_Pct"]), 6),
            "high_low_pct":    round(float(feat_row["High_Low_Pct"]), 6),
        },
        "data_date": latest_date,
        "model_version": metadata.get("model_version", "v2"),
        "feature_count": len(v2_features),
        "trading_rows_used": len(df_v2),
    }

    return result


# ===================================================================
# Offline prediction from an existing labeled/processed CSV
# ===================================================================

def predict_from_csv(csv_path: str, row_index: int = -1) -> Dict[str, Any]:
    """
    Runs the v2 prediction engine against a specific row in an existing
    labeled or processed stock CSV. Useful for offline consistency testing
    without downloading live data.

    Feature columns are recomputed from the OHLCV data in the CSV so that
    the computation path is identical to the live prediction path.

    Args:
        csv_path: Path to a labeled or processed stock CSV file.
        row_index: Which row to predict on after feature calculation
                   (default -1 = last valid row).

    Returns:
        Prediction dict (same format as predict_stock), plus
        keys 'actual_label' and 'actual_code' if Trend_Label/Trend_Code
        exist in the file.

    Raises:
        FileNotFoundError: If csv_path does not exist.
        ValueError: For data or feature problems.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    model, metadata, v2_features = _load_model_once()

    df_raw = pd.read_csv(path)
    if df_raw.empty:
        raise ValueError(f"CSV file is empty: {path}")

    # Detect ticker/market from file if available
    ticker = str(df_raw["Ticker"].iloc[0]) if "Ticker" in df_raw.columns else path.stem
    market = str(df_raw["Market"].iloc[0]) if "Market" in df_raw.columns else _detect_market(ticker)

    # Extract actual ground truth if available (for audit purposes only)
    actual_label = None
    actual_code = None
    if "Trend_Label" in df_raw.columns and "Trend_Code" in df_raw.columns:
        # The labeled CSV has one fewer row than the processed (last row pruned)
        # We'll compare after feature selection
        pass

    # Compute features using the same path as live prediction
    df_features = _compute_features_for_inference(df_raw)
    df_v2 = _select_v2_features(df_features, v2_features)

    # Select desired row
    selected = df_v2.iloc[row_index]
    selected_date = str(selected["Date"])
    feature_values = selected[v2_features].astype(np.float32).values.reshape(1, -1)

    if np.isnan(feature_values).any() or np.isinf(feature_values).any():
        raise ValueError(f"Invalid (NaN/Inf) feature values at row_index={row_index}.")

    feature_df = pd.DataFrame(feature_values, columns=v2_features)
    probs = model.predict_proba(feature_df)[0]
    pred_code = int(np.argmax(probs))
    pred_label = CODE_TO_LABEL[pred_code]
    confidence = float(probs[pred_code])

    # Try to match actual label from labeled CSV by date
    if "Trend_Label" in df_raw.columns and "Trend_Code" in df_raw.columns:
        date_match = df_raw[df_raw["Date"] == selected_date]
        if not date_match.empty:
            actual_label = str(date_match.iloc[0]["Trend_Label"])
            actual_code = int(date_match.iloc[0]["Trend_Code"])

    feat_row = selected[v2_features]
    result = {
        "ticker": ticker,
        "market": market,
        "prediction": pred_label,
        "prediction_code": pred_code,
        "confidence": round(confidence, 6),
        "probabilities": {
            "DOWN": round(float(probs[0]), 6),
            "FLAT": round(float(probs[1]), 6),
            "UP":   round(float(probs[2]), 6),
        },
        "indicators": {
            "close":           round(float(feat_row["Close"]), 4),
            "daily_return":    round(float(feat_row["Daily_Return"]), 6),
            "ma_5":            round(float(feat_row["MA_5"]), 4),
            "ma_50":           round(float(feat_row["MA_50"]), 4),
            "rsi_14":          round(float(feat_row["RSI_14"]), 4),
            "macd":            round(float(feat_row["MACD"]), 6),
            "macd_signal":     round(float(feat_row["MACD_Signal"]), 6),
            "volatility_20":   round(float(feat_row["Volatility_20"]), 6),
            "volume_change":   round(float(feat_row["Volume_Change"]), 6),
            "price_change_pct":round(float(feat_row["Price_Change_Pct"]), 6),
            "high_low_pct":    round(float(feat_row["High_Low_Pct"]), 6),
        },
        "data_date": selected_date,
        "model_version": metadata.get("model_version", "v2"),
        "feature_count": len(v2_features),
        "source": "csv",
        "csv_path": str(path),
        "actual_label": actual_label,
        "actual_code": actual_code,
    }
    return result


# ===================================================================
# Printing helpers
# ===================================================================

def _print_prediction(result: Dict[str, Any], title: str = "") -> None:
    """Pretty-print a prediction result dict."""
    ticker = result["ticker"]
    sep = "=" * 55
    print(f"\n{sep}")
    if title:
        print(f"  {title}")
    print(f"  Ticker   : {ticker}  [{result['market']}]")
    print(f"  Date     : {result['data_date']}")
    print(f"  Prediction  : {result['prediction']}  (code={result['prediction_code']})")
    print(f"  Confidence  : {result['confidence']*100:.2f}%")
    print(f"  Probabilities:")
    p = result["probabilities"]
    prob_sum = p["DOWN"] + p["FLAT"] + p["UP"]
    print(f"    DOWN  = {p['DOWN']:.6f}  ({p['DOWN']*100:.2f}%)")
    print(f"    FLAT  = {p['FLAT']:.6f}  ({p['FLAT']*100:.2f}%)")
    print(f"    UP    = {p['UP']:.6f}  ({p['UP']*100:.2f}%)")
    print(f"    SUM   = {prob_sum:.8f}  {'OK' if abs(prob_sum - 1.0) < 1e-5 else 'WARNING: does not sum to 1'}")
    ind = result["indicators"]
    print(f"  Indicators:")
    print(f"    Close          : {ind['close']:.4f}")
    print(f"    Daily Return   : {ind['daily_return']*100:.4f}%")
    print(f"    MA_5           : {ind['ma_5']:.4f}")
    print(f"    MA_50          : {ind['ma_50']:.4f}")
    print(f"    RSI_14         : {ind['rsi_14']:.2f}")
    print(f"    MACD           : {ind['macd']:.6f}")
    print(f"    MACD Signal    : {ind['macd_signal']:.6f}")
    print(f"    Volatility_20  : {ind['volatility_20']:.6f}")
    print(f"    Volume Change  : {ind['volume_change']*100:.4f}%")
    print(f"    Price Chg Pct  : {ind['price_change_pct']*100:.4f}%")
    print(f"    High-Low Pct   : {ind['high_low_pct']*100:.4f}%")
    if result.get("actual_label") is not None:
        match = "CORRECT" if result["actual_label"] == result["prediction"] else "WRONG"
        print(f"  Actual Label   : {result['actual_label']} (code={result['actual_code']}) --> {match}")
    print(sep)


# ===================================================================
# Audit / Consistency test
# ===================================================================

def run_consistency_test() -> bool:
    """
    Selects a known historical row from an existing labeled CSV, runs the
    prediction engine against it using predict_from_csv(), then directly
    feeds the same feature values into the model to verify both paths
    produce identical probabilities.

    Returns True if probabilities match within 1e-6 tolerance.
    """
    print("\n" + "=" * 55)
    print("  CONSISTENCY / AUDIT TEST")
    print("=" * 55)

    # Use AAPL labeled file as the audit target
    audit_csv = LABELED_DIR / "AAPL_labeled.csv"
    if not audit_csv.exists():
        # Try any available labeled file
        available = list(LABELED_DIR.glob("*.csv"))
        if not available:
            print("  [SKIP] No labeled files found for audit test.")
            return True
        audit_csv = available[0]

    print(f"  Audit file: {audit_csv.name}")

    # predict_from_csv produces a prediction from the last valid row
    result = predict_from_csv(str(audit_csv), row_index=-1)
    _print_prediction(result, "Audit CSV Row")

    # Now independently load the same model and feed the same feature values
    model, metadata, v2_features = _load_model_once()

    ind = result["indicators"]
    # Reconstruct the raw feature vector from the indicators dict
    # We need the full 15-column v2 feature vector; for the non-indicator
    # OHLCV features we re-read them from the result
    # Instead: re-read the CSV and recompute to get the full row
    df_raw = pd.read_csv(audit_csv)
    df_features = _compute_features_for_inference(df_raw)
    df_v2 = _select_v2_features(df_features, v2_features)
    latest_row = df_v2.iloc[-1]
    feature_values = latest_row[v2_features].astype(np.float32).values.reshape(1, -1)

    feature_df = pd.DataFrame(feature_values, columns=v2_features)
    direct_probs = model.predict_proba(feature_df)[0]

    engine_probs = np.array([
        result["probabilities"]["DOWN"],
        result["probabilities"]["FLAT"],
        result["probabilities"]["UP"],
    ])

    max_diff = np.abs(direct_probs - engine_probs).max()
    passed = max_diff < 1e-5

    print(f"\n  Direct model probs: DOWN={direct_probs[0]:.6f} FLAT={direct_probs[1]:.6f} UP={direct_probs[2]:.6f}")
    print(f"  Engine probs      : DOWN={engine_probs[0]:.6f} FLAT={engine_probs[1]:.6f} UP={engine_probs[2]:.6f}")
    print(f"  Max absolute diff : {max_diff:.2e}")
    print(f"  Consistency check : {'PASS' if passed else 'FAIL -- probabilities do not match!'}")

    return passed


# ===================================================================
# Live tests
# ===================================================================

def run_tests() -> None:
    """
    Downloads live data and runs predictions for 6 test tickers (3 US + 3 India).
    Also runs the offline consistency audit test.
    """
    print("=" * 55)
    print("  FinSight AI -- Step 8: Prediction Engine Tests")
    print("=" * 55)

    # Load model once up front
    model, metadata, v2_features = _load_model_once()
    print(f"  Model loaded  : {MODEL_V2_PATH.name}")
    print(f"  XGBoost       : {xgb.__version__}")
    print(f"  Features ({len(v2_features)}): {v2_features}")
    print(f"  Best iter     : {metadata.get('best_iteration', 'N/A')}")

    # ----------------------------------------------------------------
    # Offline CSV tests first (no network required)
    # ----------------------------------------------------------------
    print("\n--- OFFLINE CSV TESTS ---")
    csv_tickers = ["AAPL", "MSFT", "NVDA", "RELIANCE", "TCS", "INFY"]
    for stem in csv_tickers:
        csv_path = LABELED_DIR / f"{stem}_labeled.csv"
        # Try with .NS suffix for Indian stocks
        if not csv_path.exists():
            csv_path = LABELED_DIR / f"{stem}.NS_labeled.csv"
        if not csv_path.exists():
            print(f"  [SKIP] No labeled file found for {stem}")
            continue
        try:
            result = predict_from_csv(str(csv_path))
            _print_prediction(result, f"CSV Test -- {result['ticker']}")
        except Exception as exc:
            print(f"  [ERROR] {stem}: {exc}")

    # ----------------------------------------------------------------
    # Consistency / audit test
    # ----------------------------------------------------------------
    run_consistency_test()

    # ----------------------------------------------------------------
    # Live market tests (require internet)
    # ----------------------------------------------------------------
    print("\n--- LIVE MARKET TESTS ---")
    live_tickers = ["AAPL", "MSFT", "NVDA", "RELIANCE.NS", "TCS.NS", "INFY.NS"]
    all_ok = True
    for ticker in live_tickers:
        try:
            result = predict_stock(ticker)
            _print_prediction(result, f"Live -- {ticker}")

            # Sanity assertions
            prob_sum = sum(result["probabilities"].values())
            assert abs(prob_sum - 1.0) < 1e-4, f"Probs don't sum to 1: {prob_sum}"
            assert result["prediction"] == CODE_TO_LABEL[result["prediction_code"]], \
                "Predicted label/code mismatch"
            assert result["prediction_code"] == int(np.argmax([
                result["probabilities"]["DOWN"],
                result["probabilities"]["FLAT"],
                result["probabilities"]["UP"],
            ])), "Predicted code is not the argmax class"
            assert 0.0 <= result["confidence"] <= 1.0, "Confidence out of range"

        except Exception as exc:
            print(f"  [ERROR] {ticker}: {exc}")
            all_ok = False

    print("\n" + "=" * 55)
    print(f"  All live assertions passed: {all_ok}")
    print("  Step 8 tests complete.")
    print("=" * 55)


# ===================================================================
# Entry point
# ===================================================================

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Single ticker mode: python src/predict.py AAPL
        ticker_arg = sys.argv[1].strip().upper()
        print(f"Running single prediction for: {ticker_arg}")
        try:
            res = predict_stock(ticker_arg)
            _print_prediction(res, f"Prediction -- {ticker_arg}")
        except Exception as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Full test suite
        run_tests()
