import type { PricePoint, TimeRange } from '@/types';
import { addDays, format, subDays, subMonths, subYears } from 'date-fns';

function generatePriceSeries(
  startPrice: number,
  points: number,
  volatility: number,
  drift: number,
  startDate: Date
): PricePoint[] {
  const result: PricePoint[] = [];
  let price = startPrice;

  for (let i = 0; i < points; i++) {
    const date = addDays(startDate, i);
    if (date.getDay() === 0 || date.getDay() === 6) continue;

    const change = price * (drift + (Math.random() - 0.5) * volatility * 2);
    const open = price;
    const close = Math.max(price + change, 0.01);
    const high = Math.max(open, close) * (1 + Math.random() * 0.012);
    const low  = Math.min(open, close) * (1 - Math.random() * 0.012);
    const volume = Math.floor(Math.random() * 30_000_000 + 5_000_000);

    result.push({
      date: format(date, 'yyyy-MM-dd'),
      open: +open.toFixed(2),
      high: +high.toFixed(2),
      low:  +low.toFixed(2),
      close: +close.toFixed(2),
      volume,
    });

    price = close;
  }
  return result;
}

const NOW = new Date();

interface TickerConfig {
  startPrice5Y: number;
  volatility: number;
  drift: number;
}

const CONFIGS: Record<string, TickerConfig> = {
  AAPL:  { startPrice5Y: 120,   volatility: 0.012, drift: 0.0003 },
  NVDA:  { startPrice5Y: 18,    volatility: 0.025, drift: 0.0009 },
  MSFT:  { startPrice5Y: 220,   volatility: 0.010, drift: 0.0004 },
  TSLA:  { startPrice5Y: 200,   volatility: 0.035, drift: 0.0001 },
  AMZN:  { startPrice5Y: 100,   volatility: 0.015, drift: 0.0005 },
  GOOGL: { startPrice5Y: 90,    volatility: 0.013, drift: 0.0005 },
  META:  { startPrice5Y: 180,   volatility: 0.018, drift: 0.0006 },
  JPM:   { startPrice5Y: 130,   volatility: 0.010, drift: 0.0003 },
  NFLX:  { startPrice5Y: 350,   volatility: 0.020, drift: 0.0005 },
  V:     { startPrice5Y: 200,   volatility: 0.008, drift: 0.0002 },
  DIS:   { startPrice5Y: 160,   volatility: 0.013, drift: -0.0001 },
  NVAX:  { startPrice5Y: 80,    volatility: 0.045, drift: -0.0008 },
  AMD:   { startPrice5Y: 70,    volatility: 0.022, drift: 0.0004 },
  INTC:  { startPrice5Y: 55,    volatility: 0.015, drift: -0.0003 },
  UBER:  { startPrice5Y: 30,    volatility: 0.018, drift: 0.0005 },
};

const _cache: Record<string, Record<TimeRange, PricePoint[]>> = {};

export function getMockPriceHistory(ticker: string): Record<TimeRange, PricePoint[]> {
  if (_cache[ticker]) return _cache[ticker];

  const cfg = CONFIGS[ticker] ?? { startPrice5Y: 100, volatility: 0.015, drift: 0.0002 };
  const fullStart = subYears(NOW, 5);
  const full5Y = generatePriceSeries(
    cfg.startPrice5Y,
    365 * 5,
    cfg.volatility,
    cfg.drift,
    fullStart
  );

  const ranges: Record<TimeRange, PricePoint[]> = {
    '5Y': full5Y,
    '1Y': full5Y.filter(p => new Date(p.date) >= subYears(NOW, 1)),
    '6M': full5Y.filter(p => new Date(p.date) >= subMonths(NOW, 6)),
    '3M': full5Y.filter(p => new Date(p.date) >= subMonths(NOW, 3)),
    '1M': full5Y.filter(p => new Date(p.date) >= subMonths(NOW, 1)),
    '1W': full5Y.filter(p => new Date(p.date) >= subDays(NOW, 7)),
  };

  _cache[ticker] = ranges;
  return ranges;
}
