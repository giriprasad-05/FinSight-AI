"""
main.py
--------
FastAPI HTTP wrapper for the FinSight AI ML microservice.

Exposes the prediction and risk engines via clean REST endpoints.
Does NOT contain any ML logic - delegates entirely to:
  src/predict.py  -> predict_stock()
  src/risk.py     -> assess_risk()

Endpoints:
  GET /health
  GET /predict/{ticker}
  GET /risk/{ticker}
  GET /analysis/{ticker}
  GET /quote/{ticker}              <- real yfinance quote + company info
  GET /quote/{ticker}/history      <- real historical OHLCV data
  GET /search/{query}             <- search supported stock universe

Usage:
  cd ml-service
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import sys
import time
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, List

from fastapi import FastAPI, HTTPException, Path as FPath, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure src/ is on the path so predict.py / risk.py can be imported
SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

from predict import predict_stock, _load_model_once      # noqa: E402
from risk import assess_risk                                # noqa: E402
from ai_explainer import generate_explanation, build_compact_analysis  # noqa: E402

# ===================================================================
# Logging
# ===================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("finsight-ml")

# ===================================================================
# Supported stock universe
# ===================================================================
US_TICKERS: List[str] = [
    "AAPL", "AMD", "AMZN", "DIS", "GOOGL",
    "INTC", "JPM", "META", "MSFT", "NFLX",
    "NVAX", "NVDA", "TSLA", "UBER", "V",
]

INDIA_TICKERS: List[str] = [
    "ASIANPAINT.NS", "AXISBANK.NS", "BAJFINANCE.NS", "BHARTIARTL.NS",
    "HCLTECH.NS", "HDFCBANK.NS", "HINDUNILVR.NS", "ICICIBANK.NS",
    "INFY.NS", "ITC.NS", "KOTAKBANK.NS", "LT.NS", "MARUTI.NS",
    "RELIANCE.NS", "SBIN.NS", "SUNPHARMA.NS", "TATASTEEL.NS",
    "TCS.NS", "TITAN.NS", "WIPRO.NS",
]

SUPPORTED_UNIVERSE: List[str] = US_TICKERS + INDIA_TICKERS

# Alias map: bare Indian names -> canonical .NS ticker
INDIA_ALIASES: Dict[str, str] = {
    t.replace(".NS", ""): t for t in INDIA_TICKERS
}

# ===================================================================
# App
# ===================================================================
app = FastAPI(
    title="FinSight AI -- ML Microservice",
    description=(
        "XGBoost v2 stock trend prediction and quantitative risk assessment. "
        "This service is called exclusively by the Node.js backend."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ===================================================================
# CORS
# ===================================================================
_allowed_origins = os.getenv(
    "ML_CORS_ORIGINS",
    "http://localhost:5000,http://127.0.0.1:5000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ===================================================================
# Request timing middleware
# ===================================================================
@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
    response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({elapsed_ms}ms)")
    return response

# ===================================================================
# Ticker validation
# ===================================================================
_TICKER_RE = re.compile(r"^[A-Za-z0-9.\-]{1,20}$")

def _validate_ticker(ticker: str) -> str:
    """Normalise and validate a ticker symbol. Raises HTTPException on bad input."""
    t = ticker.strip().upper()
    if not t:
        raise HTTPException(status_code=400, detail="Ticker symbol is required.")
    if not _TICKER_RE.match(t):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid ticker format: '{t}'. Only letters, digits, dots, and hyphens allowed (max 20 chars).",
        )
    return t

def _resolve_ticker(ticker: str) -> str:
    """Resolve bare Indian aliases to canonical .NS form."""
    t = ticker.strip().upper()
    # Already has suffix — use as-is
    if "." in t:
        return t
    # Check alias map
    return INDIA_ALIASES.get(t, t)

# ===================================================================
# yfinance helper — safe scalar extraction
# ===================================================================
def _safe_get(info: dict, *keys, default=None):
    """Return the first non-None, non-zero-string value found in info for any of the given keys."""
    for key in keys:
        val = info.get(key)
        if val is not None and val != "N/A" and val != "":
            return val
    return default

def _safe_float(info: dict, *keys) -> Optional[float]:
    """Extract a float, returning None if missing or invalid."""
    raw = _safe_get(info, *keys)
    if raw is None:
        return None
    try:
        f = float(raw)
        return f if f == f else None  # NaN guard
    except (TypeError, ValueError):
        return None

def _safe_int(info: dict, *keys) -> Optional[int]:
    """Extract an int, returning None if missing or invalid."""
    raw = _safe_get(info, *keys)
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None

def _safe_str(info: dict, *keys) -> Optional[str]:
    """Extract a non-empty string, returning None if missing."""
    raw = _safe_get(info, *keys)
    if raw is None:
        return None
    s = str(raw).strip()
    return s if s else None

# ===================================================================
# Endpoints — existing (unchanged)
# ===================================================================

@app.get("/health", tags=["System"])
async def health() -> Dict[str, Any]:
    """Health check -- confirms the ML service is running."""
    import xgboost as xgb
    import numpy as np
    import pandas as pd
    return {
        "status": "ok",
        "service": "FinSight AI ML Service",
        "version": "2.0.0",
        "model": "xgboost_trend_model_v2.json",
        "xgboost_version": xgb.__version__,
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
    }


@app.get("/predict/{ticker}", tags=["Prediction"])
async def predict(
    ticker: str = FPath(..., description="Stock ticker symbol (e.g. AAPL, RELIANCE.NS)")
) -> Dict[str, Any]:
    """
    Run the v2 XGBoost trend prediction for a ticker.

    Returns:
      - prediction: DOWN | FLAT | UP
      - confidence: max class probability
      - probabilities: per-class probabilities
      - indicators: technical indicator values used by the model
      - data_date: date of the latest trading day used
    """
    t = _validate_ticker(ticker)
    try:
        result = predict_stock(t)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception(f"Unexpected error in /predict/{t}")
        raise HTTPException(status_code=500, detail="Internal prediction error.")


@app.get("/risk/{ticker}", tags=["Risk"])
async def risk(
    ticker: str = FPath(..., description="Stock ticker symbol (e.g. AAPL, RELIANCE.NS)")
) -> Dict[str, Any]:
    """
    Run the quantitative risk assessment for a ticker.

    Returns:
      - risk_score: 0-100
      - risk_level: LOW | MEDIUM | HIGH
      - components: per-component 0-100 scores
      - raw_metrics: annualized volatility, max drawdown, etc.
      - explanations: human-readable risk drivers
    """
    t = _validate_ticker(ticker)
    try:
        result = assess_risk(t)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception(f"Unexpected error in /risk/{t}")
        raise HTTPException(status_code=500, detail="Internal risk assessment error.")


@app.get("/analysis/{ticker}", tags=["Analysis"])
async def analysis(
    ticker: str = FPath(..., description="Stock ticker symbol (e.g. AAPL, RELIANCE.NS)")
) -> Dict[str, Any]:
    """
    Combined trend prediction + risk assessment in one call.

    Runs both engines concurrently and returns a unified response.
    """
    import asyncio

    t = _validate_ticker(ticker)

    loop = asyncio.get_event_loop()

    def _run_predict():
        return predict_stock(t)

    def _run_risk():
        return assess_risk(t)

    try:
        pred_fut = loop.run_in_executor(None, _run_predict)
        risk_fut = loop.run_in_executor(None, _run_risk)
        prediction, risk_result = await asyncio.gather(pred_fut, risk_fut)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception(f"Unexpected error in /analysis/{t}")
        raise HTTPException(status_code=500, detail="Internal analysis error.")

    feat_imps = _get_model_feature_importances()
    explanation_result = generate_explanation(prediction, risk_result, feat_imps, polish_llm=False)

    combined = {
        "ticker": t,
        "market": prediction.get("market", "US"),
        "data_date": prediction.get("data_date"),
        "trend": {
            "prediction": prediction["prediction"],
            "prediction_code": prediction["prediction_code"],
            "confidence": prediction["confidence"],
            "probabilities": prediction["probabilities"],
            "model_version": prediction.get("model_version", "v2"),
        },
        "risk": {
            "risk_score": risk_result["risk_score"],
            "risk_level": risk_result["risk_level"],
            "components": risk_result["components"],
            "raw_metrics": risk_result["raw_metrics"],
            "explanations": risk_result["explanations"],
        },
        "indicators": prediction.get("indicators", {}),
        "explanation": explanation_result,
    }
    return combined


# Cache for model feature importances
_feature_importances_cache: Optional[Dict[str, float]] = None


def _get_model_feature_importances() -> Dict[str, float]:
    global _feature_importances_cache
    if _feature_importances_cache is not None:
        return _feature_importances_cache
    try:
        model, _, features = _load_model_once()
        booster = model.get_booster()
        scores = booster.get_score(importance_type="gain")
        total = sum(scores.values()) or 1.0
        _feature_importances_cache = {f: float(scores.get(f, 0.0)) / total for f in features}
        return _feature_importances_cache
    except Exception as exc:
        logger.warning(f"Could not compute feature importances: {exc}")
        return {}


# ===================================================================
# /explain/{ticker} - AI Explanation Engine Endpoint
# ===================================================================

@app.get("/explain/{ticker}", tags=["Explanation"])
async def explain(
    ticker: str = FPath(..., description="Stock ticker symbol (e.g. AAPL, RELIANCE.NS)")
) -> Dict[str, Any]:
    """
    AI Explanation Engine endpoint.
    Converts structured XGBoost model predictions and quantitative risk assessment
    into clear human-readable explanations, key drivers, risk breakdown, and watch items.
    Reuses the existing prediction and risk assessment pipeline.
    """
    import asyncio

    t = _validate_ticker(ticker)

    loop = asyncio.get_event_loop()

    def _run_predict():
        return predict_stock(t)

    def _run_risk():
        return assess_risk(t)

    try:
        pred_fut = loop.run_in_executor(None, _run_predict)
        risk_fut = loop.run_in_executor(None, _run_risk)
        prediction, risk_result = await asyncio.gather(pred_fut, risk_fut)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception(f"Unexpected error in /explain/{t}")
        raise HTTPException(status_code=500, detail="Internal explanation error.")

    feat_imps = _get_model_feature_importances()
    return generate_explanation(prediction, risk_result, feat_imps)


# ===================================================================
# ===================================================================
# In-memory quote and history caches (60s TTL)
# ===================================================================
_quote_cache: Dict[str, Any] = {}
_history_cache: Dict[str, Any] = {}


# ===================================================================
# NEW: /quote/{ticker}
# ===================================================================

@app.get("/quote/{ticker}", tags=["Quote"])
async def get_quote(
    ticker: str = FPath(..., description="Stock ticker symbol (e.g. AAPL, RELIANCE.NS)")
) -> Dict[str, Any]:
    """
    Latest available stock quote + company info via yfinance.

    Note: yfinance provides DELAYED quotes for most sources (not real-time).
    The quote_timestamp reflects the data timestamp from the source.
    Includes in-memory 60s TTL caching and robust metadata fallback.
    """
    import asyncio
    import yfinance as yf

    t = _validate_ticker(ticker)
    # Resolve bare Indian aliases (RELIANCE -> RELIANCE.NS)
    t = _resolve_ticker(t)

    now = time.time()
    if t in _quote_cache:
        cached_ts, cached_data = _quote_cache[t]
        if now - cached_ts < 60:
            return cached_data

    def _fetch_quote():
        ticker_obj = yf.Ticker(t)

        # Static metadata lookup for instant fallback
        meta_match = next((s for s in SUPPORTED_STOCKS_METADATA if s["ticker"] == t or s["ticker"].replace(".NS", "") == t), None)

        # --- Fast path: use .fast_info (lightweight, no crumb needed) ---
        try:
            fi = ticker_obj.fast_info
        except Exception:
            fi = None

        # --- Full info (may be slow / rate-limited) ---
        try:
            info = ticker_obj.info or {}
        except Exception:
            info = {}

        # Determine market
        market = "IN" if t.endswith(".NS") or t.endswith(".BO") else "US"
        currency = _safe_str(info, "currency") or (meta_match.get("currency") if meta_match else None) or ("INR" if market == "IN" else "USD")
        exchange = _safe_str(info, "exchange", "fullExchangeName") or (meta_match.get("exchange") if meta_match else None)

        # ── Price fields ─────────────────────────────────────────────
        # Prefer fast_info when available, fall back to info dict
        price = None
        if fi is not None:
            try:
                price = float(fi.last_price) if fi.last_price is not None else None
            except Exception:
                price = None
        if price is None:
            price = _safe_float(info, "currentPrice", "regularMarketPrice",
                                "postMarketPrice", "ask", "bid")

        previous_close = None
        if fi is not None:
            try:
                previous_close = float(fi.previous_close) if fi.previous_close is not None else None
            except Exception:
                previous_close = None
        if previous_close is None:
            previous_close = _safe_float(info, "previousClose", "regularMarketPreviousClose")

        # Historical fallback if fast_info and info both failed to provide price
        if price is None:
            try:
                h = ticker_obj.history(period="5d")
                if not h.empty:
                    price = float(h["Close"].iloc[-1])
                    if previous_close is None and len(h) > 1:
                        previous_close = float(h["Close"].iloc[-2])
            except Exception:
                pass

        change = None
        change_percent = None
        if price is not None and previous_close is not None and previous_close != 0:
            change = round(price - previous_close, 4)
            change_percent = round((change / previous_close) * 100, 4)
        else:
            change = _safe_float(info, "regularMarketChange")
            change_percent = _safe_float(info, "regularMarketChangePercent")

        # ── Volume / market cap ──────────────────────────────────────
        volume = _safe_int(info, "regularMarketVolume", "volume")
        if volume is None and fi is not None:
            try:
                volume = int(fi.three_month_average_volume) if fi.three_month_average_volume else None
            except Exception:
                volume = None

        average_volume = _safe_int(info, "averageVolume", "averageDailyVolume3Month")
        market_cap = _safe_float(info, "marketCap")

        # ── 52-week range ────────────────────────────────────────────
        year_high = None
        year_low = None
        if fi is not None:
            try:
                year_high = float(fi.year_high) if fi.year_high is not None else None
                year_low = float(fi.year_low) if fi.year_low is not None else None
            except Exception:
                pass
        if year_high is None:
            year_high = _safe_float(info, "fiftyTwoWeekHigh")
        if year_low is None:
            year_low = _safe_float(info, "fiftyTwoWeekLow")

        # ── Valuation ────────────────────────────────────────────────
        trailing_pe = _safe_float(info, "trailingPE")
        trailing_eps = _safe_float(info, "trailingEps")
        dividend_yield = _safe_float(info, "dividendYield")
        beta = _safe_float(info, "beta")

        # ── Company info ─────────────────────────────────────────────
        long_name = _safe_str(info, "longName", "shortName") or (meta_match.get("company_name") if meta_match else None)
        short_name = _safe_str(info, "shortName", "longName") or (meta_match.get("company_name") if meta_match else None)
        sector = _safe_str(info, "sector") or (meta_match.get("sector") if meta_match else None)
        industry = _safe_str(info, "industry") or (meta_match.get("industry") if meta_match else None)
        description = _safe_str(info, "longBusinessSummary")
        website = _safe_str(info, "website")
        employees = _safe_int(info, "fullTimeEmployees")
        country = _safe_str(info, "country") or (meta_match.get("country") if meta_match else None)
        city = _safe_str(info, "city")

        # ── Quote timestamp ──────────────────────────────────────────
        quote_timestamp = None
        raw_ts = info.get("regularMarketTime")
        if raw_ts is not None:
            try:
                import datetime
                dt = datetime.datetime.fromtimestamp(int(raw_ts), tz=datetime.timezone.utc)
                quote_timestamp = dt.isoformat()
            except Exception:
                quote_timestamp = None

        return {
            "ticker": t,
            "short_name": short_name,
            "long_name": long_name,
            "market": market,
            "currency": currency,
            "exchange": exchange,
            "price": price,
            "previous_close": previous_close,
            "change": change,
            "change_percent": change_percent,
            "market_cap": market_cap,
            "volume": volume,
            "average_volume": average_volume,
            "fifty_two_week_high": year_high,
            "fifty_two_week_low": year_low,
            "trailing_pe": trailing_pe,
            "trailing_eps": trailing_eps,
            "dividend_yield": dividend_yield,
            "beta": beta,
            "sector": sector,
            "industry": industry,
            "description": description,
            "website": website,
            "employees": employees,
            "country": country,
            "city": city,
            "quote_timestamp": quote_timestamp,
            "data_source": "yfinance (delayed)",
        }

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _fetch_quote)

        if result["price"] is None:
            raise HTTPException(
                status_code=404,
                detail=f"No quote data found for '{t}'. The ticker may be invalid or delisted."
            )

        _quote_cache[t] = (now, result)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Unexpected error in /quote/{t}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch quote for '{t}'.")


# ===================================================================
# NEW: /quote/{ticker}/history
# ===================================================================

@app.get("/quote/{ticker}/history", tags=["Quote"])
async def get_history(
    ticker: str = FPath(..., description="Stock ticker symbol"),
    range: str = Query("1Y", alias="range", description="Time range: 1W|1M|3M|6M|1Y|5Y"),
) -> List[Dict[str, Any]]:
    """
    Real historical closing price data for charting via yfinance.

    Returns a list of {date, open, high, low, close, volume} objects.
    The 'range' query parameter maps to standard historical periods.
    Includes in-memory 60s TTL caching.
    """
    import asyncio
    import yfinance as yf
    import pandas as pd

    t = _validate_ticker(ticker)
    t = _resolve_ticker(t)

    # Map range to yfinance period
    # Use 'time_range' locally to avoid shadowing Python builtin range()
    time_range = range
    PERIOD_MAP = {
        "1W": "5d",
        "1M": "1mo",
        "3M": "3mo",
        "6M": "6mo",
        "1Y": "1y",
        "5Y": "5y",
    }
    period = PERIOD_MAP.get(time_range.upper(), "1y")

    cache_key = f"{t}_{time_range.upper()}"
    now = time.time()
    if cache_key in _history_cache:
        cached_ts, cached_data = _history_cache[cache_key]
        if now - cached_ts < 60:
            return cached_data

    def _fetch_history():
        ticker_obj = yf.Ticker(t)
        df = ticker_obj.history(period=period, interval="1d", auto_adjust=True)

        if df.empty:
            return []

        df = df.reset_index()

        # Normalize Date column (handle both Date and Datetime columns)
        if "Date" in df.columns:
            date_col = pd.to_datetime(df["Date"])
        elif "Datetime" in df.columns:
            date_col = pd.to_datetime(df["Datetime"])
        else:
            return []

        # Remove timezone info for consistent string formatting
        if date_col.dt.tz is not None:
            date_col = date_col.dt.tz_localize(None)

        # Add normalized date strings to the DataFrame so iterrows can access them
        df = df.copy()
        df["_date_str"] = [d.strftime("%Y-%m-%d") for d in date_col]

        result = []
        for _, row in df.iterrows():
            date_str = row["_date_str"]

            close_val = row.get("Close") if "Close" in df.columns else None
            if close_val is None or (close_val != close_val):  # NaN check
                continue

            def _safe_num(col_name, as_int=False):
                if col_name not in df.columns:
                    return None
                v = row[col_name]
                if v != v or v is None:  # NaN
                    return None
                try:
                    return int(v) if as_int else round(float(v), 4)
                except (TypeError, ValueError):
                    return None

            record = {
                "date": date_str,
                "open": _safe_num("Open"),
                "high": _safe_num("High"),
                "low": _safe_num("Low"),
                "close": round(float(close_val), 4),
                "volume": _safe_num("Volume", as_int=True),
            }
            result.append(record)

        return result

    loop = asyncio.get_event_loop()
    try:
        data = await loop.run_in_executor(None, _fetch_history)
        _history_cache[cache_key] = (now, data)
        return data
    except Exception as exc:
        logger.exception(f"Unexpected error in /quote/{t}/history")
        raise HTTPException(status_code=500, detail=f"Failed to fetch history for '{t}'.")


# ===================================================================
# Supported stock universe metadata
# ===================================================================
SUPPORTED_STOCKS_METADATA: List[Dict[str, Any]] = [
    # --- US Stocks (15) ---
    {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "market": "US",
        "currency": "USD",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "country": "United States",
        "aliases": ["APPLE", "AAPL"],
    },
    {
        "ticker": "AMD",
        "company_name": "Advanced Micro Devices, Inc.",
        "market": "US",
        "currency": "USD",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Semiconductors",
        "country": "United States",
        "aliases": ["ADVANCED MICRO DEVICES", "AMD"],
    },
    {
        "ticker": "AMZN",
        "company_name": "Amazon.com, Inc.",
        "market": "US",
        "currency": "USD",
        "exchange": "NASDAQ",
        "sector": "Consumer Cyclical",
        "industry": "Internet Retail",
        "country": "United States",
        "aliases": ["AMAZON", "AMZN"],
    },
    {
        "ticker": "DIS",
        "company_name": "The Walt Disney Company",
        "market": "US",
        "currency": "USD",
        "exchange": "NYSE",
        "sector": "Communication Services",
        "industry": "Entertainment",
        "country": "United States",
        "aliases": ["DISNEY", "WALT DISNEY", "DIS"],
    },
    {
        "ticker": "GOOGL",
        "company_name": "Alphabet Inc.",
        "market": "US",
        "currency": "USD",
        "exchange": "NASDAQ",
        "sector": "Communication Services",
        "industry": "Internet Content & Information",
        "country": "United States",
        "aliases": ["GOOGLE", "ALPHABET", "GOOGL", "GOOG"],
    },
    {
        "ticker": "INTC",
        "company_name": "Intel Corporation",
        "market": "US",
        "currency": "USD",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Semiconductors",
        "country": "United States",
        "aliases": ["INTEL", "INTC"],
    },
    {
        "ticker": "JPM",
        "company_name": "JPMorgan Chase & Co.",
        "market": "US",
        "currency": "USD",
        "exchange": "NYSE",
        "sector": "Financial Services",
        "industry": "Banks - Diversified",
        "country": "United States",
        "aliases": ["JPMORGAN", "JP MORGAN", "CHASE", "JPM"],
    },
    {
        "ticker": "META",
        "company_name": "Meta Platforms, Inc.",
        "market": "US",
        "currency": "USD",
        "exchange": "NASDAQ",
        "sector": "Communication Services",
        "industry": "Internet Content & Information",
        "country": "United States",
        "aliases": ["FACEBOOK", "META"],
    },
    {
        "ticker": "MSFT",
        "company_name": "Microsoft Corporation",
        "market": "US",
        "currency": "USD",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Software - Infrastructure",
        "country": "United States",
        "aliases": ["MICROSOFT", "MSFT"],
    },
    {
        "ticker": "NFLX",
        "company_name": "Netflix, Inc.",
        "market": "US",
        "currency": "USD",
        "exchange": "NASDAQ",
        "sector": "Communication Services",
        "industry": "Entertainment",
        "country": "United States",
        "aliases": ["NETFLIX", "NFLX"],
    },
    {
        "ticker": "NVAX",
        "company_name": "Novavax, Inc.",
        "market": "US",
        "currency": "USD",
        "exchange": "NASDAQ",
        "sector": "Healthcare",
        "industry": "Biotechnology",
        "country": "United States",
        "aliases": ["NOVAVAX", "NVAX"],
    },
    {
        "ticker": "NVDA",
        "company_name": "NVIDIA Corporation",
        "market": "US",
        "currency": "USD",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Semiconductors",
        "country": "United States",
        "aliases": ["NVIDIA", "NVDA"],
    },
    {
        "ticker": "TSLA",
        "company_name": "Tesla, Inc.",
        "market": "US",
        "currency": "USD",
        "exchange": "NASDAQ",
        "sector": "Consumer Cyclical",
        "industry": "Auto Manufacturers",
        "country": "United States",
        "aliases": ["TESLA", "TSLA"],
    },
    {
        "ticker": "UBER",
        "company_name": "Uber Technologies, Inc.",
        "market": "US",
        "currency": "USD",
        "exchange": "NYSE",
        "sector": "Technology",
        "industry": "Software - Application",
        "country": "United States",
        "aliases": ["UBER"],
    },
    {
        "ticker": "V",
        "company_name": "Visa Inc.",
        "market": "US",
        "currency": "USD",
        "exchange": "NYSE",
        "sector": "Financial Services",
        "industry": "Credit Services",
        "country": "United States",
        "aliases": ["VISA", "V"],
    },

    # --- India / NSE Stocks (20) ---
    {
        "ticker": "ASIANPAINT.NS",
        "company_name": "Asian Paints Limited",
        "market": "IN",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Consumer Cyclical",
        "industry": "Specialty Chemicals",
        "country": "India",
        "aliases": ["ASIANPAINT", "ASIAN PAINTS", "ASIANPAINT.NS"],
    },
    {
        "ticker": "AXISBANK.NS",
        "company_name": "Axis Bank Limited",
        "market": "IN",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Financial Services",
        "industry": "Banks - Regional",
        "country": "India",
        "aliases": ["AXISBANK", "AXIS", "AXIS BANK", "AXISBANK.NS"],
    },
    {
        "ticker": "BAJFINANCE.NS",
        "company_name": "Bajaj Finance Limited",
        "market": "IN",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Financial Services",
        "industry": "Credit Services",
        "country": "India",
        "aliases": ["BAJFINANCE", "BAJAJ FINANCE", "BAJAJ", "BAJFINANCE.NS"],
    },
    {
        "ticker": "BHARTIARTL.NS",
        "company_name": "Bharti Airtel Limited",
        "market": "IN",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Communication Services",
        "industry": "Telecom Services",
        "country": "India",
        "aliases": ["BHARTIARTL", "AIRTEL", "BHARTI", "BHARTI AIRTEL", "BHARTIARTL.NS"],
    },
    {
        "ticker": "HCLTECH.NS",
        "company_name": "HCL Technologies Limited",
        "market": "IN",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Technology",
        "industry": "Information Technology Services",
        "country": "India",
        "aliases": ["HCLTECH", "HCL", "HCL TECH", "HCLTECH.NS"],
    },
    {
        "ticker": "HDFCBANK.NS",
        "company_name": "HDFC Bank Limited",
        "market": "IN",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Financial Services",
        "industry": "Banks - Regional",
        "country": "India",
        "aliases": ["HDFCBANK", "HDFC", "HDFC BANK", "HDFCBANK.NS"],
    },
    {
        "ticker": "HINDUNILVR.NS",
        "company_name": "Hindustan Unilever Limited",
        "market": "IN",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Consumer Defensive",
        "industry": "Household & Personal Products",
        "country": "India",
        "aliases": ["HINDUNILVR", "HUL", "HINDUSTAN UNILEVER", "UNILEVER", "HINDUNILVR.NS"],
    },
    {
        "ticker": "ICICIBANK.NS",
        "company_name": "ICICI Bank Limited",
        "market": "IN",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Financial Services",
        "industry": "Banks - Regional",
        "country": "India",
        "aliases": ["ICICIBANK", "ICICI", "ICICI BANK", "ICICIBANK.NS"],
    },
    {
        "ticker": "INFY.NS",
        "company_name": "Infosys Limited",
        "market": "IN",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Technology",
        "industry": "Information Technology Services",
        "country": "India",
        "aliases": ["INFY", "INFOSYS", "INFY.NS"],
    },
    {
        "ticker": "ITC.NS",
        "company_name": "ITC Limited",
        "market": "IN",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Consumer Defensive",
        "industry": "Tobacco",
        "country": "India",
        "aliases": ["ITC", "ITC.NS"],
    },
    {
        "ticker": "KOTAKBANK.NS",
        "company_name": "Kotak Mahindra Bank Limited",
        "market": "IN",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Financial Services",
        "industry": "Banks - Regional",
        "country": "India",
        "aliases": ["KOTAKBANK", "KOTAK", "KOTAK BANK", "KOTAK MAHINDRA", "KOTAKBANK.NS"],
    },
    {
        "ticker": "LT.NS",
        "company_name": "Larsen & Toubro Limited",
        "market": "IN",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Industrials",
        "industry": "Engineering & Construction",
        "country": "India",
        "aliases": ["LT", "L&T", "LARSEN", "LARSEN & TOUBRO", "LARSEN AND TOUBRO", "LT.NS"],
    },
    {
        "ticker": "MARUTI.NS",
        "company_name": "Maruti Suzuki India Limited",
        "market": "IN",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Consumer Cyclical",
        "industry": "Auto Manufacturers",
        "country": "India",
        "aliases": ["MARUTI", "MARUTI SUZUKI", "SUZUKI", "MARUTI.NS"],
    },
    {
        "ticker": "RELIANCE.NS",
        "company_name": "Reliance Industries Limited",
        "market": "IN",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Energy",
        "industry": "Oil & Gas Refining & Marketing",
        "country": "India",
        "aliases": ["RELIANCE", "RIL", "RELIANCE INDUSTRIES", "RELIANCE.NS"],
    },
    {
        "ticker": "SBIN.NS",
        "company_name": "State Bank of India",
        "market": "IN",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Financial Services",
        "industry": "Banks - Regional",
        "country": "India",
        "aliases": ["SBIN", "SBI", "STATE BANK", "STATE BANK OF INDIA", "SBIN.NS"],
    },
    {
        "ticker": "SUNPHARMA.NS",
        "company_name": "Sun Pharmaceutical Industries Limited",
        "market": "IN",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Healthcare",
        "industry": "Drug Manufacturers",
        "country": "India",
        "aliases": ["SUNPHARMA", "SUN PHARMA", "SUN PHARMACEUTICAL", "SUNPHARMA.NS"],
    },
    {
        "ticker": "TATASTEEL.NS",
        "company_name": "Tata Steel Limited",
        "market": "IN",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Basic Materials",
        "industry": "Steel",
        "country": "India",
        "aliases": ["TATASTEEL", "TATA STEEL", "TATASTEEL.NS"],
    },
    {
        "ticker": "TCS.NS",
        "company_name": "Tata Consultancy Services Limited",
        "market": "IN",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Technology",
        "industry": "Information Technology Services",
        "country": "India",
        "aliases": ["TCS", "TATA CONSULTANCY", "TATA CONSULTANCY SERVICES", "TCS.NS"],
    },
    {
        "ticker": "TITAN.NS",
        "company_name": "Titan Company Limited",
        "market": "IN",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Consumer Cyclical",
        "industry": "Luxury Goods",
        "country": "India",
        "aliases": ["TITAN", "TITAN COMPANY", "TITAN.NS"],
    },
    {
        "ticker": "WIPRO.NS",
        "company_name": "Wipro Limited",
        "market": "IN",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Technology",
        "industry": "Information Technology Services",
        "country": "India",
        "aliases": ["WIPRO", "WIPRO.NS"],
    },
]


# ===================================================================
# /search endpoint
# ===================================================================

@app.get("/search", tags=["Search"])
@app.get("/search/", tags=["Search"])
@app.get("/search/{query}", tags=["Search"])
async def search_stocks(
    query: Optional[str] = None,
    q: Optional[str] = Query(None, description="Search query parameter")
) -> List[Dict[str, Any]]:
    """
    Search the supported stock universe for matching tickers, company names, or aliases.
    When query is empty, returns all 35 supported stocks.
    """
    raw_query = query if query is not None else (q or "")
    clean_q = raw_query.strip().upper()

    # Empty query: return all 35 supported stocks
    if not clean_q:
        return [
            {
                "ticker": s["ticker"],
                "company_name": s["company_name"],
                "market": s["market"],
                "currency": s["currency"],
                "exchange": s["exchange"],
                "sector": s.get("sector", ""),
                "industry": s.get("industry", ""),
                "country": s.get("country", "United States" if s["market"] == "US" else "India"),
            }
            for s in SUPPORTED_STOCKS_METADATA
        ]

    if len(clean_q) > 30:
        raise HTTPException(status_code=400, detail="Query must be 1-30 characters.")

    # Match against tickers, aliases, and company names with relevance scoring
    scored: List[tuple] = []
    for s in SUPPORTED_STOCKS_METADATA:
        ticker = s["ticker"].upper()
        name = s["company_name"].upper()
        aliases = [a.upper() for a in s.get("aliases", [])]
        bare_ticker = ticker.replace(".NS", "")

        score = 0
        if ticker == clean_q or bare_ticker == clean_q:
            score = 100
        elif any(a == clean_q for a in aliases):
            score = 90
        elif ticker.startswith(clean_q) or bare_ticker.startswith(clean_q):
            score = 80
        elif any(a.startswith(clean_q) for a in aliases):
            score = 70
        elif clean_q in name:
            score = 60
        elif any(clean_q in a for a in aliases):
            score = 50
        elif clean_q in ticker:
            score = 40

        if score > 0:
            scored.append((score, s))

    # Sort descending by match relevance
    scored.sort(key=lambda x: -x[0])

    return [
        {
            "ticker": s["ticker"],
            "company_name": s["company_name"],
            "market": s["market"],
            "currency": s["currency"],
            "exchange": s["exchange"],
            "sector": s.get("sector", ""),
            "industry": s.get("industry", ""),
            "country": s.get("country", "United States" if s["market"] == "US" else "India"),
        }
        for _, s in scored
    ]


# ===================================================================
# Global exception handler
# ===================================================================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error.", "path": str(request.url.path)},
    )


# ===================================================================
# Entry point (direct run)
# ===================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
