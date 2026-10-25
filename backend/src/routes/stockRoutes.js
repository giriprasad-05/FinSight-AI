/**
 * stockRoutes.js
 * ---------------
 * Stock-related API routes:
 *   GET /api/stocks/search?q=...      → search the supported stock universe
 *   GET /api/stocks/:ticker/quote     → latest quote + company info (yfinance)
 *   GET /api/stocks/:ticker/history   → historical OHLCV data (yfinance)
 *   GET /api/stocks/:ticker           → lightweight stock identity
 *
 * IMPORTANT: The /search route MUST be registered before /:ticker
 * to avoid Express treating "search" as a ticker parameter.
 */

import { Router } from 'express';
import {
  searchStocks,
  getStockQuote,
  getPriceHistory,
  getStockInfo,
} from '../controllers/stockController.js';

const router = Router();

// GET /api/stocks/search?q=...
// Must come BEFORE /:ticker routes so "search" is not treated as a ticker
router.get('/search', searchStocks);

// GET /api/stocks/:ticker/quote
router.get('/:ticker/quote', getStockQuote);

// GET /api/stocks/:ticker/history
router.get('/:ticker/history', getPriceHistory);

// GET /api/stocks/:ticker/info (lightweight metadata)
router.get('/:ticker/info', getStockInfo);

// GET /api/stocks/:ticker (primary endpoint for stock data from Yahoo Finance)
router.get('/:ticker', getStockQuote);

export default router;
