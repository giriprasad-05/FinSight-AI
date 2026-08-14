function assert(condition: boolean, message: string) {
  if (!condition) throw new Error(`Assertion failed: ${message}`);
}
assert.strictEqual = function(actual: any, expected: any, message: string) {
  if (actual !== expected) throw new Error(`Assertion failed: ${message}. Expected ${expected}, got ${actual}`);
}
assert.deepStrictEqual = function(actual: any, expected: any, message: string) {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) throw new Error(`Assertion failed: ${message}. Expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}

import {
  calculateSMA,
  calculateEMA,
  calculateRSI,
  calculateMACD,
  calculateVolatility
} from './indicators';

function testSMA() {
  const prices = [1, 2, 3, 4, 5];
  const sma = calculateSMA(prices, 3);
  assert.deepStrictEqual(sma, [2, 3, 4], 'SMA calculation is incorrect');
  console.log('testSMA: PASS');
}

function testEMA() {
  const prices = [1, 2, 3, 4, 5];
  const ema = calculateEMA(prices, 3);
  assert.deepStrictEqual(ema, [2, 3, 4], 'EMA calculation is incorrect for linear series');
  console.log('testEMA: PASS');
}

function testMACD() {
  const prices = Array(40).fill(100).map((v, i) => v + i); // linear trend
  const macdResult = calculateMACD(prices);
  assert(macdResult.macd.length > 0, 'MACD array should not be empty');
  console.log('testMACD: PASS');
}

function testRSI() {
  const prices = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25];
  const rsi = calculateRSI(prices, 14);
  assert.strictEqual(rsi[rsi.length - 1], 100, 'RSI for pure gains should be 100');
  
  const drops = [20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5];
  const rsiDrops = calculateRSI(drops, 14);
  assert.strictEqual(rsiDrops[rsiDrops.length - 1], 0, 'RSI for pure losses should be 0');
  console.log('testRSI: PASS');
}

function testVolatility() {
  const constantPrices = Array(30).fill(100);
  const vol = calculateVolatility(constantPrices, 20);
  assert.strictEqual(vol, 0, 'Volatility of constant prices should be 0');
  
  const alternating = [];
  for (let i = 0; i < 30; i++) alternating.push(i % 2 === 0 ? 100 : 110);
  const highVol = calculateVolatility(alternating, 20);
  assert(highVol > 0, 'Volatility of alternating prices should be > 0');
  console.log('testVolatility: PASS');
}

function runAll() {
  try {
    testSMA();
    testEMA();
    testMACD();
    testRSI();
    testVolatility();
    console.log('ALL INDICATOR TESTS PASSED');
  } catch (err) {
    console.error('TEST FAILED:', err);
    throw err;
  }
}

runAll();
