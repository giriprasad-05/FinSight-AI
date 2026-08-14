import type { StockDetail, PriceHistory } from './stock';
import type { RiskAssessment, TrendAnalysis, EducationalInsight } from './risk';

export interface CanonicalStock {
  identity: Pick<StockDetail, 'ticker' | 'name' | 'sector' | 'industry' | 'exchange' | 'country' | 'logo'>;
  pricing: Pick<StockDetail, 'price' | 'priceChange' | 'priceChangePct' | 'marketCap' | 'volume' | 'avgVolume' | 'peRatio' | 'eps' | 'dividendYield' | 'beta' | 'yearHigh' | 'yearLow' | 'marketStatus'>;
  company: Pick<StockDetail, 'description' | 'ceo' | 'employees' | 'founded' | 'website'>;
  history: PriceHistory;
  analytics: {
    risk: RiskAssessment;
    trend: TrendAnalysis;
  };
  education: EducationalInsight;
}
