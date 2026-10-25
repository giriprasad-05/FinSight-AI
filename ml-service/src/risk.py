"""
risk.py
--------
Step 9 of the FinSight AI ML pipeline.

Investment Risk Assessment Engine.

Produces a 0-100 risk score for any stock ticker using four quantitative
components derived from historical daily returns:

    1. Annualized Volatility     (weight 35%)
    2. Maximum Drawdown          (weight 30%)
    3. Downside Volatility       (weight 20%)
    4. Recent Volatility         (weight 15%)

Each raw metric is converted to a 0-100 score using piecewise-linear
normalization anchored to the empirical distribution of the 35-stock
FinSight AI training universe (computed during Step 9 reference analysis).

The thresholds, weights, and normalization anchor points are documented
and saved to ml-service/models/risk_metadata.json.

THIS IS NOT FINANCIAL ADVICE. Risk scores are statistical estimates only.

Usage:
    python src/risk.py                    # test suite (6 tickers)
    python src/risk.py AAPL               # single ticker
    python src/risk.py RELIANCE.NS        # Indian NSE ticker
"""

import json
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ===================================================================
# Paths
# ===================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
RISK_METADATA_PATH = MODELS_DIR / "risk_metadata.json"

# ===================================================================
# Configuration constants
# ===================================================================

# ---- Calculation windows ----
LONG_TERM_DAYS_CALENDAR = 504   # ~2 calendar years fetched to get ~504 trading days
LONG_TERM_DAYS_TRADING  = 252   # use most recent 252 trading days for long-term metrics
RECENT_DAYS_TRADING     = 20    # rolling recent volatility window
TRADING_DAYS_PER_YEAR   = 252

# ---- Component weights (must sum to 1.0) ----
WEIGHTS = {
    "volatility":          0.35,
    "max_drawdown":        0.30,
    "downside_volatility": 0.20,
    "recent_volatility":   0.15,
}

# ---- Risk level thresholds ----
RISK_THRESHOLDS = {
    "LOW_MAX":    33,   # score 0-33 = LOW
    "MEDIUM_MAX": 66,   # score 34-66 = MEDIUM
    # score 67-100 = HIGH
}

# ---- Piecewise-linear normalization anchors ----
#
# Each metric is mapped to a 0-100 risk score via piecewise linear
# interpolation between empirical percentile anchors.
#
# Anchors derived from the 35-stock FinSight AI training universe:
#   - 5th percentile of that universe maps to score 5   (nearly lowest risk)
#   - 25th percentile maps to score 25
#   - 50th percentile maps to score 50  (median = moderate risk)
#   - 75th percentile maps to score 75
#   - 95th percentile maps to score 95  (high risk)
#
# Values below the 5th percentile are linearly extrapolated toward 0.
# Values above the 95th percentile are linearly extrapolated toward 100
# but clamped to [0, 100].
#
# This ensures:
#   - A "median" stock in the universe always scores ~50.
#   - An extremely volatile/risky stock scores near 100.
#   - A low-volatility stable stock scores near 0.
#   - The normalization is fully deterministic and reproducible.

NORMALIZATION_ANCHORS = {
    # (raw_value, score) pairs — derived from Step 9 reference analysis
    "volatility": [
        (0.1904, 5.0),    # 5th pct
        (0.2217, 25.0),   # 25th pct
        (0.2502, 50.0),   # 50th pct
        (0.3344, 75.0),   # 75th pct
        (0.6644, 95.0),   # 95th pct
    ],
    "max_drawdown": [
        (0.1364, 5.0),
        (0.1950, 25.0),
        (0.2517, 50.0),
        (0.3489, 75.0),
        (0.4175, 95.0),
    ],
    "downside_volatility": [
        (0.1299, 5.0),
        (0.1539, 25.0),
        (0.1828, 50.0),
        (0.2145, 75.0),
        (0.3477, 95.0),
    ],
    "recent_volatility": [
        (0.1312, 5.0),
        (0.1780, 25.0),
        (0.2179, 50.0),
        (0.3903, 75.0),
        (0.6583, 95.0),
    ],
}

# Explanation thresholds (score-based, per component)
EXPLANATION_THRESHOLDS = {
    "high":   75.0,   # score >= 75 => elevated risk explanation
    "medium": 50.0,   # score >= 50 => moderate risk explanation
}

# Indian NSE/BSE ticker suffixes
INDIAN_SUFFIXES = (".NS", ".BO")

# ===================================================================
# Helper functions
# ===================================================================

def _detect_market(ticker: str) -> str:
    """Returns 'NSE' for Indian tickers, 'US' for all others."""
    if any(ticker.upper().endswith(s) for s in INDIAN_SUFFIXES):
        return "NSE"
    return "US"


def _piecewise_linear_score(value: float, anchors: List[Tuple[float, float]]) -> float:
    """
    Maps a raw metric value to a 0-100 risk score using piecewise linear
    interpolation between the provided (raw, score) anchor pairs.

    For values below the first anchor or above the last anchor, the function
    linearly extrapolates using the slope of the nearest segment, then
    clamps the result to [0, 100].

    Args:
        value:   Raw metric value (e.g. annualized volatility = 0.35).
        anchors: List of (raw_value, score) tuples, sorted by raw_value ascending.

    Returns:
        Float score in [0, 100].
    """
    # Ensure anchors are sorted by raw value
    sorted_anchors = sorted(anchors, key=lambda x: x[0])
    raw_vals = [a[0] for a in sorted_anchors]
    scores   = [a[1] for a in sorted_anchors]

    # Direct interpolation
    score = float(np.interp(value, raw_vals, scores))

    # np.interp already clamps at boundary values, but we extend linearly
    # for values beyond the last anchor (to penalise extreme outliers)
    if value > raw_vals[-1]:
        # Linear extrapolation from the last segment
        slope = (scores[-1] - scores[-2]) / (raw_vals[-1] - raw_vals[-2] + 1e-12)
        score = scores[-1] + slope * (value - raw_vals[-1])
    elif value < raw_vals[0]:
        # Linear extrapolation below the first anchor
        slope = (scores[1] - scores[0]) / (raw_vals[1] - raw_vals[0] + 1e-12)
        score = scores[0] + slope * (value - raw_vals[0])

    return float(np.clip(score, 0.0, 100.0))


def _fetch_ohlcv(ticker: str) -> pd.DataFrame:
    """
    Downloads OHLCV daily data from Yahoo Finance for the risk window.

    Args:
        ticker: Ticker symbol (e.g. 'AAPL', 'RELIANCE.NS').

    Returns:
        DataFrame with columns: Date, Open, High, Low, Close, Volume.
        Sorted ascending by Date.

    Raises:
        RuntimeError: On Yahoo Finance failure.
        ValueError: If insufficient data is returned.
    """
    import datetime
    end_date   = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=LONG_TERM_DAYS_CALENDAR)

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
            f"No data returned for '{ticker}'. "
            "Verify the ticker symbol. Indian NSE tickers require '.NS' suffix."
        )

    # Flatten MultiIndex columns if present
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [col[0] for col in raw.columns]

    raw = raw.reset_index()
    raw = raw.rename(columns={"index": "Date", "Datetime": "Date"})

    col_map = {c: c.capitalize() for c in raw.columns
               if c.lower() in ["open", "high", "low", "close", "volume"]}
    raw = raw.rename(columns=col_map)

    raw["Date"] = pd.to_datetime(raw["Date"]).dt.strftime("%Y-%m-%d")
    raw = raw.sort_values("Date").drop_duplicates(subset=["Date"]).reset_index(drop=True)

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in raw.columns:
            raw[col] = pd.to_numeric(raw[col], errors="coerce")

    raw = raw.dropna(subset=["Close"]).reset_index(drop=True)

    if len(raw) < RECENT_DAYS_TRADING + 5:
        raise ValueError(
            f"Insufficient data for '{ticker}': only {len(raw)} trading days returned."
        )

    return raw


# ===================================================================
# Risk metric calculations
# ===================================================================

def _compute_daily_returns(close: pd.Series) -> pd.Series:
    """Computes daily percentage returns from a Close price series."""
    returns = close.pct_change().dropna()
    # Replace any inf/-inf with NaN and drop
    returns = returns.replace([np.inf, -np.inf], np.nan).dropna()
    return returns


def _annualized_volatility(returns: pd.Series) -> float:
    """
    Annualized historical volatility = std(daily_returns) * sqrt(252).

    Args:
        returns: Daily return series (decimal, e.g. 0.012 = +1.2%).

    Returns:
        Annualized volatility as a decimal (e.g. 0.25 = 25%).
    """
    if len(returns) < 5:
        raise ValueError("Insufficient returns for volatility calculation (need >= 5).")
    return float(returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR))


def _max_drawdown(close: pd.Series) -> float:
    """
    Maximum peak-to-trough percentage drawdown over the full price series.

    Returns the absolute value of the maximum drawdown (e.g. 0.35 = 35% drop).

    Args:
        close: Close price series (sorted ascending by date).

    Returns:
        Max drawdown as a positive decimal.
    """
    close_arr = close.values
    if len(close_arr) < 2:
        return 0.0
    rolling_max = np.maximum.accumulate(close_arr)
    # Avoid division by zero for zero-price edge case
    with np.errstate(invalid="ignore", divide="ignore"):
        drawdowns = np.where(
            rolling_max > 0,
            (close_arr - rolling_max) / rolling_max,
            0.0,
        )
    return float(abs(np.min(drawdowns)))


def _downside_volatility(returns: pd.Series) -> float:
    """
    Annualized downside volatility: std of NEGATIVE daily returns only.

    This captures asymmetric loss risk more precisely than total volatility.
    If there are too few negative return observations, falls back to total
    annualized volatility.

    Args:
        returns: Daily return series.

    Returns:
        Annualized downside volatility as a decimal.
    """
    neg_returns = returns[returns < 0]
    if len(neg_returns) < 5:
        # Fallback: use total volatility if almost no negative days
        return _annualized_volatility(returns)
    return float(neg_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR))


def _recent_volatility(returns: pd.Series, window: int = RECENT_DAYS_TRADING) -> float:
    """
    Annualized volatility calculated over the most recent `window` trading days.

    Args:
        returns: Daily return series (full history, sorted ascending).
        window:  Number of recent trading days to use.

    Returns:
        Annualized recent volatility as a decimal.
    """
    recent = returns.tail(window).dropna()
    if len(recent) < 5:
        # Not enough recent data — use total volatility
        return _annualized_volatility(returns)
    return float(recent.std() * np.sqrt(TRADING_DAYS_PER_YEAR))


# ===================================================================
# Explanation generation
# ===================================================================

def _generate_explanations(
    components: Dict[str, float],
    raw_metrics: Dict[str, float],
) -> List[str]:
    """
    Generates human-readable, metric-grounded explanation strings.

    Explanations are triggered by component risk scores exceeding
    configurable thresholds. No financial advice is given.

    Args:
        components:  Dict of component risk scores (0-100).
        raw_metrics: Dict of raw metric values.

    Returns:
        List of explanation strings.
    """
    explanations = []

    vol_score  = components["volatility"]
    dd_score   = components["max_drawdown"]
    ds_score   = components["downside_volatility"]
    rec_score  = components["recent_volatility"]

    ann_vol  = raw_metrics["annualized_volatility"]
    max_dd   = raw_metrics["max_drawdown"]
    ds_vol   = raw_metrics["downside_volatility"]
    rec_vol  = raw_metrics["recent_volatility"]

    HIGH   = EXPLANATION_THRESHOLDS["high"]
    MEDIUM = EXPLANATION_THRESHOLDS["medium"]

    # Volatility
    if vol_score >= HIGH:
        explanations.append(
            f"Annualized volatility is high ({ann_vol*100:.1f}%), indicating "
            f"large typical price swings over the past year."
        )
    elif vol_score >= MEDIUM:
        explanations.append(
            f"Annualized volatility is moderate ({ann_vol*100:.1f}%) relative to "
            f"the broader stock universe."
        )
    else:
        explanations.append(
            f"Annualized volatility is relatively low ({ann_vol*100:.1f}%), "
            f"suggesting historically stable price movement."
        )

    # Maximum drawdown
    if dd_score >= HIGH:
        explanations.append(
            f"The maximum historical peak-to-trough decline was {max_dd*100:.1f}%, "
            f"indicating significant past drawdown risk."
        )
    elif dd_score >= MEDIUM:
        explanations.append(
            f"The stock has experienced a notable drawdown of {max_dd*100:.1f}% "
            f"over the analysis window."
        )
    else:
        explanations.append(
            f"Historical drawdown has been contained at {max_dd*100:.1f}%, "
            f"suggesting limited peak-to-trough exposure."
        )

    # Downside volatility
    if ds_score >= HIGH:
        explanations.append(
            f"Downside volatility is elevated ({ds_vol*100:.1f}% annualized), "
            f"meaning negative return days are unusually volatile."
        )
    elif ds_score >= MEDIUM:
        explanations.append(
            f"Downside volatility ({ds_vol*100:.1f}%) suggests moderate loss "
            f"magnitude on negative trading days."
        )

    # Recent volatility
    if rec_score >= HIGH:
        explanations.append(
            f"Recent 20-day volatility is elevated ({rec_vol*100:.1f}% annualized), "
            f"suggesting current market instability for this stock."
        )
    elif rec_score >= MEDIUM:
        explanations.append(
            f"Recent 20-day volatility ({rec_vol*100:.1f}%) is above the historical "
            f"median, indicating elevated near-term uncertainty."
        )
    elif rec_score < 25:
        explanations.append(
            f"Recent 20-day volatility is low ({rec_vol*100:.1f}%), "
            f"suggesting relative calm in current price movement."
        )

    if not explanations:
        explanations.append("All risk components are within normal historical ranges.")

    return explanations


# ===================================================================
# Core risk assessment function
# ===================================================================

def assess_risk(ticker: str) -> Dict[str, Any]:
    """
    Assesses the investment risk of a given stock ticker based on
    historical price data.

    Method:
        1. Downloads 504 calendar days (~2 years) of daily OHLCV data.
        2. Uses the most recent 252 trading days for long-term metrics.
        3. Computes four quantitative risk components.
        4. Normalizes each to 0-100 via piecewise linear percentile mapping
           anchored to the 35-stock FinSight AI training universe.
        5. Combines with fixed weights into a composite risk score (0-100).
        6. Classifies into LOW / MEDIUM / HIGH.
        7. Generates human-readable explanations.

    Args:
        ticker: Stock ticker symbol. Indian NSE tickers require '.NS' suffix.

    Returns:
        Dict with keys:
            ticker, market, risk_score, risk_level, components,
            raw_metrics, explanations, data_date, trading_days_used,
            long_term_window, recent_window.

    Raises:
        RuntimeError: On data download failure.
        ValueError: On insufficient data or calculation errors.
    """
    ticker = ticker.strip().upper()
    market = _detect_market(ticker)

    # ----------------------------------------------------------------
    # 1. Fetch OHLCV data
    # ----------------------------------------------------------------
    df = _fetch_ohlcv(ticker)
    latest_date = df["Date"].iloc[-1]

    # ----------------------------------------------------------------
    # 2. Compute daily returns over full history and long-term window
    # ----------------------------------------------------------------
    close_full = df["Close"]
    returns_full = _compute_daily_returns(close_full)

    # Use most recent LONG_TERM_DAYS_TRADING rows for long-term metrics
    lt_rows = min(len(df), LONG_TERM_DAYS_TRADING)
    df_lt = df.tail(lt_rows).reset_index(drop=True)
    close_lt  = df_lt["Close"]
    returns_lt = _compute_daily_returns(close_lt)

    if len(returns_lt) < 30:
        raise ValueError(
            f"Only {len(returns_lt)} valid return observations for '{ticker}'. "
            f"Need at least 30 for reliable risk assessment."
        )

    # ----------------------------------------------------------------
    # 3. Compute raw risk metrics
    # ----------------------------------------------------------------
    ann_vol  = _annualized_volatility(returns_lt)
    max_dd   = _max_drawdown(close_lt)
    ds_vol   = _downside_volatility(returns_lt)
    rec_vol  = _recent_volatility(returns_full, window=RECENT_DAYS_TRADING)

    # Validate no NaN / Inf slipped through
    for name, val in [("ann_vol", ann_vol), ("max_dd", max_dd),
                       ("ds_vol", ds_vol), ("rec_vol", rec_vol)]:
        if np.isnan(val) or np.isinf(val):
            raise ValueError(f"Invalid (NaN/Inf) metric computed for '{name}'.")

    # ----------------------------------------------------------------
    # 4. Normalize each metric to 0-100 using piecewise linear anchors
    # ----------------------------------------------------------------
    score_vol  = _piecewise_linear_score(ann_vol, NORMALIZATION_ANCHORS["volatility"])
    score_dd   = _piecewise_linear_score(max_dd,  NORMALIZATION_ANCHORS["max_drawdown"])
    score_ds   = _piecewise_linear_score(ds_vol,  NORMALIZATION_ANCHORS["downside_volatility"])
    score_rec  = _piecewise_linear_score(rec_vol, NORMALIZATION_ANCHORS["recent_volatility"])

    components = {
        "volatility":          round(score_vol, 2),
        "max_drawdown":        round(score_dd, 2),
        "downside_volatility": round(score_ds, 2),
        "recent_volatility":   round(score_rec, 2),
    }

    # Validate component scores
    for name, score in components.items():
        if not (0.0 <= score <= 100.0):
            raise ValueError(f"Component score out of range for '{name}': {score}")

    # ----------------------------------------------------------------
    # 5. Weighted composite risk score
    # ----------------------------------------------------------------
    risk_score_raw = (
        WEIGHTS["volatility"]          * score_vol +
        WEIGHTS["max_drawdown"]        * score_dd  +
        WEIGHTS["downside_volatility"] * score_ds  +
        WEIGHTS["recent_volatility"]   * score_rec
    )
    risk_score = round(float(np.clip(risk_score_raw, 0.0, 100.0)), 2)

    # ----------------------------------------------------------------
    # 6. Risk level classification
    # ----------------------------------------------------------------
    if risk_score <= RISK_THRESHOLDS["LOW_MAX"]:
        risk_level = "LOW"
    elif risk_score <= RISK_THRESHOLDS["MEDIUM_MAX"]:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    # ----------------------------------------------------------------
    # 7. Raw metrics (human-readable values for downstream display)
    # ----------------------------------------------------------------
    raw_metrics = {
        "annualized_volatility": round(ann_vol, 6),
        "max_drawdown":          round(max_dd, 6),
        "downside_volatility":   round(ds_vol, 6),
        "recent_volatility":     round(rec_vol, 6),
    }

    # ----------------------------------------------------------------
    # 8. Generate explanations
    # ----------------------------------------------------------------
    explanations = _generate_explanations(components, raw_metrics)

    return {
        "ticker":           ticker,
        "market":           market,
        "risk_score":       risk_score,
        "risk_level":       risk_level,
        "components":       components,
        "raw_metrics":      raw_metrics,
        "explanations":     explanations,
        "data_date":        latest_date,
        "trading_days_used": int(lt_rows),
        "long_term_window": LONG_TERM_DAYS_TRADING,
        "recent_window":    RECENT_DAYS_TRADING,
    }


def assess_risk_from_df(df: pd.DataFrame, ticker: str = "UNKNOWN") -> Dict[str, Any]:
    """
    Offline variant of assess_risk() -- accepts a pre-loaded DataFrame
    instead of downloading from Yahoo Finance. Useful for testing and
    offline consistency checks.

    Args:
        df:     DataFrame with at least columns: Date, Close.
        ticker: Ticker symbol string for labelling.

    Returns:
        Same structure as assess_risk().
    """
    ticker = ticker.strip().upper()
    market = _detect_market(ticker)

    # Normalise and sort
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    df = df.sort_values("Date").drop_duplicates(subset=["Date"]).reset_index(drop=True)
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df = df.dropna(subset=["Close"]).reset_index(drop=True)

    if len(df) < RECENT_DAYS_TRADING + 5:
        raise ValueError(f"Insufficient data in DataFrame: only {len(df)} rows.")

    latest_date = df["Date"].iloc[-1]
    close_full = df["Close"]
    returns_full = _compute_daily_returns(close_full)

    lt_rows = min(len(df), LONG_TERM_DAYS_TRADING)
    df_lt = df.tail(lt_rows).reset_index(drop=True)
    close_lt  = df_lt["Close"]
    returns_lt = _compute_daily_returns(close_lt)

    ann_vol  = _annualized_volatility(returns_lt)
    max_dd   = _max_drawdown(close_lt)
    ds_vol   = _downside_volatility(returns_lt)
    rec_vol  = _recent_volatility(returns_full, window=RECENT_DAYS_TRADING)

    score_vol  = _piecewise_linear_score(ann_vol, NORMALIZATION_ANCHORS["volatility"])
    score_dd   = _piecewise_linear_score(max_dd,  NORMALIZATION_ANCHORS["max_drawdown"])
    score_ds   = _piecewise_linear_score(ds_vol,  NORMALIZATION_ANCHORS["downside_volatility"])
    score_rec  = _piecewise_linear_score(rec_vol, NORMALIZATION_ANCHORS["recent_volatility"])

    components = {
        "volatility":          round(score_vol, 2),
        "max_drawdown":        round(score_dd, 2),
        "downside_volatility": round(score_ds, 2),
        "recent_volatility":   round(score_rec, 2),
    }

    risk_score_raw = (
        WEIGHTS["volatility"]          * score_vol +
        WEIGHTS["max_drawdown"]        * score_dd  +
        WEIGHTS["downside_volatility"] * score_ds  +
        WEIGHTS["recent_volatility"]   * score_rec
    )
    risk_score = round(float(np.clip(risk_score_raw, 0.0, 100.0)), 2)

    if risk_score <= RISK_THRESHOLDS["LOW_MAX"]:
        risk_level = "LOW"
    elif risk_score <= RISK_THRESHOLDS["MEDIUM_MAX"]:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    raw_metrics = {
        "annualized_volatility": round(ann_vol, 6),
        "max_drawdown":          round(max_dd, 6),
        "downside_volatility":   round(ds_vol, 6),
        "recent_volatility":     round(rec_vol, 6),
    }
    explanations = _generate_explanations(components, raw_metrics)

    return {
        "ticker":           ticker,
        "market":           market,
        "risk_score":       risk_score,
        "risk_level":       risk_level,
        "components":       components,
        "raw_metrics":      raw_metrics,
        "explanations":     explanations,
        "data_date":        latest_date,
        "trading_days_used": int(lt_rows),
        "long_term_window": LONG_TERM_DAYS_TRADING,
        "recent_window":    RECENT_DAYS_TRADING,
    }


# ===================================================================
# Printing helpers
# ===================================================================

def _print_risk(result: Dict[str, Any]) -> None:
    """Pretty-prints a risk assessment result."""
    ticker = result["ticker"]
    sep = "=" * 58
    LEVEL_ICONS = {"LOW": "[LOW]   ", "MEDIUM": "[MED]   ", "HIGH": "[HIGH]  "}
    icon = LEVEL_ICONS.get(result["risk_level"], "")
    print(f"\n{sep}")
    print(f"  Risk Assessment -- {ticker}  [{result['market']}]")
    print(f"{sep}")
    print(f"  Date              : {result['data_date']}")
    print(f"  Trading Days Used : {result['trading_days_used']}")
    print(f"  Risk Score        : {result['risk_score']:.1f} / 100")
    print(f"  Risk Level        : {icon}{result['risk_level']}")
    print(f"\n  Component Scores (0-100):")
    c = result["components"]
    print(f"    Volatility (35%)          : {c['volatility']:.1f}")
    print(f"    Max Drawdown (30%)        : {c['max_drawdown']:.1f}")
    print(f"    Downside Volatility (20%) : {c['downside_volatility']:.1f}")
    print(f"    Recent Volatility (15%)   : {c['recent_volatility']:.1f}")
    print(f"\n  Raw Metrics:")
    rm = result["raw_metrics"]
    print(f"    Annualized Volatility : {rm['annualized_volatility']*100:.2f}%")
    print(f"    Max Drawdown          : {rm['max_drawdown']*100:.2f}%")
    print(f"    Downside Volatility   : {rm['downside_volatility']*100:.2f}%")
    print(f"    Recent Volatility (20d): {rm['recent_volatility']*100:.2f}%")
    print(f"\n  Explanations:")
    for i, ex in enumerate(result["explanations"], 1):
        print(f"    {i}. {ex}")
    print(sep)


# ===================================================================
# Validation checks
# ===================================================================

def _validate_result(result: Dict[str, Any]) -> bool:
    """
    Runs sanity checks on a risk assessment result.
    Returns True if all checks pass, raises AssertionError otherwise.
    """
    assert 0.0 <= result["risk_score"] <= 100.0, \
        f"Risk score out of range: {result['risk_score']}"
    assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH"), \
        f"Invalid risk level: {result['risk_level']}"
    for name, val in result["components"].items():
        assert 0.0 <= val <= 100.0, f"Component {name} out of range: {val}"
    for name, val in result["raw_metrics"].items():
        assert not np.isnan(val), f"NaN in raw metric {name}"
        assert not np.isinf(val), f"Inf in raw metric {name}"
    assert len(result["explanations"]) >= 1, "No explanations generated"
    return True


# ===================================================================
# Risk metadata persistence
# ===================================================================

def save_risk_metadata() -> None:
    """Saves the risk engine methodology config to models/risk_metadata.json."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {
        "description": "FinSight AI Step 9 -- Investment Risk Assessment Engine",
        "model_type": "Rule-based quantitative risk scoring",
        "risk_components": list(WEIGHTS.keys()),
        "weights": WEIGHTS,
        "risk_thresholds": {
            "LOW":    [0, RISK_THRESHOLDS["LOW_MAX"]],
            "MEDIUM": [RISK_THRESHOLDS["LOW_MAX"] + 1, RISK_THRESHOLDS["MEDIUM_MAX"]],
            "HIGH":   [RISK_THRESHOLDS["MEDIUM_MAX"] + 1, 100],
        },
        "normalization_method": (
            "Piecewise linear interpolation between empirical percentile anchors "
            "derived from the 35-stock FinSight AI training universe. "
            "Anchors: 5th/25th/50th/75th/95th percentiles map to scores 5/25/50/75/95. "
            "Values outside anchor range are linearly extrapolated and clamped to [0,100]."
        ),
        "normalization_anchors": NORMALIZATION_ANCHORS,
        "calculation_windows": {
            "long_term_trading_days": LONG_TERM_DAYS_TRADING,
            "recent_trading_days":    RECENT_DAYS_TRADING,
            "calendar_days_fetched":  LONG_TERM_DAYS_CALENDAR,
            "trading_days_per_year":  TRADING_DAYS_PER_YEAR,
        },
        "metric_definitions": {
            "annualized_volatility":
                "std(daily_returns) * sqrt(252) over last 252 trading days",
            "max_drawdown":
                "max((close - rolling_peak) / rolling_peak) over last 252 trading days",
            "downside_volatility":
                "std(negative daily returns only) * sqrt(252) over last 252 trading days",
            "recent_volatility":
                "std(daily_returns) * sqrt(252) over most recent 20 trading days",
        },
        "formula":
            "risk_score = 0.35*vol_score + 0.30*dd_score + 0.20*ds_score + 0.15*rec_score",
        "reference_universe":
            "35 stocks (15 US + 20 Indian NSE), ~2018-2026 daily OHLCV data",
        "disclaimer":
            "Risk scores are statistical estimates only. Not financial advice.",
    }
    with open(RISK_METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"[SAVED] Risk metadata: {RISK_METADATA_PATH}")


# ===================================================================
# Test suite
# ===================================================================

def run_tests() -> None:
    """Runs risk assessment for 6 test tickers and validates all outputs."""
    print("=" * 58)
    print("  FinSight AI -- Step 9: Risk Assessment Engine Tests")
    print("=" * 58)
    print(f"  Formula: 35% Volatility + 30% MaxDD + 20% DownsideVol + 15% RecentVol")
    print(f"  Normalization: Piecewise linear percentile anchors (35-stock universe)")
    print(f"  LOW: 0-33  |  MEDIUM: 34-66  |  HIGH: 67-100")
    print("=" * 58)

    test_tickers = ["AAPL", "MSFT", "NVDA", "RELIANCE.NS", "TCS.NS", "INFY.NS"]
    results_summary = []
    all_pass = True

    for ticker in test_tickers:
        try:
            result = assess_risk(ticker)
            _print_risk(result)

            # Validate
            _validate_result(result)
            print(f"  [VALIDATION] {ticker}: PASS")

            results_summary.append({
                "ticker": ticker,
                "risk_score": result["risk_score"],
                "risk_level": result["risk_level"],
                "vol_component": result["components"]["volatility"],
                "dd_component": result["components"]["max_drawdown"],
                "ann_vol_pct": result["raw_metrics"]["annualized_volatility"] * 100,
                "max_dd_pct": result["raw_metrics"]["max_drawdown"] * 100,
                "status": "PASS",
            })

        except Exception as exc:
            print(f"  [ERROR] {ticker}: {exc}")
            all_pass = False
            results_summary.append({
                "ticker": ticker, "status": f"ERROR: {exc}"
            })

    # Summary table
    print("\n" + "=" * 58)
    print("  SUMMARY TABLE")
    print("=" * 58)
    print(f"  {'Ticker':<16} {'Score':>6} {'Level':>8} {'AnnVol':>8} {'MaxDD':>8}")
    print(f"  {'-'*52}")
    for row in results_summary:
        if row.get("status") == "PASS":
            print(f"  {row['ticker']:<16} {row['risk_score']:>6.1f} {row['risk_level']:>8} "
                  f"{row['ann_vol_pct']:>7.1f}% {row['max_dd_pct']:>7.1f}%")
        else:
            print(f"  {row['ticker']:<16}  ERROR: {row.get('status', 'unknown')}")

    print(f"\n  All validations passed: {all_pass}")
    print("=" * 58)


# ===================================================================
# Entry point
# ===================================================================

if __name__ == "__main__":
    save_risk_metadata()

    if len(sys.argv) > 1:
        ticker_arg = sys.argv[1].strip().upper()
        print(f"Assessing risk for: {ticker_arg}")
        try:
            result = assess_risk(ticker_arg)
            _print_risk(result)
            _validate_result(result)
            print(f"  [VALIDATION] PASS")
        except Exception as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)
    else:
        run_tests()
