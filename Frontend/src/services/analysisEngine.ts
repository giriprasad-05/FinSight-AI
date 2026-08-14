import type { RiskAssessment, TrendAnalysis, RiskLevel, TrendDirection, RiskFactor, FeatureImportance, TrendSignal, PricePoint } from '../types';
import { calculateSMA, calculateRSI, calculateMACD, calculateVolatility } from '../lib/indicators';
import { format } from 'date-fns';

export function analyzeStock(ticker: string, history: PricePoint[]): { risk: RiskAssessment, trend: TrendAnalysis } {
  const prices = history.map(p => p.close);
  const NOW_ISO = format(new Date(), "yyyy-MM-dd'T'HH:mm:ss");

  // 1. Calculate Indicators
  const sma20 = calculateSMA(prices, 20);
  const sma50 = calculateSMA(prices, 50);
  const rsi = calculateRSI(prices, 14);
  const macdResult = calculateMACD(prices);
  const volatility = calculateVolatility(prices, 20);

  // Safely get latest values
  const lastPrice = prices[prices.length - 1] ?? 0;
  const lastSma20 = sma20[sma20.length - 1] ?? lastPrice;
  const lastSma50 = sma50[sma50.length - 1] ?? lastPrice;
  const lastRsi = rsi[rsi.length - 1] ?? 50;
  const lastMacd = macdResult.macd[macdResult.macd.length - 1] ?? 0;
  const lastSignal = macdResult.signal[macdResult.signal.length - 1] ?? 0;

  // ── RISK ENGINE ──
  // Volatility (0.0 to ~0.5+): higher means more risk. Target 0.1=low, 0.4=high
  const volScore = Math.min(volatility * 200, 50); // max 50 points
  
  // RSI Extremes: <30 or >70 adds risk
  let rsiRisk = 0;
  if (lastRsi > 70) rsiRisk = (lastRsi - 70); // up to 30 points
  else if (lastRsi < 30) rsiRisk = (30 - lastRsi); // up to 30 points
  
  // SMA Deviation Risk: if price is way below SMA50, adds risk
  let devRisk = 0;
  if (lastPrice < lastSma50) {
    const drop = (lastSma50 - lastPrice) / lastSma50;
    devRisk = Math.min(drop * 200, 20); // max 20 points
  }

  const rawRiskScore = Math.round(Math.min(100, Math.max(0, volScore + rsiRisk + devRisk)));
  
  let riskLevel: RiskLevel = 'Medium';
  if (rawRiskScore <= 30) riskLevel = 'Low';
  else if (rawRiskScore <= 60) riskLevel = 'Medium';
  else if (rawRiskScore <= 80) riskLevel = 'High';
  else riskLevel = 'Very High';

  const riskFactors: RiskFactor[] = [
    {
      label: 'Historical Volatility',
      value: (volatility * 100).toFixed(1) + '%',
      impact: volatility > 0.25 ? 'negative' : (volatility < 0.15 ? 'positive' : 'neutral'),
      weight: 0.5
    },
    {
      label: 'RSI (14-day)',
      value: lastRsi.toFixed(1),
      impact: (lastRsi > 70 || lastRsi < 30) ? 'negative' : 'neutral',
      weight: 0.3
    },
    {
      label: 'Price vs SMA50',
      value: lastPrice >= lastSma50 ? 'Above' : 'Below',
      impact: lastPrice >= lastSma50 ? 'positive' : 'negative',
      weight: 0.2
    }
  ];

  const riskFeatures: FeatureImportance[] = [
    {
      feature: 'Volatility',
      importance: Math.round(volScore * 2),
      direction: volatility > 0.25 ? 'negative' : 'positive',
      description: `Annualized volatility of ${(volatility * 100).toFixed(1)}% indicates ${volatility > 0.25 ? 'high' : 'moderate'} price swings.`
    },
    {
      feature: 'Momentum (RSI)',
      importance: Math.round(rsiRisk * 3.33),
      direction: (lastRsi > 70 || lastRsi < 30) ? 'negative' : 'positive',
      description: `RSI at ${lastRsi.toFixed(1)} shows ${lastRsi > 70 ? 'overbought' : lastRsi < 30 ? 'oversold' : 'normal'} momentum.`
    }
  ];

  const riskSummary = `The deterministic analysis produced a risk score of ${rawRiskScore}, placing ${ticker} in the ${riskLevel} category. This is primarily driven by its recent volatility of ${(volatility * 100).toFixed(1)}% and momentum indicators.`;

  const riskAssessment: RiskAssessment = {
    ticker,
    riskScore: rawRiskScore,
    riskLevel,
    confidence: 85, // Deterministic rule confidence
    factors: riskFactors,
    featureImportances: riskFeatures,
    summary: riskSummary,
    educationalNote: `Risk is calculated using a rule-based combination of historical volatility, relative strength, and moving average deviations.`,
    modelVersion: 'deterministic-v1',
    generatedAt: NOW_ISO
  };

  // ── TREND ENGINE ──
  let trendScore = 0; // -3 to +3
  
  // 1. Price vs SMA20
  if (lastPrice > lastSma20) trendScore += 1;
  else if (lastPrice < lastSma20) trendScore -= 1;

  // 2. SMA20 vs SMA50
  if (lastSma20 > lastSma50) trendScore += 1;
  else if (lastSma20 < lastSma50) trendScore -= 1;

  // 3. MACD
  if (lastMacd > lastSignal) trendScore += 1;
  else if (lastMacd < lastSignal) trendScore -= 1;

  let trendDirection: TrendDirection = 'Neutral';
  if (trendScore >= 1) trendDirection = 'Bullish';
  else if (trendScore <= -1) trendDirection = 'Bearish';
  else if (volatility > 0.4) trendDirection = 'Volatile';

  const confidence = Math.round(50 + (Math.abs(trendScore) / 3) * 45); // 50 to 95

  const trendSignals: TrendSignal[] = [
    {
      label: 'Price vs SMA20',
      value: lastPrice > lastSma20 ? 'Above' : 'Below',
      supportingData: `Price: ${lastPrice.toFixed(2)}, SMA20: ${lastSma20.toFixed(2)}`
    },
    {
      label: 'SMA20 vs SMA50',
      value: lastSma20 > lastSma50 ? 'Bullish Cross' : 'Bearish Cross',
      supportingData: `SMA20: ${lastSma20.toFixed(2)}, SMA50: ${lastSma50.toFixed(2)}`
    },
    {
      label: 'MACD Signal',
      value: lastMacd > lastSignal ? 'Positive' : 'Negative',
      supportingData: `MACD: ${lastMacd.toFixed(2)}, Signal: ${lastSignal.toFixed(2)}`
    }
  ];

  const trendFeatures: FeatureImportance[] = [
    {
      feature: 'Moving Averages',
      importance: 80,
      direction: lastSma20 > lastSma50 ? 'positive' : 'negative',
      description: `Short-term moving average is ${lastSma20 > lastSma50 ? 'above' : 'below'} the long-term moving average.`
    },
    {
      feature: 'MACD Momentum',
      importance: 60,
      direction: lastMacd > lastSignal ? 'positive' : 'negative',
      description: `MACD is ${lastMacd > lastSignal ? 'above' : 'below'} its signal line, indicating ${lastMacd > lastSignal ? 'upward' : 'downward'} momentum.`
    }
  ];

  const trendAnalysis: TrendAnalysis = {
    ticker,
    direction: trendDirection,
    strength: confidence, // using strength field as confidence equivalent for UI
    confidence,
    shortTermOutlook: `The short-term trend is ${trendDirection.toLowerCase()}, driven by price being ${lastPrice > lastSma20 ? 'above' : 'below'} the 20-day SMA.`,
    longTermOutlook: `Long-term momentum is supported by the 20-day SMA being ${lastSma20 > lastSma50 ? 'above' : 'below'} the 50-day SMA.`,
    signals: trendSignals,
    featureImportances: trendFeatures,
    disclaimer: 'This trend is deterministically calculated using standard technical indicators (SMA, MACD).',
    generatedAt: NOW_ISO
  };

  return { risk: riskAssessment, trend: trendAnalysis };
}
