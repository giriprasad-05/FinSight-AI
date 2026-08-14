import type { TrendAnalysis } from '@/types';
import { format } from 'date-fns';

const NOW_ISO = format(new Date(), "yyyy-MM-dd'T'HH:mm:ss");

export const MOCK_TREND_ANALYSES: Record<string, TrendAnalysis> = {
  AAPL: {
    ticker: 'AAPL',
    direction: 'Bullish',
    strength: 62,
    confidence: 76,
    shortTermOutlook: 'Apple shows moderate bullish momentum driven by services revenue growth and stable iPhone demand. The stock has been consolidating near its 50-day moving average, which is a healthy technical pattern.',
    longTermOutlook: 'Over the next 6–12 months, Apple\'s continued services expansion (App Store, Apple TV+, Apple Pay) and gradual AI integration (Apple Intelligence) into its product ecosystem support a cautiously optimistic long-term view.',
    signals: [
      { label: 'Moving Average (50D)', value: 'Price above — Bullish', supportingData: 'Stock trading 3.2% above 50-day MA' },
      { label: 'RSI (14-day)', value: '54 — Neutral to Bullish', supportingData: 'Not overbought, momentum building' },
      { label: 'Volume Trend', value: 'Declining on red days', supportingData: 'Selling pressure weakening' },
      { label: 'Earnings Trend', value: '4 consecutive beats', supportingData: 'EPS beat by avg 6.3% last 4 quarters' },
    ],
    featureImportances: [
      { feature: 'Price vs 50-Day MA', importance: 78, direction: 'positive', description: 'Being above the 50-day moving average means the stock\'s recent trend is upward — a bullish signal.' },
      { feature: 'Earnings Momentum', importance: 72, direction: 'positive', description: 'Consistently beating earnings expectations pushes institutional investors to buy, supporting the price.' },
      { feature: 'Volume on Up Days', importance: 61, direction: 'positive', description: 'Higher volume when the stock rises suggests real buying conviction, not just noise.' },
      { feature: 'RSI Indicator', importance: 55, direction: 'positive', description: 'An RSI of 54 is in neutral territory — the stock has room to run without being "overbought."' },
    ],
    disclaimer: 'This trend analysis is AI-generated for educational purposes only. It is based on historical patterns and does not predict future performance. Past trends do not guarantee future results.',
    generatedAt: NOW_ISO,
  },
  NVDA: {
    ticker: 'NVDA',
    direction: 'Volatile',
    strength: 78,
    confidence: 65,
    shortTermOutlook: 'NVIDIA is in a highly volatile consolidation phase after its extraordinary 2023–2024 run. Near-term price action is difficult to predict as the market reassesses AI spending growth rates and potential GPU oversupply.',
    longTermOutlook: 'Long-term structural demand for AI compute infrastructure remains enormous. NVIDIA\'s Blackwell GPU platform and its software moat (CUDA ecosystem) provide durable competitive advantages over the 2–5 year horizon.',
    signals: [
      { label: 'Moving Average (50D)', value: 'Fluctuating around MA — Volatile', supportingData: 'Multiple crossovers in past 60 days' },
      { label: 'RSI (14-day)', value: '48 — Neutral', supportingData: 'Neither overbought nor oversold' },
      { label: 'Analyst Revisions', value: 'Mixed — 68% Buy', supportingData: '32 Buy, 8 Hold, 2 Sell ratings' },
      { label: 'Options Implied Volatility', value: 'Very High', supportingData: 'Options market pricing in ±8% weekly moves' },
    ],
    featureImportances: [
      { feature: 'Price Volatility (30D)', importance: 94, direction: 'negative', description: 'NVIDIA\'s 30-day price swings are extreme — the options market expects ±8% weekly moves, which is very high.' },
      { feature: 'AI Capital Expenditure Trend', importance: 88, direction: 'positive', description: 'Hyperscalers (AWS, Azure, Google Cloud) are committing record capex to AI infrastructure — benefiting NVIDIA.' },
      { feature: 'Supply Chain Signals', importance: 71, direction: 'positive', description: 'Reports of tight GPU supply suggest demand continues to outpace production.' },
      { feature: 'Technical Pattern', importance: 62, direction: 'negative', description: 'Multiple MA crossovers indicate the market is undecided, making short-term direction uncertain.' },
    ],
    disclaimer: 'This trend analysis is AI-generated for educational purposes only. It is based on historical patterns and does not predict future performance. Past trends do not guarantee future results.',
    generatedAt: NOW_ISO,
  },
  MSFT: {
    ticker: 'MSFT',
    direction: 'Bullish',
    strength: 71,
    confidence: 82,
    shortTermOutlook: 'Microsoft demonstrates strong, consistent bullish momentum. Azure\'s acceleration and Copilot monetization are driving positive earnings revisions, encouraging institutional accumulation.',
    longTermOutlook: 'Microsoft\'s deep integration of AI across its enterprise suite (Teams, Office, Azure, GitHub Copilot) positions it uniquely to monetize AI at scale. Its large installed base of corporate clients provides a recurring upgrade path.',
    signals: [
      { label: 'Moving Average (50D)', value: 'Price above — Bullish', supportingData: 'Sustained above 50-day MA for 48 days' },
      { label: 'RSI (14-day)', value: '61 — Bullish', supportingData: 'Momentum building, not overbought' },
      { label: 'Earnings Trend', value: '6 consecutive beats', supportingData: 'Consistent outperformance' },
      { label: 'Institutional Buying', value: 'Net positive Q2 2025', supportingData: '$4.2B net institutional inflows' },
    ],
    featureImportances: [
      { feature: 'Azure Growth Rate', importance: 90, direction: 'positive', description: 'Azure growing at 21% YoY signals healthy cloud adoption — this is the primary growth engine.' },
      { feature: 'Earnings Consistency', importance: 82, direction: 'positive', description: '6 consecutive earnings beats means analysts consistently underestimate Microsoft\'s performance.' },
      { feature: 'Institutional Flows', importance: 74, direction: 'positive', description: 'When large institutions (pension funds, hedge funds) are net buyers, it\'s a positive signal.' },
      { feature: 'Beta Stability', importance: 65, direction: 'positive', description: 'Low beta of 0.89 means Microsoft\'s price rises more steadily and falls less sharply than peers.' },
    ],
    disclaimer: 'This trend analysis is AI-generated for educational purposes only. It is based on historical patterns and does not predict future performance. Past trends do not guarantee future results.',
    generatedAt: NOW_ISO,
  },
  TSLA: {
    ticker: 'TSLA',
    direction: 'Bearish',
    strength: 65,
    confidence: 68,
    shortTermOutlook: 'Tesla faces significant short-term headwinds. Declining vehicle deliveries, margin compression from price cuts, and weakening brand sentiment have pushed the stock below key technical support levels.',
    longTermOutlook: 'The long-term thesis for Tesla rests on autonomous driving (FSD/Robotaxi) and energy storage. If these succeed, the stock could dramatically re-rate upward. However, this is highly speculative and the timeline remains deeply uncertain.',
    signals: [
      { label: 'Moving Average (50D)', value: 'Price below — Bearish', supportingData: 'Trading 12.4% below 50-day MA' },
      { label: 'RSI (14-day)', value: '38 — Oversold Territory', supportingData: 'Approaching potential bounce zone' },
      { label: 'Delivery Growth', value: 'YoY decline — Negative', supportingData: 'Q1 2025 deliveries -9% vs prior year' },
      { label: 'Margin Trend', value: 'Compressing — Negative', supportingData: 'Auto gross margin fell to 16.3%' },
    ],
    featureImportances: [
      { feature: 'Delivery Volume Trend', importance: 92, direction: 'negative', description: 'For an auto company, declining deliveries directly hit revenue. This is a major bearish signal.' },
      { feature: 'Gross Margin Compression', importance: 84, direction: 'negative', description: 'Tesla cut prices to defend market share, but it hurt profitability. This is a difficult balance to maintain.' },
      { feature: 'Price vs 50-Day MA', importance: 78, direction: 'negative', description: 'Trading 12% below the 50-day moving average signals a sustained downtrend, not a temporary dip.' },
      { feature: 'RSI Oversold Reading', importance: 55, direction: 'positive', description: 'An RSI near 38 can signal the stock is oversold and due for a short-term bounce, even in a downtrend.' },
      { feature: 'FSD Monetization Potential', importance: 65, direction: 'positive', description: 'Any positive news on Tesla\'s autonomous driving technology could rapidly reverse the trend.' },
    ],
    disclaimer: 'This trend analysis is AI-generated for educational purposes only. It is based on historical patterns and does not predict future performance. Past trends do not guarantee future results.',
    generatedAt: NOW_ISO,
  },
};

function buildDefaultTrend(ticker: string): TrendAnalysis {
  const directions = ['Bullish', 'Bearish', 'Neutral', 'Volatile'] as const;
  const hash = ticker.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0);
  const dir = directions[hash % 4];
  return {
    ticker,
    direction: dir,
    strength: 40 + (hash % 40),
    confidence: 65 + (hash % 20),
    shortTermOutlook: `${ticker} shows ${dir.toLowerCase()} momentum based on recent price action, volume patterns, and fundamental indicators tracked by the model.`,
    longTermOutlook: `The long-term outlook for ${ticker} depends on sector trends, competitive positioning, and macroeconomic conditions. The model sees moderate uncertainty over a 6–12 month horizon.`,
    signals: [
      { label: 'Moving Average (50D)', value: dir === 'Bullish' ? 'Price above' : 'Price below', supportingData: 'Based on historical closing prices' },
      { label: 'RSI (14-day)', value: '52 — Neutral', supportingData: 'Moderate momentum' },
      { label: 'Volume Trend', value: 'Average', supportingData: 'Trading near 20-day average volume' },
    ],
    featureImportances: [
      { feature: 'Price Momentum', importance: 70, direction: dir === 'Bearish' ? 'negative' : 'positive', description: 'Recent price direction is the strongest short-term indicator in the model.' },
      { feature: 'Volume Confirmation', importance: 58, direction: 'positive', description: 'Volume validates whether price moves are driven by real conviction or just noise.' },
      { feature: 'RSI Momentum', importance: 48, direction: 'positive', description: 'RSI measures the speed and magnitude of price movements to identify overbought/oversold conditions.' },
    ],
    disclaimer: 'This trend analysis is AI-generated for educational purposes only. It is based on historical patterns and does not predict future performance. Past trends do not guarantee future results.',
    generatedAt: NOW_ISO,
  };
}

export function getMockTrendAnalysis(ticker: string): TrendAnalysis {
  return MOCK_TREND_ANALYSES[ticker] ?? buildDefaultTrend(ticker);
}
