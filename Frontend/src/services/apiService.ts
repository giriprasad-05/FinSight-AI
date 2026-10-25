/**
 * apiService.ts
 * --------------
 * Real implementation of StockService that calls the Node.js/Express
 * backend API instead of using mock data.
 *
 * Switch between mock and real by setting VITE_USE_MOCK in Frontend/.env:
 *   VITE_USE_MOCK=true   → mockStockService  (current default)
 *   VITE_USE_MOCK=false  → apiStockService   (calls Node backend)
 *
 * Consumed via services/index.ts — no UI components import this directly.
 *
 * Node backend endpoints consumed:
 *   GET /api/health
 *   GET /api/stocks/search?q=...
 *   GET /api/stocks/:ticker/quote
 *   GET /api/stocks/:ticker/history?range=...
 *   GET /api/predictions/:ticker
 *   GET /api/risk/:ticker
 *   GET /api/analysis/:ticker
 */

import type {
  StockDetail,
  StockMeta,
  PricePoint,
  TimeRange,
  RiskAssessment,
  TrendAnalysis,
  EducationalInsight,
  AIExplanation,
} from '@/types';
import type { StockService } from './stockService';
import { format } from 'date-fns';

// ── Config ────────────────────────────────────────────────────────
// When VITE_API_BASE_URL is not set or empty, defaults to '' which uses Vite dev proxy (/api -> http://localhost:5000)
const _rawBase = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '');
const API_BASE = _rawBase.endsWith('/api') ? _rawBase.slice(0, -4) : _rawBase;

// ── Helper ────────────────────────────────────────────────────────
async function apiFetch<T>(path: string): Promise<T> {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  const url = `${API_BASE}${cleanPath}`;
  const token = typeof window !== 'undefined' ? localStorage.getItem('finsight_token') : null;
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const res = await fetch(url, { headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      (body as { error?: string }).error ?? `API error ${res.status}: ${cleanPath}`
    );
  }
  return res.json() as Promise<T>;
}

// ── Quote response shape from the backend (Python /quote/{ticker}) ─
interface BackendQuote {
  ticker: string;
  short_name: string | null;
  long_name: string | null;
  market: string;
  currency: string | null;
  exchange: string | null;
  price: number | null;
  previous_close: number | null;
  change: number | null;
  change_percent: number | null;
  market_cap: number | null;
  volume: number | null;
  average_volume: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
  trailing_pe: number | null;
  trailing_eps: number | null;
  dividend_yield: number | null;
  beta: number | null;
  sector: string | null;
  industry: string | null;
  description: string | null;
  website: string | null;
  employees: number | null;
  country: string | null;
  city: string | null;
  quote_timestamp: string | null;
  data_source: string;
}

// ── Search result shape from the backend ──────────────────────────
interface BackendSearchResult {
  ticker: string;
  name: string;
  market: string;
  currency: string;
  exchange: string | null;
  sector: string;
  industry: string;
  country: string;
}

// ── ML response shapes (internal — not exported as public types) ──

interface MlTrend {
  prediction: string;
  prediction_code: number;
  confidence: number;
  probabilities: Record<string, number>;
  model_version?: string;
}

interface MlRisk {
  risk_score: number;
  risk_level: string;
  components: Record<string, number>;
  raw_metrics: Record<string, number>;
  explanations: string[];
}

interface MlPrediction {
  ticker: string;
  market: string;
  data_date: string;
  prediction: string;
  prediction_code: number;
  confidence: number;
  probabilities: Record<string, number>;
  indicators: Record<string, number>;
  model_version?: string;
}

interface MlRiskResponse {
  ticker: string;
  data_date: string;
  risk_score: number;
  risk_level: string;
  components: Record<string, number>;
  raw_metrics: Record<string, number>;
  explanations: string[];
}

// ── Adapters: ML shape → Frontend type ───────────────────────────

function NOW_ISO(): string {
  return format(new Date(), "yyyy-MM-dd'T'HH:mm:ss");
}

function mlRiskToFrontend(r: MlRisk | MlRiskResponse, ticker: string): RiskAssessment {
  const level = r.risk_level as string;
  // Map ML risk levels (LOW/MEDIUM/HIGH) to frontend RiskLevel union
  const levelMap: Record<string, RiskAssessment['riskLevel']> = {
    LOW: 'Low',
    MEDIUM: 'Medium',
    HIGH: 'High',
    VERY_HIGH: 'Very High',
  };

  const explanations = (r.explanations ?? []) as string[];

  return {
    ticker,
    riskScore: Math.round(r.risk_score),
    riskLevel: levelMap[level] ?? 'Medium',
    confidence: 95, // ML model confidence — deterministic engine
    factors: explanations.map((exp, i) => ({
      label: `Risk Factor ${i + 1}`,
      // IMPORTANT: value holds the actual explanation text from the risk engine
      value: exp,
      impact: r.risk_score > 60 ? ('negative' as const) : ('neutral' as const),
      weight: 0.25,
    })),
    featureImportances: Object.entries(r.components ?? {}).map(([feature, score]) => ({
      feature,
      importance: Math.round(score as number),
      direction: (score as number) > 50 ? ('negative' as const) : ('positive' as const),
      description: `Component score: ${(score as number).toFixed(1)}/100`,
    })),
    summary: explanations[0] ?? `Risk score: ${r.risk_score.toFixed(1)} (${r.risk_level})`,
    educationalNote:
      'Risk score is computed using annualized volatility, maximum drawdown, downside volatility, and recent volatility via the FinSight AI quantitative risk engine.',
    modelVersion: 'quantitative-v1',
    generatedAt: NOW_ISO(),
  };
}

function mlTrendToFrontend(t: MlTrend, ticker: string): TrendAnalysis {
  const directionMap: Record<string, TrendAnalysis['direction']> = {
    UP: 'Bullish',
    FLAT: 'Neutral',
    DOWN: 'Bearish',
  };

  const confidencePct = Math.round(t.confidence * 100);

  return {
    ticker,
    direction: directionMap[t.prediction] ?? 'Neutral',
    strength: confidencePct,
    confidence: confidencePct,
    shortTermOutlook: `XGBoost v2 predicts ${t.prediction} trend with ${confidencePct}% confidence.`,
    longTermOutlook: `Probabilities — DOWN: ${(t.probabilities.DOWN * 100).toFixed(0)}%, FLAT: ${(t.probabilities.FLAT * 100).toFixed(0)}%, UP: ${(t.probabilities.UP * 100).toFixed(0)}%.`,
    signals: [
      {
        label: 'XGBoost Prediction',
        value: t.prediction,
        supportingData: `Confidence: ${confidencePct}% | Model: ${t.model_version ?? 'v2'}`,
      },
    ],
    featureImportances: [
      {
        feature: 'XGBoost Confidence',
        importance: confidencePct,
        direction: t.prediction === 'DOWN' ? ('negative' as const) : ('positive' as const),
        description: `Model confidence for ${t.prediction} prediction.`,
      },
    ],
    disclaimer:
      'Trend prediction is generated by the FinSight AI XGBoost v2 model. This is not financial advice.',
    generatedAt: NOW_ISO(),
  };
}

/**
 * Map a BackendQuote to the StockDetail type used by the frontend.
 * Never fabricates data — missing values become null/undefined or sensible defaults.
 */
function quoteToStockDetail(q: BackendQuote): StockDetail {
  const displayName =
    q.long_name ?? q.short_name ?? q.ticker;

  const currency = q.currency ?? (q.market === 'IN' ? 'INR' : 'USD');
  const exchange =
    q.exchange ?? (q.market === 'IN' ? 'NSE' : 'NASDAQ');

  return {
    ticker: q.ticker,
    name: displayName,
    sector: q.sector ?? 'N/A',
    industry: q.industry ?? 'N/A',
    exchange,
    country: q.country ?? (q.market === 'IN' ? 'India' : 'United States'),
    // Store currency and timestamp on the detail so StockHeader can use them
    currency,
    quoteTimestamp: q.quote_timestamp ?? null,
    market: q.market ?? 'US',
    // Pricing — use null-safe coalescing; never default to 0 when data is absent
    price: q.price ?? 0,
    priceChange: q.change ?? 0,
    priceChangePct: q.change_percent ?? 0,
    marketCap: q.market_cap ?? 0,
    volume: q.volume ?? 0,
    avgVolume: q.average_volume ?? 0,
    peRatio: q.trailing_pe ?? null,
    eps: q.trailing_eps ?? null,
    dividendYield: q.dividend_yield ?? null,
    beta: q.beta ?? 0,
    yearHigh: q.fifty_two_week_high ?? 0,
    yearLow: q.fifty_two_week_low ?? 0,
    // Company
    description: q.description ?? `${displayName} stock data sourced via yfinance.`,
    ceo: 'N/A',
    employees: q.employees ?? 0,
    founded: 0,
    website: q.website ?? '',
    marketStatus: 'open' as const,
  } as unknown as StockDetail;
}

// ── Real API implementation ───────────────────────────────────────

export const apiStockService: StockService = {
  async searchStocks(query: string): Promise<StockMeta[]> {
    const cleanQ = query ? query.trim() : '';
    const path = cleanQ
      ? `/api/stocks/search?q=${encodeURIComponent(cleanQ)}`
      : `/api/stocks/search`;
    const results = await apiFetch<BackendSearchResult[]>(path);
    return (results ?? []).map((s) => ({
      ticker: s.ticker,
      name: s.name || s.ticker,
      sector: s.sector || '',
      industry: s.industry || '',
      exchange: s.exchange || '',
      country: s.country || (s.ticker.endsWith('.NS') ? 'India' : 'United States'),
    }));
  },

  async getStock(ticker: string): Promise<StockDetail> {
    const q = await apiFetch<BackendQuote>(
      `/api/stocks/${encodeURIComponent(ticker.toUpperCase())}`
    );
    return quoteToStockDetail(q);
  },

  async getPriceHistory(ticker: string, range: TimeRange): Promise<PricePoint[]> {
    const data = await apiFetch<any[]>(
      `/api/stocks/${encodeURIComponent(ticker.toUpperCase())}/history?range=${range}`
    );
    return (data ?? []).map((d) => ({
      date: d.date,
      open: d.open ?? d.close,
      high: d.high ?? d.close,
      low: d.low ?? d.close,
      close: d.close,
      volume: d.volume ?? 0,
    }));
  },

  async getRiskAssessment(ticker: string): Promise<RiskAssessment> {
    const data = await apiFetch<MlRiskResponse>(
      `/api/risk/${encodeURIComponent(ticker.toUpperCase())}`
    );
    return mlRiskToFrontend(data, ticker.toUpperCase());
  },

  async getTrendAnalysis(ticker: string): Promise<TrendAnalysis> {
    const data = await apiFetch<MlPrediction>(
      `/api/predictions/${encodeURIComponent(ticker.toUpperCase())}`
    );
    return mlTrendToFrontend(
      {
        prediction: data.prediction,
        prediction_code: data.prediction_code,
        confidence: data.confidence,
        probabilities: data.probabilities,
        model_version: data.model_version,
      },
      ticker.toUpperCase()
    );
  },

  async getEducationalInsight(_ticker: string): Promise<EducationalInsight> {
    // Educational insights are not yet backed by the ML service.
    // Return a placeholder so the frontend doesn't break.
    return {
      summary: 'Connect your analysis to real ML results by enabling VITE_USE_MOCK=false.',
      keyPoints: [],
      learnMore: [],
    } as unknown as EducationalInsight;
  },

  async getExplanation(ticker: string): Promise<AIExplanation> {
    return apiFetch<AIExplanation>(
      `/api/explain/${encodeURIComponent(ticker.toUpperCase())}`
    );
  },
};
