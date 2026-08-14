function assert(condition: boolean, message: string) {
  if (!condition) throw new Error(`Assertion failed: ${message}`);
}
assert.strictEqual = function(actual: any, expected: any, message: string) {
  if (actual !== expected) throw new Error(`Assertion failed: ${message}. Expected ${expected}, got ${actual}`);
}

import { analyzeStock } from './analysisEngine';
import type { PricePoint } from '../types';

function createMockHistory(trend: 'up' | 'down' | 'flat', volatility: 'low' | 'high'): PricePoint[] {
  const points: PricePoint[] = [];
  let price = 100;
  
  for (let i = 0; i < 60; i++) {
    let change = 0;
    
    if (trend === 'up') change += 1;
    if (trend === 'down') change -= 1;
    
    const noise = volatility === 'high' ? (Math.random() - 0.5) * 5 : (Math.random() - 0.5) * 1;
    price += change + noise;
    
    points.push({
      date: `2025-01-${String((i % 30) + 1).padStart(2, '0')}`,
      open: price,
      high: price + 1,
      low: price - 1,
      close: price,
      volume: 1000
    });
  }
  
  return points;
}

function testUptrendLowVol() {
  const history = createMockHistory('up', 'low');
  const result = analyzeStock('TEST', history);
  
  assert.strictEqual(result.trend.direction, 'Bullish', 'Uptrend should be Bullish');
  assert(result.risk.riskScore < 60, 'Low volatility uptrend should have low/medium risk');
  console.log('testUptrendLowVol: PASS');
}

function testDowntrendHighVol() {
  const history = createMockHistory('down', 'high');
  const result = analyzeStock('TEST', history);
  
  assert(['Bearish', 'Volatile'].includes(result.trend.direction), 'Downtrend should be Bearish or Volatile');
  assert(result.risk.riskScore > 40, 'High volatility should increase risk');
  console.log('testDowntrendHighVol: PASS');
}

function runAll() {
  try {
    testUptrendLowVol();
    testDowntrendHighVol();
    console.log('ALL ANALYSIS ENGINE TESTS PASSED');
  } catch (err) {
    console.error('TEST FAILED:', err);
    throw err;
  }
}

runAll();
