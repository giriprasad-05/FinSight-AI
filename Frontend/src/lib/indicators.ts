export function calculateSMA(prices: number[], period: number): number[] {
  if (prices.length < period || period <= 0) return [];
  const sma: number[] = [];
  let sum = 0;
  
  for (let i = 0; i < prices.length; i++) {
    sum += prices[i];
    if (i >= period) sum -= prices[i - period];
    if (i >= period - 1) sma.push(sum / period);
  }
  return sma;
}

export function calculateEMA(prices: number[], period: number): number[] {
  if (prices.length < period || period <= 0) return [];
  const ema: number[] = [];
  const k = 2 / (period + 1);
  
  // Initial EMA is SMA
  let sum = 0;
  for (let i = 0; i < period; i++) sum += prices[i];
  let currentEma = sum / period;
  ema.push(currentEma);
  
  for (let i = period; i < prices.length; i++) {
    currentEma = (prices[i] - currentEma) * k + currentEma;
    ema.push(currentEma);
  }
  return ema;
}

export interface MACDResult {
  macd: number[];
  signal: number[];
  histogram: number[];
}

export function calculateMACD(prices: number[], fast = 12, slow = 26, signal = 9): MACDResult {
  if (prices.length < slow + signal) {
    return { macd: [], signal: [], histogram: [] };
  }
  
  const emaFast = calculateEMA(prices, fast);
  const emaSlow = calculateEMA(prices, slow);
  
  // emaFast and emaSlow have different lengths. 
  // emaFast starts at index (fast - 1), emaSlow starts at index (slow - 1).
  const macd: number[] = [];
  const diff = slow - fast;
  for (let i = 0; i < emaSlow.length; i++) {
    macd.push(emaFast[i + diff] - emaSlow[i]);
  }
  
  const signalLine = calculateEMA(macd, signal);
  
  const histogram: number[] = [];
  const sigDiff = signal - 1;
  for (let i = 0; i < signalLine.length; i++) {
    histogram.push(macd[i + sigDiff] - signalLine[i]);
  }
  
  return { macd, signal: signalLine, histogram };
}

export function calculateRSI(prices: number[], period = 14): number[] {
  if (prices.length <= period || period <= 0) return [];
  const rsi: number[] = [];
  
  let gains = 0;
  let losses = 0;
  
  // Initial average gain/loss
  for (let i = 1; i <= period; i++) {
    const diff = prices[i] - prices[i - 1];
    if (diff > 0) gains += diff;
    else losses -= diff; // keep losses positive
  }
  
  let avgGain = gains / period;
  let avgLoss = losses / period;
  
  if (avgLoss === 0) rsi.push(100);
  else rsi.push(100 - (100 / (1 + (avgGain / avgLoss))));
  
  for (let i = period + 1; i < prices.length; i++) {
    const diff = prices[i] - prices[i - 1];
    const gain = diff > 0 ? diff : 0;
    const loss = diff < 0 ? -diff : 0;
    
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
    
    if (avgLoss === 0) {
      rsi.push(100);
    } else {
      rsi.push(100 - (100 / (1 + (avgGain / avgLoss))));
    }
  }
  
  return rsi;
}

export function calculateVolatility(prices: number[], period = 20): number {
  if (prices.length <= period) return 0;
  
  // Calculate daily returns for the last `period` days
  const returns: number[] = [];
  const start = prices.length - period - 1;
  for (let i = Math.max(0, start); i < prices.length - 1; i++) {
    returns.push((prices[i + 1] - prices[i]) / prices[i]);
  }
  
  if (returns.length === 0) return 0;
  
  const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
  const variance = returns.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / returns.length;
  const stdDev = Math.sqrt(variance);
  
  // Annualize volatility assuming 252 trading days
  return stdDev * Math.sqrt(252);
}
