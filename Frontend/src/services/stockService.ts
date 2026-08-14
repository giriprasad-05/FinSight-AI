import type { StockDetail, StockMeta, PricePoint, TimeRange, RiskAssessment, TrendAnalysis, EducationalInsight } from '@/types';
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
};
