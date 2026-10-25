/**
 * stockController.js
 * -------------------
 * Handles stock-related API endpoints:
 *   GET /api/stocks/search?q=...      → searchStocks
 *   GET /api/stocks/:ticker/quote     → getStockQuote
 *   GET /api/stocks/:ticker/history   → getPriceHistory
 *   GET /api/stocks/:ticker           → getStockInfo
 *
 * All market data is fetched from the Python ML service which uses yfinance.
 * No yfinance logic lives here.
 */

import { getStockAnalysis, getStockQuote as fetchQuoteFromStockService } from '../services/stockService.js';
import { fetchHistory, fetchSearch } from '../services/mlService.js';
import { validateTicker } from '../utils/tickerValidator.js';


/**
 * GET /api/stocks/search?q=...
 *
 * Searches the supported stock universe via the Python ML service.
 * When q is empty, returns all 35 supported stocks.
 */
export async function searchStocks(req, res, next) {
  const q = (req.query.q || '').trim();
  if (q.length > 30) {
    return res.status(400).json({ error: 'Query too long (max 30 chars).', status: 400 });
  }

  try {
    const results = await fetchSearch(q);
    // Map to frontend-friendly shape
    const mapped = (results || []).map((s) => ({
      ticker: s.ticker,
      name: s.company_name || s.name || s.ticker,
      market: s.market || (s.ticker.endsWith('.NS') ? 'IN' : 'US'),
      currency: s.currency || (s.ticker.endsWith('.NS') ? 'INR' : 'USD'),
      exchange: s.exchange || (s.ticker.endsWith('.NS') ? 'NSE' : 'NASDAQ'),
      sector: s.sector || '',
      industry: s.industry || '',
      country: s.country || (s.market === 'IN' || s.ticker.endsWith('.NS') ? 'India' : 'United States'),
    }));
    res.json(mapped);
  } catch (err) {
    next(err);
  }
}


/**
 * GET /api/stocks/:ticker
 * GET /api/stocks/:ticker/quote
 *
 * Returns the latest available quote + company info for a ticker.
 * Delegates to the stockService → Python ML service → yfinance.
 * Never returns fake zeros — all missing fields are null.
 */
export async function getStockQuote(req, res, next) {
  const { valid, ticker, error } = validateTicker(req.params.ticker);
  if (!valid) {
    return res.status(400).json({ error, status: 400 });
  }

  try {
    const q = await fetchQuoteFromStockService(ticker);
    // Return the Python payload directly — no field fabrication
    res.json(q);
  } catch (err) {
    // Propagate 404 when the ticker genuinely has no data
    if (err.statusCode === 404) {
      return res.status(404).json({
        error: err.message || `No quote data for '${ticker}'.`,
        status: 404,
      });
    }
    next(err);
  }
}


/**
 * GET /api/stocks/:ticker/history?range=...
 *
 * Returns real historical OHLCV data from yfinance via the Python ML service.
 * Supported ranges: 1W | 1M | 3M | 6M | 1Y | 5Y
 *
 * NOTE: Does NOT read local CSV files. All data comes from yfinance in real time.
 */
export async function getPriceHistory(req, res, next) {
  const { valid, ticker, error } = validateTicker(req.params.ticker);
  if (!valid) {
    return res.status(400).json({ error, status: 400 });
  }

  const VALID_RANGES = new Set(['1W', '1M', '3M', '6M', '1Y', '5Y']);
  const range = (req.query.range || '1Y').toUpperCase();
  if (!VALID_RANGES.has(range)) {
    return res.status(400).json({
      error: `Invalid range '${range}'. Must be one of: 1W, 1M, 3M, 6M, 1Y, 5Y.`,
      status: 400,
    });
  }

  try {
    const data = await fetchHistory(ticker, range);
    res.json(data || []);
  } catch (err) {
    next(err);
  }
}


/**
 * GET /api/stocks/:ticker
 *
 * Returns lightweight stock identity info (ticker, market, last data date).
 * Uses the /analysis endpoint so only one ML service call is made.
 */
export async function getStockInfo(req, res, next) {
  const { valid, ticker, error } = validateTicker(req.params.ticker);
  if (!valid) {
    return res.status(400).json({ error, status: 400 });
  }

  try {
    const data = await getStockAnalysis(ticker);
    // Return only stock-identity fields — callers use /quote for full data
    res.json({
      ticker: data.ticker,
      market: data.market,
      data_date: data.data_date,
    });
  } catch (err) {
    next(err);
  }
}
