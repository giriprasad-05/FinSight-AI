"""
ai_explainer.py
---------------
AI Explanation Engine for FinSight AI.

Converts structured XGBoost model predictions and quantitative risk assessment
outputs into clear, transparent, human-readable explanations.

Financial Safety:
- Explains model outputs rather than giving financial or trading advice.
- No buy/sell recommendations or guaranteed return claims.
- Purely deterministic rule-based generation with optional LLM polish hook.
"""

from typing import Any, Dict, List, Optional
import numpy as np


FEATURE_DISPLAY_NAMES: Dict[str, str] = {
    "Volatility_20": "20-Day Volatility",
    "High_Low_Pct": "Intraday Price Range",
    "Close": "Closing Price",
    "MA_5": "5-Day Moving Average",
    "MA_50": "50-Day Moving Average",
    "Low": "Intraday Low",
    "High": "Intraday High",
    "Open": "Opening Price",
    "Volume": "Trading Volume",
    "Daily_Return": "Daily Return",
    "RSI_14": "Relative Strength Index (RSI-14)",
    "Price_Change_Pct": "Price Change %",
    "MACD": "MACD Line",
    "MACD_Signal": "MACD Signal Line",
    "Volume_Change": "Volume Change Ratio",
}


def build_compact_analysis(
    prediction: Dict[str, Any],
    risk_result: Dict[str, Any],
    feature_importances: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Builds a compact structured analysis dictionary containing only the
    fields required for explanation. Does not include large OHLCV series.
    """
    indicators = prediction.get("indicators", {})
    raw_metrics = risk_result.get("raw_metrics", {})
    components = risk_result.get("components", {})

    compact = {
        "ticker": prediction.get("ticker", "UNKNOWN"),
        "market": prediction.get("market", "US"),
        "data_date": prediction.get("data_date"),
        "prediction": prediction.get("prediction", "FLAT"),
        "confidence": float(prediction.get("confidence", 0.0)),
        "probabilities": prediction.get("probabilities", {}),
        "risk_score": float(risk_result.get("risk_score", 0.0)),
        "risk_category": str(risk_result.get("risk_level", "MEDIUM")).capitalize(),
        "indicators": {
            "close": indicators.get("close"),
            "daily_return": indicators.get("daily_return"),
            "ma_5": indicators.get("ma_5"),
            "ma_50": indicators.get("ma_50"),
            "rsi_14": indicators.get("rsi_14"),
            "macd": indicators.get("macd"),
            "macd_signal": indicators.get("macd_signal"),
            "volatility_20": indicators.get("volatility_20"),
            "volume_change": indicators.get("volume_change"),
            "price_change_pct": indicators.get("price_change_pct"),
            "high_low_pct": indicators.get("high_low_pct"),
        },
        "feature_importance": feature_importances or {},
        "risk_components": {
            "volatility": components.get("volatility"),
            "max_drawdown": components.get("max_drawdown"),
            "downside_volatility": components.get("downside_volatility"),
            "recent_volatility": components.get("recent_volatility"),
        },
        "risk_metrics": {
            "annualized_volatility": raw_metrics.get("annualized_volatility"),
            "max_drawdown": raw_metrics.get("max_drawdown"),
            "downside_volatility": raw_metrics.get("downside_volatility"),
            "recent_volatility": raw_metrics.get("recent_volatility"),
        },
    }
    return compact


def _explain_single_feature(
    feat: str,
    val: Any,
    indicators: Dict[str, Any],
    risk_metrics: Dict[str, Any],
) -> str:
    """Generates an objective, indicator-grounded explanation for a feature value."""
    close = indicators.get("close")
    ma_5 = indicators.get("ma_5")
    ma_50 = indicators.get("ma_50")

    if feat == "Volatility_20":
        if isinstance(val, (int, float)):
            if val > 0.025:
                return (
                    f"20-day rolling volatility is elevated ({val:.2%}), indicating larger price swings "
                    "and greater forecast dispersion."
                )
            elif val < 0.012:
                return (
                    f"20-day rolling volatility is subdued ({val:.2%}), reflecting calm price behavior "
                    "and tighter trading ranges."
                )
            return (
                f"20-day rolling volatility is moderate ({val:.2%}), reflecting standard trading fluctuation."
            )
        return "20-day historical volatility informs the model of recent variance in price action."

    elif feat == "High_Low_Pct":
        if isinstance(val, (int, float)):
            return (
                f"Intraday price spread of {val:.2%} indicates active intraday price discovery "
                "relative to typical ranges."
            )
        return "Intraday high-low range indicates intraday price span."

    elif feat == "Close":
        if isinstance(val, (int, float)) and ma_50 is not None:
            rel = "above" if val >= ma_50 else "below"
            return (
                f"Latest closing price ({val:.2f}) is positioned {rel} the 50-day moving average "
                f"({ma_50:.2f}), confirming medium-term price alignment."
            )
        return f"Closing price ({val}) anchors baseline valuation for trend determination."

    elif feat == "MA_5":
        if isinstance(val, (int, float)) and close is not None:
            rel = "above" if close >= val else "below"
            return (
                f"Short-term 5-day average stands at {val:.2f}; price is currently {rel} this short-term benchmark."
            )
        return f"5-day moving average ({val}) tracks immediate short-term directional momentum."

    elif feat == "MA_50":
        if isinstance(val, (int, float)) and close is not None:
            rel = "above" if close >= val else "below"
            return (
                f"50-day moving average is {val:.2f}; holding {rel} this level reflects medium-term trend posture."
            )
        return f"50-day moving average ({val}) represents the intermediate trend baseline."

    elif feat == "RSI_14":
        if isinstance(val, (int, float)):
            if val > 70:
                return (
                    f"RSI-14 is at {val:.1f}, entering potentially overbought territory where upward momentum "
                    "may face near-term resistance."
                )
            elif val < 30:
                return (
                    f"RSI-14 is at {val:.1f}, in potentially oversold territory, indicating strong recent "
                    "selling pressure that may stabilize."
                )
            return (
                f"RSI-14 is at {val:.1f}, residing in the neutral momentum corridor (30–70)."
            )
        return "RSI measures relative speed and magnitude of recent price changes."

    elif feat in ("MACD", "MACD_Signal"):
        macd = indicators.get("macd")
        sig = indicators.get("macd_signal")
        if isinstance(macd, (int, float)) and isinstance(sig, (int, float)):
            diff = macd - sig
            if macd > 0 and diff > 0:
                return (
                    f"MACD line ({macd:.4f}) is positive and above signal line ({sig:.4f}), reflecting "
                    "constructive upward momentum."
                )
            elif macd < 0 and diff < 0:
                return (
                    f"MACD line ({macd:.4f}) is negative and below signal line ({sig:.4f}), indicating "
                    "bearish momentum pressure."
                )
            return (
                f"MACD ({macd:.4f}) and signal ({sig:.4f}) reflect a momentum convergence zone."
            )
        return "MACD identifies changes in the strength, direction, and duration of the trend."

    elif feat == "Daily_Return" or feat == "Price_Change_Pct":
        if isinstance(val, (int, float)):
            direction = "positive" if val >= 0 else "negative"
            return (
                f"Latest session return was {direction} ({val:+.2%}), impacting the immediate directional bias."
            )
        return "Latest price return provides short-term directional impetus."

    elif feat in ("Volume", "Volume_Change"):
        vol_chg = indicators.get("volume_change")
        if isinstance(vol_chg, (int, float)):
            trend_str = "expansion" if vol_chg > 0 else "contraction"
            return (
                f"Volume change ratio indicates trading volume {trend_str} ({vol_chg:+.1%}) compared to recent sessions."
            )
        return "Volume reflects liquidity and conviction behind price movements."

    elif feat in ("High", "Low", "Open"):
        if isinstance(val, (int, float)):
            return f"Session {feat.lower()} recorded at {val:.2f}, defining the intraday boundary."
        return f"Session {feat.lower()} level informs intraday boundary conditions."

    return f"{FEATURE_DISPLAY_NAMES.get(feat, feat)} value is {val}."


def generate_explanation(
    prediction: Dict[str, Any],
    risk_result: Dict[str, Any],
    feature_importances: Optional[Dict[str, float]] = None,
    polish_llm: bool = True,
) -> Dict[str, Any]:
    """
    Deterministically converts structured XGBoost and risk results into
    human-readable explanations, key drivers, risk breakdown, and watch items.
    """
    compact = build_compact_analysis(prediction, risk_result, feature_importances)

    ticker = compact["ticker"]
    pred = compact["prediction"]
    conf = compact["confidence"]
    risk_score = compact["risk_score"]
    risk_category = compact["risk_category"]
    indicators = compact["indicators"]
    risk_metrics = compact["risk_metrics"]
    importances = compact["feature_importance"]

    # -------------------------------------------------------------------------
    # 1. Key Drivers (Top 3 features by model importance)
    # -------------------------------------------------------------------------
    # Sort feature importances descending
    sorted_features = sorted(
        importances.items(), key=lambda item: item[1], reverse=True
    )
    top_3_feats = sorted_features[:3] if sorted_features else []

    # Fallback if no feature importances passed
    if not top_3_feats:
        default_candidates = [
            ("Volatility_20", 0.35),
            ("High_Low_Pct", 0.22),
            ("RSI_14", 0.15),
        ]
        top_3_feats = default_candidates

    key_drivers: List[Dict[str, Any]] = []
    for feat_name, imp_score in top_3_feats:
        display_name = FEATURE_DISPLAY_NAMES.get(feat_name, feat_name)
        # Find indicator value
        raw_val = None
        key_lower = feat_name.lower()
        if feat_name in indicators:
            raw_val = indicators[feat_name]
        elif key_lower in indicators:
            raw_val = indicators[key_lower]
        elif feat_name == "High_Low_Pct":
            raw_val = indicators.get("high_low_pct")
        elif feat_name == "Volatility_20":
            raw_val = indicators.get("volatility_20")
        elif feat_name == "RSI_14":
            raw_val = indicators.get("rsi_14")
        elif feat_name == "MACD_Signal":
            raw_val = indicators.get("macd_signal")
        elif feat_name == "Daily_Return":
            raw_val = indicators.get("daily_return")
        elif feat_name == "Volume_Change":
            raw_val = indicators.get("volume_change")
        elif feat_name == "Price_Change_Pct":
            raw_val = indicators.get("price_change_pct")

        # Format display value
        if raw_val is None:
            val_str = "N/A"
        elif "Pct" in feat_name or "Return" in feat_name or "Volatility" in feat_name:
            val_str = f"{float(raw_val):.2%}"
        elif isinstance(raw_val, float):
            val_str = f"{raw_val:.2f}"
        else:
            val_str = str(raw_val)

        expl = _explain_single_feature(feat_name, raw_val, indicators, risk_metrics)

        key_drivers.append({
            "feature": feat_name,
            "name": display_name,
            "value": val_str,
            "importance": round(float(imp_score), 4),
            "explanation": expl,
        })

    # -------------------------------------------------------------------------
    # 2. Trend Explanation
    # -------------------------------------------------------------------------
    conf_pct = f"{conf * 100:.1f}%"
    close = indicators.get("close")
    ma_50 = indicators.get("ma_50")
    rsi = indicators.get("rsi_14")
    macd = indicators.get("macd")
    macd_sig = indicators.get("macd_signal")

    trend_details: List[str] = []
    if close is not None and ma_50 is not None:
        if close >= ma_50:
            trend_details.append(f"the latest close ({close:.2f}) trades above the 50-day moving average ({ma_50:.2f})")
        else:
            trend_details.append(f"the latest close ({close:.2f}) sits below the 50-day moving average ({ma_50:.2f})")

    if rsi is not None:
        if rsi > 70:
            trend_details.append(f"RSI-14 ({rsi:.1f}) is in overbought territory")
        elif rsi < 30:
            trend_details.append(f"RSI-14 ({rsi:.1f}) is in oversold territory")
        else:
            trend_details.append(f"RSI-14 ({rsi:.1f}) indicates balanced momentum")

    if macd is not None and macd_sig is not None:
        if macd > macd_sig:
            trend_details.append("MACD holds a positive momentum spread over its signal line")
        else:
            trend_details.append("MACD displays a negative divergence under its signal line")

    trend_supporting = "; ".join(trend_details) if trend_details else "standard technical indicators"

    if pred == "UP":
        trend_explanation = (
            f"The XGBoost trend model classifies the directional outlook as UP with {conf_pct} confidence. "
            f"This projection is supported by technical indicators: {trend_supporting}. "
            "These factors indicate constructive buying interest over the forecast horizon."
        )
    elif pred == "DOWN":
        trend_explanation = (
            f"The XGBoost trend model classifies the directional outlook as DOWN with {conf_pct} confidence. "
            f"This projection is driven by technical indicators: {trend_supporting}. "
            "These signals indicate prevailing overhead pressure and restrained buying momentum."
        )
    else:
        trend_explanation = (
            f"The XGBoost trend model classifies the directional outlook as FLAT with {conf_pct} confidence. "
            f"Current market structure shows balanced forces: {trend_supporting}. "
            "The model identifies range-bound price behavior without clear directional conviction."
        )

    # -------------------------------------------------------------------------
    # 3. Risk Explanation
    # -------------------------------------------------------------------------
    ann_vol = risk_metrics.get("annualized_volatility")
    max_dd = risk_metrics.get("max_drawdown")
    vol_text = f"{ann_vol:.1%}" if ann_vol is not None else "moderate"
    dd_text = f"{max_dd:.1%}" if max_dd is not None else "manageable"

    if risk_category.upper() == "LOW":
        risk_explanation = (
            f"The quantitative risk engine evaluates {ticker} as LOW RISK ({risk_score:.1f}/100). "
            f"Annualized volatility is well-contained at {vol_text}, and maximum historical drawdown is restrained at {dd_text}. "
            "Overall price stability remains robust relative to broader market peers."
        )
    elif risk_category.upper() == "HIGH":
        risk_explanation = (
            f"The quantitative risk engine assigns a HIGH RISK score of {risk_score:.1f}/100. "
            f"This reflects elevated annualized volatility ({vol_text}) alongside a maximum drawdown of {dd_text}. "
            "Capital fluctuations in this asset are substantially wider than market medians."
        )
    else:
        risk_explanation = (
            f"The quantitative risk engine assigns a MODERATE RISK score of {risk_score:.1f}/100. "
            f"Annualized volatility ({vol_text}) and peak historical drawdown ({dd_text}) reflect standard market swings. "
            "Downside exposure is present but aligns with typical equity profile norms."
        )

    # -------------------------------------------------------------------------
    # 4. Watch Items
    # -------------------------------------------------------------------------
    watch_items: List[str] = []
    if rsi is not None:
        if rsi > 65:
            watch_items.append(f"Monitor RSI-14 ({rsi:.1f}) for signs of exhaustion or pullback near resistance.")
        elif rsi < 35:
            watch_items.append(f"Watch RSI-14 ({rsi:.1f}) for a potential bullish divergence from oversold territory.")
        else:
            watch_items.append(f"Track RSI-14 ({rsi:.1f}) for any directional breakout beyond the 30–70 corridor.")

    if ma_50 is not None and close is not None:
        diff_pct = ((close - ma_50) / ma_50) * 100
        watch_items.append(
            f"Observe price action around the 50-day moving average ({ma_50:.2f}), currently {abs(diff_pct):.1f}% {'above' if diff_pct >= 0 else 'below'} current close."
        )

    if ann_vol is not None and ann_vol > 0.30:
        watch_items.append(f"Keep stop-loss and position-sizing disciplined due to heightened annualized volatility ({ann_vol:.1%}).")
    elif max_dd is not None:
        watch_items.append(f"Watch historical support levels established during the asset's {max_dd:.1%} peak-to-trough drawdown.")

    if len(watch_items) < 2:
        watch_items.append("Track upcoming volume changes for confirmation of trend continuation or reversal.")

    # -------------------------------------------------------------------------
    # 5. Overall Summary
    # -------------------------------------------------------------------------
    driver_names = [d["name"] for d in key_drivers[:2]]
    drivers_str = " and ".join(driver_names) if driver_names else "volatility indicators"
    headline = (
        f"{ticker}: {pred} trend outlook ({conf_pct} confidence) with {risk_category} risk ({risk_score:.1f}/100)"
    )
    summary = (
        f"FinSight AI model projects a {pred} directional trend ({conf_pct} confidence) with {risk_category} risk "
        f"({risk_score:.1f}/100) for {ticker}. Key contributors to this assessment are {drivers_str}, "
        f"alongside prevailing moving average and momentum metrics."
    )

    result = {
        "ticker": ticker,
        "prediction": pred,
        "confidence": round(conf, 4),
        "risk_score": round(risk_score, 2),
        "risk_level": risk_category.upper(),
        "headline": headline,
        "summary": summary,
        "trend_explanation": trend_explanation,
        "key_drivers": key_drivers,
        "risk_explanation": risk_explanation,
        "watch_items": watch_items,
        "compact_analysis": compact,
    }

    # Optional extension hook: natural language polish
    if polish_llm:
        result = _maybe_polish_with_llm(result, compact)
    else:
        from local_llm import is_llm_enabled
        result["llm"] = {"enabled": is_llm_enabled(), "used": False, "model": None}
    return result


def _maybe_polish_with_llm(
    structured_explanation: Dict[str, Any],
    compact_analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Applies the optional local LLM polishing layer if enabled.
    Attaches the 'llm' metadata object:
    {
        "enabled": bool,
        "used": bool,
        "model": Optional[str]
    }
    """
    from local_llm import polish_explanation_with_local_llm

    polished, llm_meta = polish_explanation_with_local_llm(
        structured_explanation, compact_analysis
    )
    polished["llm"] = llm_meta
    return polished
