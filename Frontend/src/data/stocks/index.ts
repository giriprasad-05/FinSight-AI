import type { CanonicalStock } from '@/types';
import { MOCK_STOCKS } from './core';
import { getMockPriceHistory } from './history';
import { buildEducationalInsight } from './education';
import { analyzeStock } from '@/services/analysisEngine';

export const MOCK_DATABASE: Record<string, CanonicalStock> = {};

// Build the mock database immediately
for (const [ticker, detail] of Object.entries(MOCK_STOCKS)) {
  const { 
    price, priceChange, priceChangePct, marketCap, volume, avgVolume, 
    peRatio, eps, dividendYield, beta, yearHigh, yearLow, marketStatus, 
    description, ceo, employees, founded, website,
    ...identity
  } = detail;

  const history = getMockPriceHistory(ticker);
  
  // Use 1Y history to calculate technical indicators
  const { risk, trend } = analyzeStock(ticker, history['1Y'] ?? []);
  
  MOCK_DATABASE[ticker] = {
    identity: {
      ticker: identity.ticker,
      name: identity.name,
      sector: identity.sector,
      industry: identity.industry,
      exchange: identity.exchange,
      country: identity.country,
      logo: identity.logo,
    },
    pricing: {
      price, priceChange, priceChangePct, marketCap, volume, avgVolume, 
      peRatio, eps, dividendYield, beta, yearHigh, yearLow, marketStatus
    },
    company: {
      description, ceo, employees, founded, website
    },
    history,
    analytics: {
      risk,
      trend,
    },
    education: buildEducationalInsight(ticker, risk.riskLevel),
  };
}

export const MOCK_STOCK_LIST = Object.values(MOCK_DATABASE).map(
  (stock) => stock.identity
);

export function getAllStocks() {
  return MOCK_STOCK_LIST;
}

export function getStockByTicker(ticker: string): CanonicalStock | undefined {
  return MOCK_DATABASE[ticker.toUpperCase()];
}
