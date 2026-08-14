import type { EducationalInsight, RiskLevel } from '@/types';

export function buildEducationalInsight(ticker: string, riskLevel: RiskLevel): EducationalInsight {
  const concepts: Record<string, Pick<EducationalInsight, 'concept' | 'title' | 'body' | 'tip'>> = {
    Low: {
      concept: 'Blue Chip Stocks',
      title: 'What Makes a Stock "Safe"?',
      body: `${ticker} falls in the "blue chip" category — large, well-established companies with long track records. These stocks are considered safer because they have diverse revenue streams, strong brand recognition, and financial reserves to weather economic storms.`,
      tip: `Even "safe" stocks can lose value. Diversifying across multiple low-risk stocks is wiser than concentrating in just one — no matter how reliable it seems.`,
    },
    Medium: {
      concept: 'Balanced Risk-Reward',
      title: 'The Middle Ground of Investing',
      body: `${ticker} represents a medium-risk investment — not as stable as a blue chip, but not as volatile as a pure growth play. Medium-risk stocks often offer a combination of some dividend income and moderate capital appreciation.`,
      tip: `Many financial advisors suggest keeping a core of medium-risk, diversified investments. They offer growth potential without the extreme volatility of high-risk picks.`,
    },
    High: {
      concept: 'Growth Stock Investing',
      title: 'High Risk, High Reward?',
      body: `${ticker} is a high-risk stock, often called a "growth stock." Its price reflects high expectations for future performance. When those expectations are met, returns can be exceptional. When they're not — even a small disappointment — the stock can drop sharply.`,
      tip: `If you're interested in high-risk stocks, consider using a "position sizing" approach — limiting any single high-risk stock to no more than 5–10% of a total portfolio to protect against severe losses.`,
    },
    'Very High': {
      concept: 'Speculative Investing',
      title: 'Understanding Speculation',
      body: `${ticker} is classified as very high risk — often called "speculative." These stocks can deliver extraordinary returns, but also extraordinary losses. Many speculative stocks lose 50–90% of their value when things go wrong. This is a category where most beginners should tread carefully.`,
      tip: `A core principle of risk management: never invest money you can't afford to lose entirely in speculative positions. The potential upside must always be weighed against the very real possibility of total loss.`,
    },
  };
  
  const content = concepts[riskLevel] ?? concepts['Medium'];
  return {
    ticker,
    ...content,
  };
}
