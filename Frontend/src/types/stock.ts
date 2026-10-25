// ── Stock types ──────────────────────────────────────────────

export type TimeRange = '1W' | '1M' | '3M' | '6M' | '1Y' | '5Y';

export type MarketStatus = 'open' | 'closed' | 'pre-market' | 'after-hours';

export interface StockMeta {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  exchange: string;
  country: string;
  logo?: string;
}

export interface StockDetail extends StockMeta {
  price: number;
  priceChange: number;        // absolute change today
  priceChangePct: number;     // percentage change today
  marketCap: number;          // in local currency
  volume: number;
  avgVolume: number;
  peRatio: number | null;
  eps: number | null;
  dividendYield: number | null;
  beta: number;
  yearHigh: number;
  yearLow: number;
  description: string;
  ceo: string;
  employees: number;
  founded: number;
  website: string;
  marketStatus: MarketStatus;
  // Real-data fields (populated when VITE_USE_MOCK=false)
  currency?: string;            // e.g. 'USD' or 'INR'
  market?: string;              // 'US' | 'IN'
  quoteTimestamp?: string | null; // ISO timestamp from yfinance
}

export interface PricePoint {
  date: string;      // ISO date string
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export type PriceHistory = {
  [K in TimeRange]: PricePoint[];
};
