import type { StockDetail, StockMeta, PricePoint, TimeRange, RiskAssessment, TrendAnalysis, EducationalInsight, AIExplanation } from '@/types';
import { MOCK_DATABASE, MOCK_STOCK_LIST } from '@/data/stocks';

// ── Service interface — this is the contract both mock and real
// ── implementations must satisfy. Swapping is a one-line change.
export interface StockService {
  searchStocks(query: string): Promise<StockMeta[]>;
  getStock(ticker: string): Promise<StockDetail>;
  getPriceHistory(ticker: string, range: TimeRange): Promise<PricePoint[]>;
  getRiskAssessment(ticker: string): Promise<RiskAssessment>;
  getTrendAnalysis(ticker: string): Promise<TrendAnalysis>;
  getEducationalInsight(ticker: string): Promise<EducationalInsight>;
  getExplanation(ticker: string): Promise<AIExplanation>;
}

// ── Simulate realistic network latency ────────────────────────
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// ── Mock implementation ───────────────────────────────────────
export const mockStockService: StockService = {
  async searchStocks(query: string) {
    await delay(180);
    const q = query.toLowerCase().trim();
    if (!q) return MOCK_STOCK_LIST;
    return MOCK_STOCK_LIST.filter(
      s =>
        s.ticker.toLowerCase().includes(q) ||
        s.name.toLowerCase().includes(q) ||
        s.sector.toLowerCase().includes(q)
    );
  },

  async getStock(ticker: string) {
    await delay(240);
    const stock = MOCK_DATABASE[ticker.toUpperCase()];
    if (!stock) throw new Error(`Stock "${ticker}" not found in mock data`);
    
    // Assemble StockDetail from CanonicalStock
    return {
      ...stock.identity,
      ...stock.pricing,
      ...stock.company
    } as StockDetail;
  },

  async getPriceHistory(ticker: string, range: TimeRange) {
    await delay(320);
    const stock = MOCK_DATABASE[ticker.toUpperCase()];
    if (!stock) return [];
    return stock.history[range] ?? [];
  },

  async getRiskAssessment(ticker: string) {
    await delay(400);
    const stock = MOCK_DATABASE[ticker.toUpperCase()];
    if (!stock) throw new Error(`Stock "${ticker}" not found in mock data`);
    return stock.analytics.risk;
  },

  async getTrendAnalysis(ticker: string) {
    await delay(380);
    const stock = MOCK_DATABASE[ticker.toUpperCase()];
    if (!stock) throw new Error(`Stock "${ticker}" not found in mock data`);
    return stock.analytics.trend;
  },

  async getEducationalInsight(ticker: string) {
    await delay(200);
    const stock = MOCK_DATABASE[ticker.toUpperCase()];
    if (!stock) throw new Error(`Stock "${ticker}" not found in mock data`);
    return stock.education;
  },

  async getExplanation(ticker: string): Promise<AIExplanation> {
    await delay(300);
    const stock = MOCK_DATABASE[ticker.toUpperCase()];
    const t = stock?.analytics.trend;
    const r = stock?.analytics.risk;
    return {
      ticker: ticker.toUpperCase(),
      prediction: t?.direction === 'Bullish' ? 'UP' : t?.direction === 'Bearish' ? 'DOWN' : 'FLAT',
      confidence: (t?.confidence ?? 60) / 100,
      risk_score: r?.riskScore ?? 35,
      risk_level: r?.riskLevel?.toUpperCase() ?? 'MEDIUM',
      summary: `FinSight AI models indicate a ${t?.direction ?? 'Neutral'} directional outlook with ${r?.riskLevel ?? 'Medium'} risk for ${ticker.toUpperCase()}.`,
      trend_explanation: `Model projects ${t?.direction ?? 'Neutral'} trend based on momentum and moving average positioning.`,
      key_drivers: [
        {
          feature: 'Volatility_20',
          name: '20-Day Volatility',
          value: '1.45%',
          importance: 0.28,
          explanation: 'Rolling 20-day volatility indicates standard price variation.',
        },
        {
          feature: 'High_Low_Pct',
          name: 'Intraday Price Range',
          value: '1.80%',
          importance: 0.18,
          explanation: 'Intraday price swings reflect active order matching and liquidity.',
        },
        {
          feature: 'Close',
          name: 'Closing Price',
          value: `$${stock?.pricing.price.toFixed(2) ?? '150.00'}`,
          importance: 0.12,
          explanation: 'Price positioning relative to technical baselines.',
        },
      ],
      risk_explanation: `Quantitative risk score of ${r?.riskScore ?? 35}/100 places ${ticker.toUpperCase()} in the ${r?.riskLevel ?? 'Medium'} risk tier.`,
      watch_items: [
        'Monitor RSI for shifts beyond key boundary ranges.',
        'Watch reaction near 50-day moving average support.',
      ],
    };
  },
};
