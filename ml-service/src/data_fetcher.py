"""
data_fetcher.py
----------------
Purpose:
- Fetches 7+ years of daily historical market data for the full US + India stock universe using `yfinance`.
- Uses explicit historical start and end dates to guarantee comprehensive time-series depth.
- Standardizes raw data format and persists individual stock CSVs to `data/raw/`.
- Verifies historical data coverage depth (>= 7 years) and reports coverage anomalies.

Configured Stock Universe:
- US Equities (15): AAPL, MSFT, NVDA, TSLA, AMZN, GOOGL, META, JPM, NFLX, V, DIS, NVAX, AMD, INTC, UBER
- Indian Equities (20): RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS, ICICIBANK.NS, SBIN.NS, BHARTIARTL.NS,
                        ITC.NS, KOTAKBANK.NS, LT.NS, HINDUNILVR.NS, WIPRO.NS, AXISBANK.NS, BAJFINANCE.NS,
                        MARUTI.NS, SUNPHARMA.NS, TITAN.NS, ASIANPAINT.NS, TATASTEEL.NS, HCLTECH.NS

Raw Output Schema:
- Date, Open, High, Low, Close, Volume, Ticker, Market

Usage:
  python src/data_fetcher.py
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
import pandas as pd
import yfinance as yf

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"

# Full configured India + US stock universe
US_TICKERS: List[str] = [
    "AAPL",
    "MSFT",
    "NVDA",
    "TSLA",
    "AMZN",
    "GOOGL",
    "META",
    "JPM",
    "NFLX",
    "V",
    "DIS",
    "NVAX",
    "AMD",
    "INTC",
    "UBER",
]

INDIA_TICKERS: List[str] = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "BHARTIARTL.NS",
    "ITC.NS",
    "KOTAKBANK.NS",
    "LT.NS",
    "HINDUNILVR.NS",
    "WIPRO.NS",
    "AXISBANK.NS",
    "BAJFINANCE.NS",
    "MARUTI.NS",
    "SUNPHARMA.NS",
    "TITAN.NS",
    "ASIANPAINT.NS",
    "TATASTEEL.NS",
    "HCLTECH.NS",
]

DEFAULT_UNIVERSE: List[str] = US_TICKERS + INDIA_TICKERS

RAW_SCHEMA: List[str] = [
    "Date",
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "Ticker",
    "Market",
]


def get_market_for_ticker(ticker: str) -> str:
    """
    Determines market exchange classification for a given ticker symbol.
    """
    upper = ticker.upper()
    if upper.endswith(".NS"):
        return "NSE"
    if upper.endswith(".BO"):
        return "BSE"
    return "US"


def get_default_date_range(years_back: float = 8.0) -> Tuple[str, str]:
    """
    Generates explicit start and end date strings to guarantee >= 7 years of history.
    Defaults to 8.0 years back to account for calendar holidays and warmup windows.
    """
    today = datetime.today()
    start_dt = today - timedelta(days=int(years_back * 365.25))
    start_date_str = start_dt.strftime("%Y-%m-%d")
    end_date_str = today.strftime("%Y-%m-%d")
    return start_date_str, end_date_str


def verify_historical_coverage(
    df: pd.DataFrame,
    ticker: str,
    min_years: float = 7.0,
) -> Tuple[bool, str]:
    """
    Verifies if the downloaded data meets the minimum historical coverage requirement (>= 7 years).

    Args:
        df: Downloaded stock DataFrame.
        ticker: Ticker symbol.
        min_years: Minimum required historical depth in years.

    Returns:
        Tuple of (is_sufficient: bool, detail_message: str)
    """
    if df.empty:
        return False, "No data available (0 rows)."

    first_date = pd.to_datetime(df["Date"].iloc[0])
    last_date = pd.to_datetime(df["Date"].iloc[-1])
    span_days = (last_date - first_date).days
    span_years = span_days / 365.25
    row_count = len(df)

    # 7 years of daily trading is typically ~1,700+ trading days (minimum acceptable ~1,600)
    min_rows = int(min_years * 240)

    if span_years < min_years or row_count < min_rows:
        return (
            False,
            f"Coverage spans only {span_years:.1f} years ({row_count} rows, {first_date.strftime('%Y-%m-%d')} to {last_date.strftime('%Y-%m-%d')}), below required {min_years:.1f} years (~{min_rows} rows).",
        )

    return (
        True,
        f"Coverage spans {span_years:.1f} years ({row_count} rows, {first_date.strftime('%Y-%m-%d')} to {last_date.strftime('%Y-%m-%d')}).",
    )


def fetch_stock_data(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Downloads historical DAILY data using explicit start and end dates via yfinance.

    Args:
        ticker: Stock ticker symbol (e.g. 'AAPL', 'RELIANCE.NS').
        start_date: Explicit start date string 'YYYY-MM-DD' (defaults to >= 8 years ago).
        end_date: Explicit end date string 'YYYY-MM-DD' (defaults to today).

    Returns:
        Standardized DataFrame with columns:
        [Date, Open, High, Low, Close, Volume, Ticker, Market]
    """
    default_start, default_end = get_default_date_range(years_back=8.0)
    if start_date is None:
        start_date = default_start
    if end_date is None:
        end_date = default_end

    ticker_obj = yf.Ticker(ticker)
    df = ticker_obj.history(
        start=start_date,
        end=end_date,
        interval="1d",
        auto_adjust=False,
    )

    if df.empty:
        raise ValueError(f"No historical data returned for '{ticker}' between {start_date} and {end_date}.")

    # Reset index to access Date
    df = df.reset_index()

    # Normalize Date column to YYYY-MM-DD string without timezone
    if "Date" in df.columns:
        date_series = pd.to_datetime(df["Date"])
        if date_series.dt.tz is not None:
            date_series = date_series.dt.tz_localize(None)
        df["Date"] = date_series.dt.strftime("%Y-%m-%d")
    elif "Datetime" in df.columns:
        date_series = pd.to_datetime(df["Datetime"])
        if date_series.dt.tz is not None:
            date_series = date_series.dt.tz_localize(None)
        df["Date"] = date_series.dt.strftime("%Y-%m-%d")
    else:
        raise KeyError(f"Date column not found in downloaded data for '{ticker}'.")

    # Ensure required OHLCV columns exist
    required_ohlcv = ["Open", "High", "Low", "Close", "Volume"]
    for col in required_ohlcv:
        if col not in df.columns:
            raise KeyError(f"Missing required column '{col}' for ticker '{ticker}'.")

    # Add metadata
    df["Ticker"] = ticker
    df["Market"] = get_market_for_ticker(ticker)

    # Filter and reorder columns
    df = df[RAW_SCHEMA].copy()

    # Convert Date to datetime for sorting and deduplication
    df["Date_dt"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date_dt", ascending=True).drop_duplicates(subset=["Date"]).reset_index(drop=True)
    df = df.drop(columns=["Date_dt"])

    # Ensure numeric columns
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop any initial rows missing core price data
    df = df.dropna(subset=["Open", "High", "Low", "Close", "Volume"]).reset_index(drop=True)

    return df


def save_raw_data(df: pd.DataFrame, ticker: str, output_dir: Optional[Path] = None) -> Path:
    """
    Saves raw stock DataFrame to CSV inside raw data directory.

    Args:
        df: OHLCV DataFrame.
        ticker: Ticker symbol.
        output_dir: Destination directory.

    Returns:
        Path to saved file.
    """
    if output_dir is None:
        output_dir = RAW_DATA_DIR

    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / f"{ticker}.csv"
    df.to_csv(file_path, index=False)
    return file_path


def fetch_and_save_universe(
    tickers: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Downloads historical data for the entire stock universe, validates coverage,
    saves individual raw CSVs, and prints the detailed per-ticker and summary reports.

    Args:
        tickers: List of tickers (defaults to DEFAULT_UNIVERSE).
        start_date: Explicit start date.
        end_date: Explicit end date.
        output_dir: Target output directory (defaults to RAW_DATA_DIR).

    Returns:
        Comprehensive dictionary of execution results.
    """
    if tickers is None:
        tickers = DEFAULT_UNIVERSE

    if output_dir is None:
        output_dir = RAW_DATA_DIR

    default_start, default_end = get_default_date_range(years_back=8.0)
    if start_date is None:
        start_date = default_start
    if end_date is None:
        end_date = default_end

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("  FinSight AI - Step 2 Correction: Historical Data Collection Pipeline")
    print("=" * 80)
    print(f"Requested Universe Size : {len(tickers)} tickers ({len([t for t in tickers if not t.endswith('.NS')])} US, {len([t for t in tickers if t.endswith('.NS')])} India)")
    print(f"Explicit Date Range     : {start_date} to {end_date} (Target: >= 7.0 Years)")
    print(f"Raw Output Directory    : {output_dir}")
    print("=" * 80)
    print(f"{'Ticker':<16} | {'Market':<6} | {'First Date':<12} | {'Last Date':<12} | {'Rows':<6} | {'Status'}")
    print("-" * 80)

    successful_tickers: List[Dict[str, Any]] = []
    failed_tickers: List[Dict[str, Any]] = []
    insufficient_coverage_tickers: List[Dict[str, Any]] = []
    total_raw_rows = 0

    for ticker in tickers:
        market = get_market_for_ticker(ticker)
        try:
            df = fetch_stock_data(ticker=ticker, start_date=start_date, end_date=end_date)
            saved_path = save_raw_data(df=df, ticker=ticker, output_dir=output_dir)

            first_date = df["Date"].iloc[0]
            last_date = df["Date"].iloc[-1]
            rows = len(df)
            total_raw_rows += rows

            is_sufficient, coverage_msg = verify_historical_coverage(df=df, ticker=ticker, min_years=7.0)

            status_str = "OK (>=7y)" if is_sufficient else "COVERAGE SHORT"

            print(f"{ticker:<16} | {market:<6} | {first_date:<12} | {last_date:<12} | {rows:<6} | {status_str}")

            record = {
                "ticker": ticker,
                "market": market,
                "first_date": first_date,
                "last_date": last_date,
                "rows": rows,
                "file_path": str(saved_path),
                "is_sufficient": is_sufficient,
                "coverage_msg": coverage_msg,
            }

            successful_tickers.append(record)

            if not is_sufficient:
                insufficient_coverage_tickers.append(record)

        except Exception as e:
            print(f"{ticker:<16} | {market:<6} | {'N/A':<12} | {'N/A':<12} | {'0':<6} | FAILED: {e}", file=sys.stderr)
            failed_tickers.append({"ticker": ticker, "market": market, "error": str(e)})

    # Final Summary Report
    print("\n" + "=" * 80)
    print("  Historical Data Collection Summary")
    print("=" * 80)
    print(f"Total tickers requested                  : {len(tickers)}")
    print(f"Successful tickers                       : {len(successful_tickers)}")
    print(f"Failed tickers                           : {len(failed_tickers)}")
    print(f"Tickers with insufficient coverage (<7y) : {len(insufficient_coverage_tickers)}")
    print(f"Total raw rows                           : {total_raw_rows:,}")
    print("=" * 80)

    if insufficient_coverage_tickers:
        print("\n[DATA COVERAGE NOTICES]")
        for item in insufficient_coverage_tickers:
            print(f"  - {item['ticker']} ({item['market']}): {item['coverage_msg']}")

    if failed_tickers:
        print("\n[FAILED TICKERS]")
        for item in failed_tickers:
            print(f"  - {item['ticker']} ({item['market']}): {item['error']}")

    return {
        "total_requested": len(tickers),
        "successful_count": len(successful_tickers),
        "failed_count": len(failed_tickers),
        "insufficient_coverage_count": len(insufficient_coverage_tickers),
        "total_raw_rows": total_raw_rows,
        "successful_tickers": successful_tickers,
        "failed_tickers": failed_tickers,
        "insufficient_coverage_tickers": insufficient_coverage_tickers,
    }


if __name__ == "__main__":
    fetch_and_save_universe()
