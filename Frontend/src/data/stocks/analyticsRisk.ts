import type { RiskAssessment } from '@/types';
import { format } from 'date-fns';

const NOW_ISO = format(new Date(), "yyyy-MM-dd'T'HH:mm:ss");

export const MOCK_RISK_ASSESSMENTS: Record<string, RiskAssessment> = {
  AAPL: {
    ticker: 'AAPL',
    riskScore: 38,
    riskLevel: 'Low',
    confidence: 84,
    factors: [
      { label: 'Market Cap Stability', value: '$3.28T — mega cap', impact: 'positive', weight: 0.22 },
      { label: 'Revenue Diversification', value: 'Services growing to 26% of revenue', impact: 'positive', weight: 0.19 },
      { label: 'Beta', value: '1.19 — slightly above market', impact: 'neutral', weight: 0.14 },
      { label: 'Dividend History', value: '11 years of consecutive increases', impact: 'positive', weight: 0.16 },
      { label: 'China Revenue Exposure', value: '~18% of sales — geopolitical risk', impact: 'negative', weight: 0.17 },
      { label: 'Valuation Premium', value: 'P/E 34.2 — above sector average', impact: 'negative', weight: 0.12 },
    ],
    featureImportances: [
      { feature: 'Market Capitalization', importance: 88, direction: 'positive', description: 'Very large companies are generally more stable — they have resources to weather downturns.' },
      { feature: 'Revenue Growth (YoY)', importance: 74, direction: 'positive', description: 'Consistent revenue growth signals strong demand for Apple\'s products.' },
      { feature: 'Debt-to-Equity Ratio', importance: 62, direction: 'positive', description: 'Apple carries manageable debt relative to its equity — a sign of financial discipline.' },
      { feature: 'Beta Coefficient', importance: 55, direction: 'negative', description: 'Beta of 1.19 means Apple tends to move slightly more than the overall market — adding some volatility.' },
      { feature: 'Geopolitical Exposure', importance: 48, direction: 'negative', description: 'Heavy reliance on Chinese manufacturing and sales creates risk from trade tensions.' },
      { feature: 'P/E Ratio', importance: 41, direction: 'negative', description: 'At 34.2x earnings, Apple is priced at a premium. If growth disappoints, the stock can fall sharply.' },
    ],
    summary: 'Apple presents a LOW risk profile for educational review. Its massive scale, brand loyalty, and growing services revenue buffer it against short-term shocks. However, its premium valuation and China exposure are worth monitoring.',
    educationalNote: 'Low-risk stocks like AAPL are often called "blue chip" stocks — they are large, well-established companies with a long history of stability. They\'re typically less exciting than high-growth stocks, but they\'re also less likely to lose large amounts of value quickly.',
    modelVersion: 'rf-v2.1-mock',
    generatedAt: NOW_ISO,
  },
  NVDA: {
    ticker: 'NVDA',
    riskScore: 72,
    riskLevel: 'High',
    confidence: 78,
    factors: [
      { label: 'AI Demand Tailwind', value: 'Dominant GPU market position in AI', impact: 'positive', weight: 0.20 },
      { label: 'Valuation Stretch', value: 'P/E 67.3 — very elevated', impact: 'negative', weight: 0.22 },
      { label: 'Beta', value: '1.68 — significantly above market', impact: 'negative', weight: 0.18 },
      { label: 'Concentration Risk', value: 'Top 5 customers = ~46% of revenue', impact: 'negative', weight: 0.16 },
      { label: 'Export Restrictions', value: 'US chip restrictions to China', impact: 'negative', weight: 0.14 },
      { label: 'No Dividend', value: 'Dividend yield 0.03% — reinvestment mode', impact: 'neutral', weight: 0.10 },
    ],
    featureImportances: [
      { feature: 'Valuation (P/E)', importance: 91, direction: 'negative', description: 'At 67x earnings, NVIDIA is priced for perfection. Any miss in AI demand could trigger a sharp correction.' },
      { feature: 'Beta Coefficient', importance: 85, direction: 'negative', description: 'NVIDIA moves ~68% more than the market on average. Big swings up AND down are common.' },
      { feature: 'Revenue Concentration', importance: 76, direction: 'negative', description: 'Relying heavily on a few large customers (hyperscalers) creates revenue risk if any of them reduce orders.' },
      { feature: 'AI Sector Growth', importance: 88, direction: 'positive', description: 'NVIDIA is the critical pick-and-shovel play in AI — every AI system needs GPUs.' },
      { feature: 'Regulatory Risk', importance: 68, direction: 'negative', description: 'US government restrictions on chip exports to China have already cut into revenue.' },
      { feature: 'R&D Spending', importance: 62, direction: 'positive', description: 'NVIDIA spends heavily on R&D, keeping its technology lead wide against competitors like AMD.' },
    ],
    summary: 'NVIDIA presents a HIGH risk profile for educational review. While it is the leading beneficiary of AI infrastructure spending, its extreme valuation, high beta, and customer concentration mean significant downside risk if the AI boom slows.',
    educationalNote: 'High-risk, high-reward stocks like NVDA are called "growth stocks." They\'re priced for explosive future growth. When expectations are met or exceeded, returns can be spectacular. But when growth disappoints even slightly, the stock can drop 20–40% very quickly.',
    modelVersion: 'rf-v2.1-mock',
    generatedAt: NOW_ISO,
  },
  MSFT: {
    ticker: 'MSFT',
    riskScore: 30,
    riskLevel: 'Low',
    confidence: 87,
    factors: [
      { label: 'Azure Cloud Growth', value: '21% YoY growth — strong', impact: 'positive', weight: 0.24 },
      { label: 'Enterprise Dominance', value: 'Microsoft 365 deeply embedded', impact: 'positive', weight: 0.20 },
      { label: 'Conservative Beta', value: '0.89 — less volatile than market', impact: 'positive', weight: 0.16 },
      { label: 'Dividend Growth', value: '22 consecutive years of increases', impact: 'positive', weight: 0.18 },
      { label: 'AI Integration', value: 'Copilot across product suite', impact: 'positive', weight: 0.14 },
      { label: 'Premium Valuation', value: 'P/E 38.4 — elevated but justified', impact: 'neutral', weight: 0.08 },
    ],
    featureImportances: [
      { feature: 'Business Diversification', importance: 92, direction: 'positive', description: 'Microsoft earns from cloud, software, gaming, and hardware — no single product dependency.' },
      { feature: 'Beta Coefficient', importance: 78, direction: 'positive', description: 'A beta below 1.0 means Microsoft moves LESS than the market — smoother price action.' },
      { feature: 'Revenue Predictability', importance: 84, direction: 'positive', description: 'Subscription-based revenues from Microsoft 365 and Azure are highly recurring and predictable.' },
      { feature: 'Free Cash Flow', importance: 76, direction: 'positive', description: 'Microsoft generates enormous free cash flow — over $70B annually — giving it flexibility to invest or return capital.' },
      { feature: 'Valuation Premium', importance: 52, direction: 'negative', description: 'At 38x earnings, Microsoft is expensive. This limits upside potential in the near term.' },
    ],
    summary: 'Microsoft presents a LOW risk profile for educational review. Its diversified cloud business, steady dividend growth, sub-market beta, and massive free cash flow make it one of the most stable large-cap technology investments.',
    educationalNote: 'Microsoft is a "quality compounder" — a type of investment that may not explode in value overnight, but consistently grows over long periods. Many long-term investors prefer quality compounders because they sleep better at night holding them.',
    modelVersion: 'rf-v2.1-mock',
    generatedAt: NOW_ISO,
  },
  TSLA: {
    ticker: 'TSLA',
    riskScore: 88,
    riskLevel: 'Very High',
    confidence: 71,
    factors: [
      { label: 'CEO Distraction Risk', value: 'Musk managing multiple companies', impact: 'negative', weight: 0.18 },
      { label: 'Extreme Beta', value: '2.35 — moves 2.35x vs market', impact: 'negative', weight: 0.20 },
      { label: 'EV Competition Surge', value: 'Chinese EV brands pressuring margins', impact: 'negative', weight: 0.18 },
      { label: 'Robotaxi Optionality', value: 'FSD and Cybercab could transform business', impact: 'positive', weight: 0.15 },
      { label: 'Brand Polarization', value: 'Political controversy affecting sales', impact: 'negative', weight: 0.16 },
      { label: 'No Dividend', value: 'All cash reinvested into growth', impact: 'neutral', weight: 0.13 },
    ],
    featureImportances: [
      { feature: 'Beta Coefficient', importance: 96, direction: 'negative', description: 'Tesla moves more than twice as much as the stock market. A 10% market drop could mean a 20%+ Tesla drop.' },
      { feature: 'Valuation Premium', importance: 88, direction: 'negative', description: 'At 78x earnings, Tesla is priced as a technology company, not a car company. This is very risky if growth slows.' },
      { feature: 'Competitive Pressure', importance: 82, direction: 'negative', description: 'Chinese EV makers like BYD are offering comparable vehicles at lower prices, squeezing Tesla\'s market share.' },
      { feature: 'Autonomous Driving Potential', importance: 78, direction: 'positive', description: 'If Tesla\'s Full Self-Driving technology succeeds, it could unlock a massive new revenue stream from robotaxis.' },
      { feature: 'Brand Sentiment', importance: 65, direction: 'negative', description: 'Tesla\'s brand is closely tied to Elon Musk, whose controversial public behavior has affected consumer sentiment.' },
    ],
    summary: 'Tesla presents a VERY HIGH risk profile for educational review. Extreme price volatility, stretched valuation, intensifying EV competition, and CEO-related risks make Tesla one of the highest-risk large-cap stocks in the market.',
    educationalNote: 'Tesla is a "speculative growth stock." Its price already reflects enormous future success. If that future arrives as hoped, gains can be massive. But if any major assumption (autonomous driving timeline, market share, execution) is wrong, losses can be severe and fast. Beginners should understand this before considering any exposure.',
    modelVersion: 'rf-v2.1-mock',
    generatedAt: NOW_ISO,
  },
};

// ── Parameterized risk for remaining tickers ──────────────────
const RISK_DEFAULTS: Record<string, Pick<RiskAssessment, 'riskScore' | 'riskLevel' | 'confidence'>> = {
  AMZN:  { riskScore: 45, riskLevel: 'Medium',    confidence: 81 },
  GOOGL: { riskScore: 35, riskLevel: 'Low',        confidence: 85 },
  META:  { riskScore: 50, riskLevel: 'Medium',     confidence: 79 },
  JPM:   { riskScore: 42, riskLevel: 'Medium',     confidence: 82 },
  NFLX:  { riskScore: 60, riskLevel: 'High',       confidence: 75 },
  V:     { riskScore: 28, riskLevel: 'Low',        confidence: 89 },
  DIS:   { riskScore: 55, riskLevel: 'Medium',     confidence: 76 },
  NVAX:  { riskScore: 92, riskLevel: 'Very High',  confidence: 68 },
  AMD:   { riskScore: 68, riskLevel: 'High',       confidence: 77 },
  INTC:  { riskScore: 63, riskLevel: 'High',       confidence: 74 },
  UBER:  { riskScore: 58, riskLevel: 'Medium',     confidence: 78 },
};

function buildDefaultRisk(ticker: string): RiskAssessment {
  const d = RISK_DEFAULTS[ticker] ?? { riskScore: 50, riskLevel: 'Medium' as const, confidence: 75 };
  return {
    ticker,
    ...d,
    riskLevel: d.riskLevel,
    factors: [
      { label: 'Market Cap', value: 'Large cap', impact: 'positive', weight: 0.25 },
      { label: 'Beta', value: 'Market-aligned', impact: 'neutral', weight: 0.20 },
      { label: 'Revenue Trend', value: 'Positive growth', impact: 'positive', weight: 0.20 },
      { label: 'Debt Levels', value: 'Manageable', impact: 'neutral', weight: 0.15 },
      { label: 'Competitive Position', value: 'Strong moat', impact: 'positive', weight: 0.20 },
    ],
    featureImportances: [
      { feature: 'Market Capitalization', importance: 75, direction: 'positive', description: 'Larger companies tend to be more stable investments.' },
      { feature: 'Revenue Growth', importance: 65, direction: 'positive', description: 'Consistent revenue growth signals healthy business fundamentals.' },
      { feature: 'Volatility (Beta)', importance: 58, direction: 'negative', description: 'Higher beta means larger price swings in both directions.' },
      { feature: 'Profitability', importance: 52, direction: 'positive', description: 'Profitable companies have more resilience during economic downturns.' },
    ],
    summary: `${ticker} presents a ${d.riskLevel.toUpperCase()} risk profile for educational review. The AI model assessed market position, financial health, volatility, and sector dynamics.`,
    educationalNote: 'Every investment carries risk. Understanding a stock\'s risk level helps you make informed decisions about how it fits into a balanced portfolio.',
    modelVersion: 'rf-v2.1-mock',
    generatedAt: NOW_ISO,
  };
}

export function getMockRiskAssessment(ticker: string): RiskAssessment {
  return MOCK_RISK_ASSESSMENTS[ticker] ?? buildDefaultRisk(ticker);
}
